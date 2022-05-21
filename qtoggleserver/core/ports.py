
from __future__ import annotations

import abc
import asyncio
import copy
import functools
import inspect
import logging

from typing import Any, Dict, List, Optional, Set, Union

from qtoggleserver import persist
from qtoggleserver.conf import settings
from qtoggleserver.core import events as core_events
from qtoggleserver.core import expressions as core_expressions
from qtoggleserver.core import history as core_history
from qtoggleserver.core import main
from qtoggleserver.core import sequences as core_sequences
from qtoggleserver.core.typing import Attribute, Attributes, AttributeDefinitions, GenericJSONDict
from qtoggleserver.core.typing import NullablePortValue, PortValue
from qtoggleserver.utils import dynload as dynload_utils
from qtoggleserver.utils import json as json_utils
from qtoggleserver.utils import logging as logging_utils


TYPE_BOOLEAN = 'boolean'
TYPE_NUMBER = 'number'

CHANGE_REASON_NATIVE = 'N'
CHANGE_REASON_API = 'A'
CHANGE_REASON_SEQUENCE = 'S'
CHANGE_REASON_EXPRESSION = 'E'

SAVE_INTERVAL = 1

logger = logging.getLogger(__name__)

_ports_by_id: Dict[str, BasePort] = {}
_save_loop_task: Optional[asyncio.Task] = None


async def _attrdef_unit_enabled(port: BasePort) -> bool:
    return await port.get_type() == TYPE_NUMBER


STANDARD_ATTRDEFS = {
    'id': {
        'type': 'string'
    },
    'display_name': {
        'type': 'string',
        'modifiable': True,
        'max': 64
    },
    'type': {
        'type': 'string',
        'choices': [
            {
                'value': 'boolean',
                'display_name': 'Boolean'
            },
            {
                'value': 'number',
                'display_name': 'Number'
            }
        ]
    },
    'unit': {
        'type': 'string',
        'modifiable': True,
        'max': 16,
        'enabled': _attrdef_unit_enabled
    },
    'writable': {
        'type': 'boolean'
    },
    'enabled': {
        'type': 'boolean',
        'modifiable': True
    },

    'min': {
        'type': 'number',
        'optional': True
    },
    'max': {
        'type': 'number',
        'optional': True
    },
    'integer': {
        'type': 'boolean',
        'optional': True
    },
    'step': {
        'type': 'number',
        'optional': True
    },
    'choices': {  # TODO data type uncertain
        'type': '[]',
        'optional': True
    },

    'tag': {
        'type': 'string',
        'optional': True,
        'modifiable': True,
        'max': 64,
    },
    'expression': {
        'type': 'string',
        'optional': True,
        'modifiable': True,
        'max': 1024,
    },
    'transform_read': {
        'type': 'string',
        'optional': True,
        'modifiable': True,
        'max': 1024,
    },
    'transform_write': {
        'type': 'string',
        'optional': True,
        'modifiable': True,
        'max': 1024,
    },
    'persisted': {
        'type': 'boolean',
        'optional': True,
        'modifiable': True
    },
    'internal': {
        'type': 'boolean',
        'optional': True,
        'modifiable': True
    },
    'virtual': {
        'type': 'boolean',
        'optional': True
    },
    'online': {
        'type': 'boolean',
        'optional': True
    },
    'history_interval': {
        'type': 'number',
        'integer': True,
        'min': -1,
        'max': 2147483647,
        'optional': True,
        'modifiable': True,
        'enabled': lambda p: core_history.is_enabled()
    },
    'history_retention': {
        'type': 'number',
        'integer': True,
        'min': 0,
        'max': 2147483647,
        'optional': True,
        'modifiable': True,
        'enabled': lambda p: core_history.is_enabled()
    }
}


class PortError(Exception):
    pass


class PortLoadError(PortError):
    pass


class PortReadError(PortError):
    pass


class InvalidAttributeValue(PortError):
    def __init__(self, attr: str, details: Optional[GenericJSONDict] = None) -> None:
        self.attr: str = attr
        self.details: Optional[GenericJSONDict] = details

        super().__init__(attr)


class PortTimeout(PortError):
    pass


class BasePort(logging_utils.LoggableMixin, metaclass=abc.ABCMeta):
    PERSIST_COLLECTION = 'ports'

    TYPE = TYPE_BOOLEAN
    DISPLAY_NAME = ''
    UNIT = ''
    WRITABLE = False
    CHOICES = None

    WRITE_VALUE_QUEUE_SIZE = 1024

    STANDARD_ATTRDEFS = STANDARD_ATTRDEFS

    ADDITIONAL_ATTRDEFS = {}
    '''
    ADDITIONAL_ATTRDEFS = {
        'attr1': {
            'display_name': 'Some Attribute Display Name',
            'description': 'Some attribute description',
            'type': 'number',
            'modifiable': True,
            'pattern': '^.*$',
            'unit': 'seconds',
            'min': 1,
            'max': 100,
            'integer': True,
            'step': 5,
            'choices': [
                {'value': 2, 'display_name': 'Two'},
                {'value': 4, 'display_name': 'Four'}
            ]
        },
        ...
    }'''

    def __init__(self, port_id: str) -> None:
        logging_utils.LoggableMixin.__init__(self, port_id, logger)

        self._id: str = port_id
        self._enabled: bool = False
        self._display_name: Optional[str] = None
        self._unit: Optional[str] = None

        self._sequence: Optional[core_sequences.Sequence] = None
        self._expression: Optional[core_expressions.Expression] = None
        self._transform_read: Optional[core_expressions.Expression] = None
        self._transform_write: Optional[core_expressions.Expression] = None

        self._history_interval: int = 0
        self._history_retention: int = 0
        self._history_last_timestamp: int = 0

        # Attributes cache is used to prevent computing an attribute value more than once per core iteration
        self._attrs_cache: Attributes = {}

        # Cache attribute definitions so that the ATTRDEFS property doesn't need to gather all of them on each access
        self._attrdefs_cache: Optional[AttributeDefinitions] = None

        self._modifiable_attrs: Optional[Set[str]] = None
        self._non_modifiable_attrs: Optional[Set[str]] = None

        self._schema: Optional[GenericJSONDict] = None
        self._value_schema: Optional[GenericJSONDict] = None

        self._last_read_value: NullablePortValue = None
        self._write_value_queue: asyncio.Queue = asyncio.Queue(maxsize=self.WRITE_VALUE_QUEUE_SIZE)
        self._write_value_task: Optional[asyncio.Task] = None
        if asyncio.get_event_loop().is_running():
            self._write_value_task = asyncio.create_task(self._write_value_loop())
        self._change_reason: str = CHANGE_REASON_NATIVE
        self._reading: bool = False
        self._writing: bool = False

        self._eval_queue: asyncio.Queue = asyncio.Queue(maxsize=self.WRITE_VALUE_QUEUE_SIZE)
        self._eval_task: Optional[asyncio.Task] = None
        if asyncio.get_event_loop().is_running():
            self._eval_task = asyncio.create_task(self._eval_loop())

        self._save_lock: asyncio.Lock = asyncio.Lock()
        self._pending_save: bool = False

        self._loaded: bool = False

    def __str__(self) -> str:
        return f'port {self._id}'

    def __repr__(self) -> str:
        return f'Port({self._id})'

    def initialize(self) -> None:
        pass

    async def get_attrdefs(self) -> AttributeDefinitions:
        if self._attrdefs_cache is None:
            self._attrdefs_cache = dict(self.STANDARD_ATTRDEFS, **self.ADDITIONAL_ATTRDEFS)

            for name, attrdef in list(self._attrdefs_cache.items()):
                enabled = attrdef.get('enabled', True)
                if callable(enabled):
                    enabled = enabled(self)
                if inspect.isawaitable(enabled):
                    enabled = await enabled

                if not enabled:
                    self._attrdefs_cache.pop(name)

        return self._attrdefs_cache

    def invalidate_attrdefs(self) -> None:
        self._attrs_cache = {}
        self._attrdefs_cache = None
        self._modifiable_attrs = None
        self._non_modifiable_attrs = None
        self._schema = None

    async def get_non_modifiable_attrs(self) -> Set[str]:
        attrdefs = await self.get_attrdefs()

        if self._non_modifiable_attrs is None:
            self._non_modifiable_attrs = set(n for (n, v) in attrdefs.items() if not v.get('modifiable'))

        return self._non_modifiable_attrs

    async def get_modifiable_attrs(self) -> Set[str]:
        attrdefs = await self.get_attrdefs()

        if self._modifiable_attrs is None:
            self._modifiable_attrs = set(n for (n, v) in attrdefs.items() if v.get('modifiable'))

        return self._modifiable_attrs

    async def get_attrs(self) -> Attributes:
        d = {}

        for name in await self.get_attrdefs():
            v = await self.get_attr(name)
            if v is None:
                continue

            d[name] = v

        return d

    def invalidate_attrs(self) -> None:
        self._attrs_cache = {}

    async def get_attr(self, name: str) -> Optional[Attribute]:
        value = self._attrs_cache.get(name)
        if value is not None:
            return value

        method = getattr(self, 'attr_get_' + name, getattr(self, 'attr_is_' + name, None))
        if method:
            value = await method()
            if value is not None:
                self._attrs_cache[name] = value
                return value

        value = getattr(self, '_' + name, None)
        if value is not None:
            self._attrs_cache[name] = value
            return value

        method = getattr(self, 'attr_get_default_' + name, getattr(self, 'attr_is_default_' + name, None))
        if method:
            value = await method()
            if value is not None:
                self._attrs_cache[name] = value
                return value

        value = getattr(self, name.upper(), None)
        if value is not None:
            self._attrs_cache[name] = value
            return value

        return None  # Unsupported attribute

    async def set_attr(self, name: str, value: Attribute) -> None:
        old_value = await self.get_attr(name)
        if old_value is None:
            return  # Refuse to set an unsupported attribute

        method = getattr(self, 'attr_set_' + name, None)
        if method:
            try:
                await method(value)

            except Exception:
                self.error('failed to set attribute %s = %s', name, json_utils.dumps(value), exc_info=True)

                raise

        elif hasattr(self, '_' + name):
            setattr(self, '_' + name, value)

        if self.is_loaded():
            await main.update()

        # New attributes might have been added or removed after setting an attribute; therefore new definitions might
        # have appeared or disappeared
        self.invalidate_attrdefs()

        self._attrs_cache[name] = value
        if old_value != value:
            await self.handle_attr_change(name, value)

        if not self.is_loaded():
            return

        # Skip an IO loop iteration, allowing setting multiple attributes before triggering a port-update
        await asyncio.sleep(0)
        await self.trigger_update()

    def invalidate_attr(self, name: str) -> None:
        self._attrs_cache.pop(name, None)

    async def handle_attr_change(self, name: str, value: Attribute) -> None:
        method_name = f'handle_{name}'
        method = getattr(self, method_name, None)
        if method:
            try:
                await method(value)

            except Exception as e:
                self.error('%s failed: %s', method_name, e, exc_info=True)

    async def get_display_name(self) -> str:
        return await self.get_attr('display_name') or self._id

    async def get_display_value(self, value: NullablePortValue = None) -> str:
        choices = await self.get_attr('choices')
        unit = await self.get_attr('unit')
        if value is None:
            value = self.get_last_read_value()

        if value is None:
            return 'unknown'  # TODO: i18n

        if choices:
            for choice in choices:
                if choice['value'] == value:
                    return choice['display_name']

        if await self.get_type() == TYPE_BOOLEAN:
            value_str = 'on' if value else 'off'  # TODO: i18n

        else:
            value_str = str(value)

        if unit:
            return f'{value_str}{unit}'

        else:
            return value_str

    def get_id(self) -> str:
        return self._id

    def map_id(self, new_id: str) -> None:
        self._id = new_id
        self.debug('mapped to %s', new_id)
        self.set_logger_name(new_id)

    async def get_type(self) -> str:
        return await self.get_attr('type')

    async def is_writable(self) -> bool:
        return await self.get_attr('writable')

    async def is_persisted(self) -> bool:
        return await self.get_attr('persisted')

    async def is_internal(self) -> bool:
        return await self.get_attr('internal')

    def is_enabled(self) -> bool:
        return self._enabled

    async def enable(self) -> None:
        if self._enabled:
            return

        self.debug('enabling')
        self._enabled = True
        self.invalidate_attr('enabled')

        # Reset port expression
        if self._expression:
            sexpression = str(self._expression)
            self.debug('resetting expression "%s"', sexpression)
            self._expression = core_expressions.parse(self.get_id(), sexpression)

            main.force_eval_expressions(self)

        try:
            await self.handle_enable()

        except Exception:
            self.error('failed to enable')
            self._enabled = False

            raise

    async def disable(self) -> None:
        if not self._enabled:
            return

        # Cancel sequence
        if self._sequence:
            self.debug('canceling current sequence')
            await self._sequence.cancel()
            self._sequence = None

        self.debug('disabling')
        self._enabled = False
        self.invalidate_attr('enabled')

        try:
            await self.handle_disable()

        except Exception:
            self.error('failed to disable')
            self._enabled = True

            raise

    async def handle_enable(self) -> None:
        pass

    async def handle_disable(self) -> None:
        pass

    async def attr_set_enabled(self, value: bool) -> None:
        if value:
            await self.enable()

        else:
            await self.disable()

    def get_expression(self) -> Optional[core_expressions.Expression]:
        return self._expression

    async def attr_get_expression(self) -> Optional[str]:
        writable = self._attrs_cache.get('writable')  # Use cached value if available, to avoid unnecessary await
        if writable is None:
            writable = await self.is_writable()

        if not writable:
            return None

        if self._expression:
            return str(self._expression)

        else:
            return ''

    async def attr_set_expression(self, sexpression: str) -> None:
        writable = self._attrs_cache.get('writable')  # Use cached value if available, to avoid unnecessary await
        if writable is None:
            writable = await self.is_writable()

        if not writable:
            self.error('refusing to set expression on non-writable port')
            raise PortError('Cannot set expression on non-writable port')

        if self._sequence:
            self.debug('canceling current sequence')
            await self._sequence.cancel()
            self._sequence = None

        if not sexpression:
            self._expression = None
            return

        try:
            self.debug('parsing expression "%s"', sexpression)
            expression = core_expressions.parse(self.get_id(), sexpression)

            self.debug('checking for expression circular dependencies')
            await core_expressions.check_loops(self, expression)

        except core_expressions.ExpressionParseError as e:
            self.error('failed to set expression "%s": %s', sexpression, e)

            raise InvalidAttributeValue('expression', details=e.to_json()) from e

        self.debug('setting expression "%s"', expression)
        self._expression = expression

        main.force_eval_expressions(self)

    async def attr_get_transform_read(self) -> str:
        if self._transform_read:
            return str(self._transform_read)

        else:
            return ''

    async def attr_set_transform_read(self, stransform_read: str) -> None:
        if not stransform_read:
            self._transform_read = None
            return

        try:
            self.debug('parsing expression "%s"', stransform_read)
            transform_read = core_expressions.parse(self.get_id(), stransform_read)

            deps = transform_read.get_deps()
            for dep in deps:
                if not dep.startswith('$'):
                    continue

                if dep != f'${self._id}':
                    raise core_expressions.ExternalDependency(
                        port_id=dep[1:],
                        pos=stransform_read.index(dep)
                    )

            self.debug('setting read transform "%s"', transform_read)
            self._transform_read = transform_read

        except core_expressions.ExpressionParseError as e:
            self.error('failed to set transform read expression "%s": %s', stransform_read, e)

            raise InvalidAttributeValue('transform_read', details=e.to_json()) from e

    async def attr_get_transform_write(self) -> Optional[str]:
        writable = self._attrs_cache.get('writable')  # Use cached value if available, to avoid unnecessary await
        if writable is None:
            writable = await self.is_writable()

        if not writable:
            return None  # Only writable ports have transform_write attributes

        if self._transform_write:
            return str(self._transform_write)

        else:
            return ''

    async def attr_set_transform_write(self, stransform_write: str) -> None:
        if not stransform_write:
            self._transform_write = None
            return

        try:
            self.debug('parsing expression "%s"', stransform_write)
            transform_write = core_expressions.parse(self.get_id(), stransform_write)

            deps = transform_write.get_deps()
            for dep in deps:
                if not dep.startswith('$'):
                    continue

                if dep != f'${self._id}':
                    raise core_expressions.ExternalDependency(
                        port_id=dep[1:],
                        pos=stransform_write.index(dep)
                    )

            self.debug('setting write transform "%s"', transform_write)
            self._transform_write = transform_write

        except core_expressions.ExpressionParseError as e:
            self.error('failed to set transform write expression "%s": %s', stransform_write, e)

            raise InvalidAttributeValue('transform_write', details=e.to_json()) from e

    async def get_history_interval(self) -> int:
        return await self.get_attr('history_interval')

    async def get_history_retention(self) -> int:
        return await self.get_attr('history_retention')

    def get_history_last_timestamp(self) -> int:
        return self._history_last_timestamp

    def set_history_last_timestamp(self, timestamp: int) -> None:
        self._history_last_timestamp = timestamp

    @abc.abstractmethod
    async def read_value(self) -> NullablePortValue:
        return None

    async def write_value(self, value: PortValue) -> None:
        pass

    def get_last_read_value(self) -> NullablePortValue:
        return self._last_read_value

    def set_last_read_value(self, value: NullablePortValue) -> None:
        self._last_read_value = value

    def get_change_reason(self) -> str:
        return self._change_reason

    def reset_change_reason(self) -> None:
        self._change_reason = CHANGE_REASON_NATIVE

    async def read_transformed_value(self) -> NullablePortValue:
        if self._reading:
            return  # Prevent overlapped readings

        self._reading = True

        try:
            value = await self.read_value()

        except Exception:
            raise

        finally:
            self._reading = False

        if value is None:
            return None

        if self._transform_read:
            # Temporarily set the new value to the port, so that the read transform expression works as expected
            old_value = self._last_read_value
            self._last_read_value = value
            value = await self.adapt_value_type(await self._transform_read.eval(self._make_expression_context()))
            self._last_read_value = old_value

        return value

    def is_reading(self) -> bool:
        return self._reading

    async def write_transformed_value(self, value: PortValue, reason: str) -> None:
        value_str = json_utils.dumps(value)

        if self._transform_write:
            # Temporarily set the port value to the new value, so that the write transform expression takes the new
            # value into consideration when evaluating the result
            prev_value = self._last_read_value
            self._last_read_value = value
            value = await self.adapt_value_type(await self._transform_write.eval(self._make_expression_context()))
            self._last_read_value = prev_value

            value_str = f'{value_str} ({json_utils.dumps(value)} after write transform)'

        try:
            await self._write_value_queued(value, reason)
            self.debug('wrote value %s (reason=%s)', value_str, reason)

        except Exception:
            self.error('failed to write value %s (reason=%s)', value_str, reason, exc_info=True)

            raise

    def is_writing(self) -> bool:
        return self._writing

    async def _write_value_queued(self, value: PortValue, reason: str) -> None:
        done = asyncio.get_running_loop().create_future()

        while True:
            try:
                self._write_value_queue.put_nowait((value, reason, done))

            except asyncio.QueueFull as e:
                self.warning('write queue full, dropping oldest value')

                # Reject the future of the dropped request with a QueueFull exception
                dropped = self._write_value_queue.get_nowait()
                dropped[2].set_exception(e)

            else:
                break

        # Wait for actual write_value operation to be done
        await done

    async def _write_value_loop(self) -> None:
        while True:
            try:
                value, reason, done = await self._write_value_queue.get()

                self._change_reason = reason
                self._writing = True

                try:
                    result = await self.write_value(value)
                    done.set_result(result)

                except Exception as e:
                    done.set_exception(e)

                self._writing = False

                await main.update()  # Do an update after every confirmed write

            except asyncio.CancelledError:
                self.debug('write value task cancelled')
                break

    def push_eval(self, port_values: Dict[str, NullablePortValue]) -> None:
        self.debug('will evaluate expression asap')

        try:
            self._eval_queue.put_nowait(self._make_expression_context(port_values))

        except asyncio.QueueFull:
            self.warning('eval queue full')

    async def _eval_loop(self) -> None:
        while True:
            try:
                context = await self._eval_queue.get()
                await self._eval_and_write(context)

            except asyncio.CancelledError:
                self.debug('eval task cancelled')
                break

    async def _eval_and_write(self, context: Dict[str, Any]) -> None:
        self.debug('evaluating expression')
        expression = self.get_expression()

        try:
            value = await expression.eval(context)

        except core_expressions.ExpressionEvalError:
            return

        except Exception as e:
            self.error('failed to evaluate expression "%s": %s', expression, e)
            return

        value = await self.adapt_value_type(value)
        if value is None:
            return

        if value != self.get_last_read_value():  # Value changed after evaluation
            self.debug('expression "%s" evaluated to %s', expression, json_utils.dumps(value))
            try:
                await self.write_transformed_value(value, reason=CHANGE_REASON_EXPRESSION)

            except Exception as e:
                self.error('failed to write value: %s', e)

    def _make_expression_context(self, port_values: Optional[Dict[str, NullablePortValue]] = None) -> Dict[str, Any]:
        if port_values is None:
            # In case port values haven't been supplied with context
            port_values = {p.get_id(): p.get_last_read_value() for p in get_all()}

        return {
            'port_values': port_values
        }

    async def adapt_value_type(self, value: NullablePortValue) -> NullablePortValue:
        return self.adapt_value_type_sync(await self.get_type(), await self.get_attr('integer'), value)

    @staticmethod
    def adapt_value_type_sync(type_: str, integer: bool, value: NullablePortValue) -> NullablePortValue:
        if value is None:
            return None

        if type_ == TYPE_BOOLEAN:
            return bool(value)

        else:
            # Round the value if port accepts only integers
            if integer:
                return int(value)

            return float(value)

    async def set_sequence(self, values: List[PortValue], delays: List[int], repeat: int) -> None:
        if self._sequence:
            self.debug('canceling current sequence')
            await self._sequence.cancel()
            self._sequence = None

        if values:
            callback = functools.partial(self._write_transformed_value_fire_and_forget, reason=CHANGE_REASON_SEQUENCE)
            self._sequence = core_sequences.Sequence(values, delays, repeat, callback, self._on_sequence_finish)

            self.debug('installing sequence')
            self._sequence.start()

    def _write_transformed_value_fire_and_forget(self, value: PortValue, reason: str) -> None:
        asyncio.create_task(self.write_transformed_value(value, reason))

    async def _on_sequence_finish(self) -> None:
        self.debug('sequence finished')

        self._sequence = None
        if await self.is_persisted():
            self.save_asap()

    def heart_beat_second(self) -> None:
        pass

    async def to_json(self) -> GenericJSONDict:
        attrs = await self.get_attrs()
        attrs = dict(attrs)

        if self._enabled:
            attrs['value'] = self._last_read_value

        else:
            attrs['value'] = None

        attrdefs = copy.deepcopy(self.ADDITIONAL_ATTRDEFS)
        for attrdef in attrdefs.values():
            attrdef.pop('pattern', None)

        attrs['definitions'] = attrdefs

        return attrs

    async def load(self) -> None:
        self.debug('loading persisted data')

        data = await persist.get(self.PERSIST_COLLECTION, self.get_id()) or {}
        await self.load_from_data(data)

        self.set_loaded()
        self.initialize()

    async def reset(self) -> None:
        self.debug('resetting persisted data')
        await self.load_from_data(data={})
        self.invalidate_attrdefs()

    async def load_from_data(self, data: GenericJSONDict) -> None:
        attrs_start = ['enabled']  # These will be loaded first, in this order
        attrs_end = ['expression']  # These will be loaded last, in this order

        attr_items = data.items()
        attr_items = [a for a in attr_items if (a[0] not in attrs_start) and (a[0] not in attrs_end)]

        attr_items_start = []
        for n in attrs_start:
            v = data.get(n)
            if v is not None:
                attr_items_start.append((n, v))

        # Sort the rest of the attributes alphabetically
        attr_items.sort(key=lambda i: i[0])

        attr_items_end = []
        for n in attrs_end:
            v = data.get(n)
            if v is not None:
                attr_items_end.append((n, v))

        attr_items = attr_items_start + attr_items + attr_items_end

        for name, value in attr_items:
            if name in ('id', 'value'):
                continue  # Value is also among the persisted fields

            try:
                self.debug('loading %s = %s', name, json_utils.dumps(value))
                await self.set_attr(name, value)

            except Exception as e:
                self.error('failed to set attribute %s = %s: %s', name, json_utils.dumps(value), e)

        # value
        if await self.is_persisted() and data.get('value') is not None:
            self._last_read_value = data['value']
            self.debug('loaded value = %s', json_utils.dumps(self._last_read_value))

            if await self.is_writable():
                # Write the just-loaded value to the port
                value = self._last_read_value
                if self._transform_write:
                    value = await self.adapt_value_type(
                        await self._transform_write.eval(self._make_expression_context())
                    )

                await self.write_value(value)

        elif self.is_enabled():
            try:
                value = await self.read_transformed_value()
                if value is not None:
                    self._last_read_value = value
                    self.debug('read value = %s', json_utils.dumps(self._last_read_value))

            except Exception as e:
                self.error('failed to read value: %s', e, exc_info=True)

        # various
        self._history_last_timestamp = data.get('history_last_timestamp', 0)

    async def save(self) -> None:
        if not self.is_loaded():
            return

        self.debug('persisting data')

        async with self._save_lock:
            d = await self.prepare_for_save()
            await persist.replace(self.PERSIST_COLLECTION, self._id, d)

        self._pending_save = False

    async def prepare_for_save(self) -> GenericJSONDict:
        # value
        d = {
            'id': self.get_id(),
            'history_last_timestamp': self._history_last_timestamp
        }

        if await self.is_persisted():
            d['value'] = self._last_read_value

        else:
            d['value'] = None

        # attributes
        for name in await self.get_modifiable_attrs():
            v = await self.get_attr(name)
            if v is None:
                continue

            d[name] = v

        return d

    def save_asap(self) -> None:
        self.debug('marking for saving')
        self._pending_save = True

    def is_pending_save(self) -> bool:
        return self._pending_save

    async def cleanup(self) -> None:
        if self._write_value_task:
            self._write_value_task.cancel()
            await self._write_value_task
            self._write_value_task = None

        if self._eval_task:
            self._eval_task.cancel()
            await self._eval_task
            self._eval_task = None

    def is_loaded(self) -> bool:
        return self._loaded

    def set_loaded(self) -> None:
        self._loaded = True

    async def remove(self, persisted_data: bool = True) -> None:
        await self.cleanup()

        self.debug('removing port')
        _ports_by_id.pop(self._id, None)

        if persisted_data:
            self.debug('removing persisted data')
            await persist.remove(self.PERSIST_COLLECTION, filt={'id': self._id})
            if core_history.is_enabled():
                await core_history.remove_samples([self], background=True)

        await self.trigger_remove()

    async def trigger_add(self) -> None:
        await core_events.trigger(core_events.PortAdd(self))

    async def trigger_remove(self) -> None:
        await core_events.trigger(core_events.PortRemove(self))

    async def trigger_update(self) -> None:
        await core_events.trigger(core_events.PortUpdate(self))

    async def trigger_value_change(self) -> None:
        await core_events.trigger(core_events.ValueChange(self))

    async def get_schema(self) -> GenericJSONDict:
        if self._schema is None:
            self._schema = {
                'type': 'object',
                'properties': {},
                'additionalProperties': False
            }

            attrdefs = await self.get_attrdefs()
            for name, attrdef in attrdefs.items():
                if not attrdef.get('modifiable'):
                    continue

                if await self.get_attr(name) is None:
                    continue

                attr_schema = dict(attrdef)

                if attr_schema['type'] == 'string':
                    if 'min' in attr_schema:
                        attr_schema['minLength'] = attr_schema.pop('min')

                    if 'max' in attr_schema:
                        attr_schema['maxLength'] = attr_schema.pop('max')

                elif attr_schema['type'] == 'number':
                    if attr_schema.get('integer'):
                        attr_schema['type'] = 'integer'

                    if 'min' in attr_schema:
                        attr_schema['minimum'] = attr_schema.pop('min')

                    if 'max' in attr_schema:
                        attr_schema['maximum'] = attr_schema.pop('max')

                if 'choices' in attrdef:
                    attr_schema['enum'] = [c['value'] for c in attr_schema.pop('choices')]

                attr_schema.pop('modifiable', None)

                self._schema['properties'][name] = attr_schema

        return self._schema

    async def get_value_schema(self) -> GenericJSONDict:
        if self._value_schema is None:
            self._value_schema = {}

            c = await self.get_attr('choices')
            if c is not None:
                self._value_schema['enum'] = [i['value'] for i in c]

            else:
                m = await self.get_attr('min')
                if m is not None:
                    self._value_schema['minimum'] = m

                m = await self.get_attr('max')
                if m is not None:
                    self._value_schema['maximum'] = m

                if await self.get_attr('integer'):
                    self._value_schema['type'] = 'integer'

                elif await self.get_type() == TYPE_BOOLEAN:
                    self._value_schema['type'] = 'boolean'

                else:  # Assuming number
                    self._value_schema['type'] = 'number'

        return self._value_schema


class Port(BasePort, metaclass=abc.ABCMeta):
    def __init__(self, port_id: str) -> None:
        super().__init__(port_id)

        self._tag: str = ''
        self._persisted: bool = False
        self._internal: bool = False


async def load(
    port_args: List[Dict[str, Any]],
    raise_on_error: bool = True,
    trigger_add: bool = True
) -> List[BasePort]:
    port_driver_classes = {}
    ports = []

    # Create ports
    for ps in port_args:
        driver = ps.pop('driver', None)
        if not driver:
            if raise_on_error:
                raise PortLoadError('Missing port driver')

            logger.error('ignoring port with no driver')
            continue

        if isinstance(driver, str):
            if driver not in port_driver_classes:
                try:
                    logger.debug('loading port driver %s', driver)
                    port_driver_classes[driver] = dynload_utils.load_attr(driver)

                except Exception as e:
                    if raise_on_error:
                        raise PortLoadError(f'Failed to load port driver {driver}') from e

                    logger.error('failed to load port driver %s: %s', driver, e, exc_info=True)
                    continue

            port_class = port_driver_classes[driver]

        else:
            port_class = driver

        port_class_desc = f'{port_class.__module__}.{port_class.__name__}'

        try:
            port = port_class(**ps)
            port_id = port.get_id()

            if port_id in _ports_by_id:
                raise PortLoadError(f'A port with id {port_id} already exists')

            _ports_by_id[port.get_id()] = port
            ports.append(port)

            logger.debug('initialized %s (driver %s)', port, port_class_desc)

        except Exception as e:
            if raise_on_error:
                raise PortLoadError(f'Failed to initialize port from driver {port_class_desc}') from e

            logger.error('failed to initialize port from driver %s: %s', port_class_desc, e, exc_info=True)

    # Map IDs
    for port in ports:
        if await port.get_attr('virtual'):
            continue

        old_id = port.get_id()
        new_id = settings.port_mappings.get(old_id)
        if not new_id:
            continue

        if new_id in _ports_by_id:
            if raise_on_error:
                raise PortLoadError(f'Cannot map port {old_id} to {new_id}: new id already exists')

            logger.error('cannot map port %s to %s: new id already exists', old_id, new_id)
            continue

        port = _ports_by_id.get(old_id)
        if not port:
            if raise_on_error:
                raise PortLoadError(f'Cannot map port {old_id} to {new_id}: no such port')

            logger.error('cannot map port %s to %s: no such port', old_id, new_id)
            continue

        try:
            port.map_id(new_id)

        except Exception as e:
            if raise_on_error:
                raise PortLoadError(f'Cannot map port {old_id} to {new_id}') from e

            port.error('cannot map to %s: %s', new_id, e)

        _ports_by_id.pop(old_id)
        _ports_by_id[port.get_id()] = port

    # Load created ports
    for port in ports:
        try:
            await port.load()

        except Exception as e:
            if raise_on_error:
                raise PortLoadError(f'Failed to load {port}') from e

            port.error('failed to load: %s', port, e, exc_info=True)

        if trigger_add:
            await port.trigger_add()

    return ports


async def load_one(cls: Union[str, type], args: Dict[str, Any], trigger_add: bool = True) -> BasePort:
    port_args = [dict(driver=cls, **args)]
    ports = await load(port_args, raise_on_error=True, trigger_add=trigger_add)

    return ports[0]


def get(port_id: str) -> Optional[BasePort]:
    return _ports_by_id.get(port_id)


def get_all() -> List[BasePort]:
    return list(_ports_by_id.values())


async def save_loop() -> None:
    while True:
        try:
            for port in get_all():
                if not port.is_pending_save():
                    continue

                try:
                    await port.save()

                except Exception as e:
                    port.error('save failed: %s', e, exc_info=True)

            await asyncio.sleep(SAVE_INTERVAL)

        except asyncio.CancelledError:
            logger.debug('save loop cancelled')
            break


async def init() -> None:
    global _save_loop_task

    _save_loop_task = asyncio.create_task(save_loop())

    # Use raise_on_error=False because we prefer a partial successful startup rather than a failed one
    await load(settings.ports, raise_on_error=False)


async def cleanup() -> None:

    async def cleanup_port(port: BasePort) -> None:
        await port.disable()
        await port.cleanup()

    if _save_loop_task:
        _save_loop_task.cancel()
        await _save_loop_task

    tasks = [asyncio.create_task(cleanup_port(port)) for port in _ports_by_id.values()]
    if tasks:
        await asyncio.wait(tasks)


async def reset() -> None:
    logger.debug('clearing ports persisted data')
    await persist.remove(BasePort.PERSIST_COLLECTION)
