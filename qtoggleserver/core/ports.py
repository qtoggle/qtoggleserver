
import abc
import asyncio
import copy
import functools
import logging
import sys
import time

from tornado import queues

from qtoggleserver import persist
from qtoggleserver import utils

from qtoggleserver.conf import settings
from qtoggleserver.core import events as core_events
from qtoggleserver.core import expressions as core_expressions
from qtoggleserver.core import main
from qtoggleserver.core import sessions as core_sessions
from qtoggleserver.core import sequences as core_sequences
from qtoggleserver.utils import json as json_utils


TYPE_BOOLEAN = 'boolean'
TYPE_NUMBER = 'number'

CHANGE_REASON_NATIVE = 'N'
CHANGE_REASON_API = 'A'
CHANGE_REASON_SEQUENCE = 'S'
CHANGE_REASON_EXPRESSION = 'E'

logger = logging.getLogger(__name__)

_ports = {}  # indexed by id


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
        'max': 16
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
    'virtual': {
        'type': 'boolean',
        'optional': True
    },
    'online': {
        'type': 'boolean',
        'optional': True
    }
}


class PortError(Exception):
    pass


class InvalidAttributeValue(PortError):
    def __init__(self, attr):
        self.attr = attr

        super().__init__(attr)


class PortTimeout(PortError):
    pass


class BasePort(utils.LoggableMixin, metaclass=abc.ABCMeta):
    PERSIST_COLLECTION = 'ports'

    TYPE = TYPE_BOOLEAN
    DISPLAY_NAME = ''
    UNIT = ''
    WRITABLE = False
    CHOICES = None

    WRITE_VALUE_PAUSE = 0

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

    def __init__(self, port_id):
        utils.LoggableMixin.__init__(self, port_id, logger)

        self._id = port_id
        self._enabled = False
        self._display_name = None
        self._unit = None

        self._sequence = None
        self._expression = None
        self._transform_read = None
        self._transform_write = None

        # attributes cache is used to prevent computing
        # an attribute value more than once per core iteration
        self._attrs_cache = {}

        # cache attribute definitions so that the ATTRDEFS property
        # doesn't need to gather all of them with each access
        self._attrdefs_cache = None

        self._modifiable_attrs = None
        self._non_modifiable_attrs = None

        self._schema = None
        self._value_schema = None

        self._value = None
        self._write_value_queue = queues.Queue()
        self._write_value_task = asyncio.create_task(self._write_value_loop())
        self._asap_value = None
        self._change_reason = CHANGE_REASON_NATIVE

        self._loaded = False

    def __str__(self):
        return 'port {}'.format(self._id)

    def __repr__(self):
        return 'Port({})'.format(self._id)

    def initialize(self):
        pass

    def _get_attrdefs(self):
        if self._attrdefs_cache is None:
            self._attrdefs_cache = dict(self.STANDARD_ATTRDEFS, **self.ADDITIONAL_ATTRDEFS)

        return self._attrdefs_cache

    ATTRDEFS = property(_get_attrdefs)

    def invalidate_attrdefs(self):
        self._attrs_cache = {}
        self._attrdefs_cache = None
        self._modifiable_attrs = None
        self._non_modifiable_attrs = None
        self._schema = None

    def get_non_modifiable_attrs(self):
        if self._non_modifiable_attrs is None:
            self._non_modifiable_attrs = set([n for (n, v) in self.ATTRDEFS.items() if not v.get('modifiable')])

        return self._non_modifiable_attrs

    def get_modifiable_attrs(self):
        if self._modifiable_attrs is None:
            self._modifiable_attrs = set([n for (n, v) in self.ATTRDEFS.items() if v.get('modifiable')])

        return self._modifiable_attrs

    async def get_attrs(self):
        d = {}

        for name in self.ATTRDEFS.keys():
            v = await self.get_attr(name)
            if v is None:
                continue

            d[name] = v

        return d

    def invalidate_attrs(self):
        self._attrs_cache = {}

    def invalidate_attr(self, name):
        self._attrs_cache.pop(name, None)

    async def get_attr(self, name):
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

        return None  # unsupported attribute

    async def set_attr(self, name, value):
        old_value = await self.get_attr(name)
        if old_value is None:
            return  # refuse to set an unsupported attribute

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

        # new attributes might have been added or removed after setting an attribute;
        # therefore new definitions might have appeared or disappeared
        self.invalidate_attrdefs()

        self._attrs_cache[name] = value
        if old_value != value:
            await self.handle_attr_change(name, value)

        if not self.is_loaded():
            return

        # skip an IO loop iteration, allowing setting multiple attributes before triggering a port-update
        await asyncio.sleep(0)
        self.trigger_update()

    async def handle_attr_change(self, name, value):
        method_name = 'handle_{}_change'.format(name)
        method = getattr(self, method_name, None)
        if method:
            try:
                await method(value)

            except Exception as e:
                self.error('%s failed: %s', method_name, e, exc_info=True)

    def get_id(self):
        return self._id

    def map_id(self, new_id):
        self._id = new_id
        self.debug('mapped to %s', new_id)

    async def get_type(self):
        return await self.get_attr('type')

    async def is_writable(self):
        return await self.get_attr('writable')

    async def is_persisted(self):
        return await self.get_attr('persisted')

    def is_enabled(self):
        return self._enabled

    async def enable(self):
        if self._enabled:
            return

        self.debug('enabling')
        self._enabled = True
        self.invalidate_attr('enabled')

        try:
            await self.handle_enable()

        except Exception:
            self.error('failed to enable')
            self._enabled = False

            raise

    async def disable(self):
        if not self._enabled:
            return

        # cancel sequence
        if self._sequence:
            self.debug('canceling current sequence')
            self._sequence.cancel()
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

    async def handle_enable(self):
        pass

    async def handle_disable(self):
        pass

    async def attr_set_enabled(self, value):
        if value:
            await self.enable()

        else:
            await self.disable()

    async def get_expression(self):
        if not await self.is_writable():
            return None

        return self._expression

    async def attr_get_expression(self):
        if not await self.is_writable():
            return None

        if self._expression:
            return str(self._expression)

        else:
            return ''

    async def attr_set_expression(self, sexpression):
        if not await self.is_writable():
            self.debug('refusing to set expression to non-writable port')
            return False

        if self._sequence:
            self.debug('canceling current sequence')
            self._sequence.cancel()

        if not sexpression:
            self._expression = None
            return

        try:
            self.debug('parsing expression "%s"', sexpression)
            expression = core_expressions.parse(self.get_id(), sexpression)

            self.debug('checking for expression circular dependencies')
            await core_expressions.check_loops(self, expression)

        except core_expressions.ExpressionError as e:
            self.error('failed to set expression "%s": %s', sexpression, e)

            raise InvalidAttributeValue('expression') from e

        self.debug('setting expression "%s"', expression)
        self._expression = expression

        main.force_eval_expressions()

    async def attr_get_transform_read(self):
        if self._transform_read:
            return str(self._transform_read)

        else:
            return ''

    async def attr_set_transform_read(self, stransform_read):
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

                if dep != '${}'.format(self._id):
                    raise core_expressions.ExpressionError('transform expression depends other ports')

            self.debug('setting read transform "%s"', transform_read)
            self._transform_read = transform_read

        except core_expressions.ExpressionError as e:
            self.error('failed to set transform read expression "%s": %s', stransform_read, e)

            raise InvalidAttributeValue('transform_read') from e

    async def attr_get_transform_write(self):
        if not await self.is_writable():
            return None  # only writable ports have transform_write attributes

        if self._transform_write:
            return str(self._transform_write)

        else:
            return ''

    async def attr_set_transform_write(self, stransform_write):
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

                if dep != '${}'.format(self._id):
                    raise core_expressions.ExpressionError('transform expression depends other ports')

            self.debug('setting write transform "%s"', transform_write)
            self._transform_write = transform_write

        except core_expressions.ExpressionError as e:
            self.error('failed to set transform write expression "%s": %s', stransform_write, e)

            raise InvalidAttributeValue('transform_write') from e

    async def read_value(self):
        raise NotImplementedError()

    async def write_value(self, value):
        pass

    def get_value(self):
        return self._value

    def get_change_reason(self):
        return self._change_reason

    def reset_change_reason(self):
        self._change_reason = CHANGE_REASON_NATIVE

    async def _write_value_queued(self, value, reason):
        done = asyncio.get_running_loop().create_future()

        await self._write_value_queue.put((value, reason, done))

        # wait for actual write_value operation to be done
        await done

    async def _write_value_loop(self):
        while True:
            try:
                value, reason, done = await self._write_value_queue.get()

                try:
                    result = await self._write_value(value, reason)
                    if not done.done():
                        done.set_result(result)

                except Exception:
                    done.set_exception(sys.exc_info()[1])

                await asyncio.sleep(await self.get_attr('write_value_pause'))

            except asyncio.CancelledError:
                self.debug('write value task cancelled')
                break

    async def _write_value(self, value, reason):
        self._last_write_value_time = time.time()
        self._change_reason = reason

        await self.write_value(value)
        await main.update()

    async def set_value(self, value, reason):
        if self._transform_write:
            # temporarily set the port value to the new value,
            # so that the write transform expression takes the new
            # value into consideration when evaluating the result
            prev_value = self._value
            self._value = value
            value = await self.adapt_value_type(self._transform_write.eval())
            self._value = prev_value

        try:
            await self._write_value_queued(value, reason)
            self.debug('wrote value %s (reason=%s)', json_utils.dumps(value), reason)

        except Exception:
            self.error('failed to write value %s (reason=%s)', json_utils.dumps(value), reason, exc_info=True)

            raise

    def set_value_fire_and_forget(self, value, reason):
        asyncio.create_task(self.set_value(value, reason))

    def push_value(self, value, reason):
        already_scheduled = self._asap_value is not None
        self._asap_value = value

        if not already_scheduled:
            async def set_value():
                asap_value = self._asap_value
                self._asap_value = None
                await self.set_value(asap_value, reason)

            asyncio.create_task(set_value())

        else:
            self.debug('will set value %s asap', json_utils.dumps(value))

    async def read_transformed_value(self):
        value = await self.read_value()
        if value is None:
            return None

        if self._transform_read:
            # temporarily set the new value to the port,
            # so that the read transform expression works as expected

            old_value = self._value
            self._value = value
            value = await self.adapt_value_type(self._transform_read.eval())
            self._value = old_value

        return value

    async def adapt_value_type(self, value):
        return self.adapt_value_type_sync(await self.get_type(), await self.get_attr('integer'), value)

    @staticmethod
    def adapt_value_type_sync(typ, integer, value):
        if value is None:
            return None

        if typ == TYPE_BOOLEAN:
            return bool(value)

        else:
            # round the value if port accepts only integers
            if integer:
                return int(value)

            return float(value)

    async def set_sequence(self, values, delays, repeat):
        if self._sequence:
            self.debug('canceling current sequence')
            self._sequence.cancel()
            self._sequence = None

        if values:
            callback = functools.partial(self.set_value_fire_and_forget, reason=CHANGE_REASON_SEQUENCE)
            self._sequence = core_sequences.Sequence(values, delays, repeat, callback, self._on_sequence_finish)

            self.debug('installing sequence')
            self._sequence.start()

    async def _on_sequence_finish(self):
        self.debug('sequence finished')

        self._sequence = None
        if await self.is_persisted():
            await self.save()

    def heart_beat(self):
        pass

    def heart_beat_second(self):
        pass

    @staticmethod
    def add_timeout(timeout, callback, *args, **kwargs):
        callback = functools.partial(callback, *args, **kwargs)

        return main.loop.call_later(timeout / 1000.0, callback)

    @staticmethod
    def cancel_timeout(handle):
        handle.cancel()

    async def to_json(self):
        attrs = await self.get_attrs()

        if self._enabled:
            attrs['value'] = self._value

        else:
            attrs['value'] = None

        attrdefs = copy.deepcopy(self.ADDITIONAL_ATTRDEFS)
        for attrdef in attrdefs.values():
            attrdef.pop('pattern', None)

        attrs['definitions'] = attrdefs

        return attrs

    async def load(self):
        self.debug('loading persisted data')

        data = persist.get(self.PERSIST_COLLECTION, self.get_id()) or {}
        await self.load_from_data(data)

        self.set_loaded()
        self.initialize()

    async def load_from_data(self, data):
        attrs_start = ['enabled']  # these will be loaded first, in this order
        attrs_end = ['expression']  # these will be loaded last, in this order

        attr_items = data.items()
        attr_items = [a for a in attr_items if (a[0] not in attrs_start) and (a[0] not in attrs_end)]

        attr_items_start = []
        for n in attrs_start:
            v = data.get(n)
            if v is not None:
                attr_items_start.append((n, v))

        # sort the rest of the attributes alphabetically
        attr_items.sort(key=lambda i: i[0])

        attr_items_end = []
        for n in attrs_end:
            v = data.get(n)
            if v is not None:
                attr_items_end.append((n, v))

        attr_items = attr_items_start + attr_items + attr_items_end

        for name, value in attr_items:
            if name in ('id', 'value'):
                continue  # value is also among the persisted fields

            try:
                self.debug('loading %s = %s', name, json_utils.dumps(value))
                await self.set_attr(name, value)

            except Exception as e:
                self.error('failed to set attribute %s = %s: %s', name, json_utils.dumps(value), e)

        # value
        if await self.is_persisted() and data.get('value') is not None:
            self._value = data['value']
            self.debug('loaded value = %s', json_utils.dumps(self._value))

            if await self.is_writable():
                # write the just-loaded value to the port
                value = self._value
                if self._transform_write:
                    value = await self.adapt_value_type(self._transform_write.eval())

                await self.write_value(value)

        elif self.is_enabled():
            try:
                value = await self.read_transformed_value()
                if value is not None:
                    self._value = value
                    self.debug('read value = %s', json_utils.dumps(self._value))

            except Exception as e:
                self.error('failed to read value: %s', e, exc_info=True)

    async def save(self):
        if not self.is_loaded():
            return

        d = await self.prepare_for_save()

        self.debug('persisting data')
        persist.replace(self.PERSIST_COLLECTION, self._id, d)

    async def prepare_for_save(self):
        # value
        d = {
            'id': self.get_id()
        }

        if await self.is_persisted():
            d['value'] = self._value

        else:
            d['value'] = None

        # attributes
        for name in self.get_modifiable_attrs():
            v = await self.get_attr(name)
            if v is None:
                continue

            d[name] = v

        return d

    async def cleanup(self):
        # cancel sequence
        if self._sequence:
            self.debug('canceling current sequence')
            self._sequence.cancel()
            self._sequence = None

        self._write_value_task.cancel()
        await self._write_value_task

    def is_loaded(self):
        return self._loaded

    def set_loaded(self):
        self._loaded = True

    def remove(self, persisted_data=True):
        # cancel sequence
        if self._sequence:
            self.debug('canceling current sequence')
            self._sequence.cancel()
            self._sequence = None

        _ports.pop(self._id, None)

        if persisted_data:
            self.debug('removing persisted data')
            persist.remove(self.PERSIST_COLLECTION, filt={'id': self._id})

        self.trigger_remove()

        return True

    def trigger_add(self):
        event = core_events.PortAdd(self)
        core_sessions.push(event)
        core_events.handle_event(event)

    def trigger_remove(self):
        event = core_events.PortRemove(self)
        core_sessions.push(event)
        core_events.handle_event(event)

    def trigger_update(self):
        event = core_events.PortUpdate(self)
        core_sessions.push(event)
        core_events.handle_event(event)

    def trigger_value_change(self):
        event = core_events.ValueChange(self)
        core_sessions.push(event)
        core_events.handle_event(event)

    async def get_schema(self):
        if self._schema is None:
            self._schema = {
                'type': 'object',
                'properties': {},
                'additionalProperties': False
            }

            for name, attrdef in self.ATTRDEFS.items():
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

    async def get_value_schema(self):
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

                else:  # assuming number
                    self._value_schema['type'] = 'number'

        return self._value_schema


class Port(BasePort, metaclass=abc.ABCMeta):
    def __init__(self, port_id):
        super().__init__(port_id)

        self._tag = ''
        self._persisted = False


async def load(port_settings):
    port_driver_classes = {}
    ports = []

    for port_spec in port_settings:
        driver = port_spec.pop('driver', None)
        if not driver:
            logger.error('ignoring port with no driver')
            continue

        if isinstance(driver, str):
            if driver not in port_driver_classes:
                try:
                    logger.debug('loading port driver %s', driver)
                    port_driver_classes[driver] = utils.load_attr(driver)

                except Exception as e:
                    logger.error('failed to load port driver %s: %s', driver, e, exc_info=True)

                    continue

            port_class = port_driver_classes[driver]

        else:
            port_class = driver

        port_class_desc = '{}.{}'.format(port_class.__module__, port_class.__name__)

        try:
            value = port_spec.pop('value', None)  # initial value
            port = port_class(**port_spec)
            if value is not None:
                port._value = value

            _ports[port.get_id()] = port
            ports.append(port)

            logger.debug('initialized %s (driver %s)', port, port_class_desc)

        except Exception as e:
            logger.error('failed to initialize port from driver %s: %s', port_class_desc, e, exc_info=True)

    for old_id, new_id in settings.port_mappings.items():
        if new_id in _ports:
            logger.error('cannot map port %s: new id already exists', old_id, new_id)
            continue

        port = _ports.get(old_id)
        if not port:
            logger.error('cannot map port %s to %s: no such port', old_id, new_id)
            continue

        try:
            port.map_id(new_id)

        except Exception as e:
            port.error('cannot map to %s: %s', new_id, e)

        _ports.pop(old_id)
        _ports[port.get_id()] = port

    for port in ports:
        try:
            await port.load()

        except Exception as e:
            logger.error('failed to load %s: %s', port, e, exc_info=True)

        port.trigger_add()

    return ports


async def load_one(cls, args):
    ports = await load([dict(driver=cls, **args)])
    if not ports:
        return None

    return ports[0]


def get(port_id):
    return _ports.get(port_id)


def all_ports():
    return _ports.values()


async def cleanup():
    for port in _ports.values():
        await port.cleanup()


def reset():
    logger.debug('clearing ports persisted data')
    persist.remove(BasePort.PERSIST_COLLECTION)
