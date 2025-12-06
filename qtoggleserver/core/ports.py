from __future__ import annotations

import abc
import asyncio
import copy
import functools
import inspect
import logging
import time

from collections import deque
from collections.abc import Callable
from typing import Any

from qtoggleserver import persist
from qtoggleserver.conf import settings
from qtoggleserver.core import events as core_events
from qtoggleserver.core import expressions as core_expressions
from qtoggleserver.core import history as core_history
from qtoggleserver.core import sequences as core_sequences
from qtoggleserver.core.expressions import exceptions as expressions_exceptions
from qtoggleserver.core.typing import (
    Attribute,
    AttributeDefinitions,
    Attributes,
    GenericJSONDict,
    NullablePortValue,
    PortValue,
)
from qtoggleserver.utils import asyncio as asyncio_utils
from qtoggleserver.utils import dynload as dynload_utils
from qtoggleserver.utils import json as json_utils
from qtoggleserver.utils import logging as logging_utils


TYPE_BOOLEAN = "boolean"
TYPE_NUMBER = "number"

logger = logging.getLogger(__name__)

_ports_by_id: dict[str, BasePort] = {}
_save_loop_task: asyncio.Task | None = None


def _attrdef_unit_enabled(port: BasePort) -> bool:
    return port.get_type() == TYPE_NUMBER


STANDARD_ATTRDEFS = {
    "id": {"type": "string"},
    "display_name": {"type": "string", "modifiable": True, "max": 64},
    "type": {
        "type": "string",
        "choices": [{"value": "boolean", "display_name": "Boolean"}, {"value": "number", "display_name": "Number"}],
    },
    "unit": {"type": "string", "modifiable": True, "max": 16, "enabled": _attrdef_unit_enabled},
    "writable": {"type": "boolean"},
    "enabled": {"type": "boolean", "modifiable": True},
    "min": {"type": "number", "optional": True},
    "max": {"type": "number", "optional": True},
    "integer": {"type": "boolean", "optional": True},
    "step": {"type": "number", "optional": True},
    "choices": {"type": "[]", "optional": True},  # TODO data type uncertain
    "tag": {
        "type": "string",
        "optional": True,
        "modifiable": True,
        "max": 64,
    },
    "expression": {
        "type": "string",
        "optional": True,
        "modifiable": True,
        "max": 10240,
    },
    "transform_read": {
        "type": "string",
        "optional": True,
        "modifiable": True,
        "max": 10240,
    },
    "transform_write": {
        "type": "string",
        "optional": True,
        "modifiable": True,
        "max": 10240,
    },
    "persisted": {"type": "boolean", "optional": True, "modifiable": True},
    "internal": {"type": "boolean", "optional": True, "modifiable": True},
    "virtual": {"type": "boolean", "optional": True},
    "online": {"type": "boolean", "optional": True},
    "history_interval": {
        "type": "number",
        "integer": True,
        "min": -1,
        "max": 2147483647,
        "optional": True,
        "modifiable": True,
        "enabled": lambda p: core_history.is_enabled(),
    },
    "history_retention": {
        "type": "number",
        "integer": True,
        "min": 0,
        "max": 2147483647,
        "optional": True,
        "modifiable": True,
        "enabled": lambda p: core_history.is_enabled(),
    },
}


class PortError(Exception):
    pass


class PortLoadError(PortError):
    pass


class PortReadError(PortError):
    pass


class PortWriteError(PortError):
    pass


class SkipRead(PortReadError):
    pass


class InvalidAttributeValue(PortError):
    def __init__(self, attr: str, details: GenericJSONDict | None = None) -> None:
        self.attr: str = attr
        self.details: GenericJSONDict | None = details

        super().__init__(attr)


class PortTimeout(PortError):
    pass


def skip_write_unavailable(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(self: BasePort, value: NullablePortValue) -> None:
        if value is None:
            return
        await func(self, value)

    return wrapper


class BasePort(logging_utils.LoggableMixin, metaclass=abc.ABCMeta):
    PERSIST_COLLECTION = "ports"

    DISPLAY_NAME = ""
    TYPE = TYPE_BOOLEAN
    WRITABLE = False
    UNIT = ""
    TAG = ""
    CHOICES = None
    MIN = None
    MAX = None
    INTEGER = False
    STEP = None
    PERSISTED = False
    INTERNAL = False

    WRITE_QUEUE_SIZE = 16

    STANDARD_ATTRDEFS = STANDARD_ATTRDEFS

    ADDITIONAL_ATTRDEFS = {}
    """
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
    }"""

    def __init__(self, port_id: str) -> None:
        logging_utils.LoggableMixin.__init__(self, port_id, logger)

        self._id: str = port_id
        self._display_name: str | None = self.DISPLAY_NAME
        self._type: str = self.TYPE
        self._writable: bool = self.WRITABLE
        self._enabled: bool = False
        self._unit: str | None = self.UNIT
        self._tag: str = self.TAG
        self._choices: list[dict[str, str | int]] | None = self.CHOICES
        self._min: int | float | None = self.MIN
        self._max: int | float | None = self.MAX
        self._integer: bool = self.INTEGER
        self._step: int | float | None = self.STEP
        self._persisted: bool = self.PERSISTED
        self._internal: bool = self.INTERNAL

        self._sequence: core_sequences.Sequence | None = None
        self._expression: core_expressions.Expression | None = None
        self._transform_read: core_expressions.Expression | None = None
        self._transform_write: core_expressions.Expression | None = None

        self._history_interval: int = 0
        self._history_retention: int = 0
        self._history_last_timestamp: int = 0

        # Attributes cache is used to prevent computing an attribute value more than once per core iteration
        self._attrs_cache: Attributes = {}

        # Cache attribute definitions
        self._standard_attrdefs_cache: AttributeDefinitions | None = None
        self._additional_attrdefs_cache: AttributeDefinitions | None = None

        self._schema: GenericJSONDict | None = None
        self._value_schema: GenericJSONDict | None = None

        self._last_read_value: tuple[NullablePortValue, int] | None = None
        self._read_value_lock = asyncio.Lock()

        # Value that's currently being written
        self._writing_value: NullablePortValue = None
        self._last_written_value: tuple[NullablePortValue, int] | None = None
        self._write_value_lock = asyncio.Lock()

        self._write_queue: deque[PortValue] = deque(maxlen=self.WRITE_QUEUE_SIZE)
        self._write_task: asyncio.Task | None = None
        try:
            asyncio.get_running_loop()
            self._write_task = asyncio.create_task(self._write_loop())
        except RuntimeError:
            pass

        self._save_lock: asyncio.Lock = asyncio.Lock()
        self._pending_save: bool = False

        self._loaded: bool = False

    def __str__(self) -> str:
        return f"port {self._id}"

    def __repr__(self) -> str:
        return f"Port({self._id})"

    def initialize(self) -> None:
        pass

    async def get_attrdefs(self) -> AttributeDefinitions:
        if self._standard_attrdefs_cache is None:
            self._standard_attrdefs_cache = dict(await self.get_standard_attrdefs())
            for name, attrdef in list(self._standard_attrdefs_cache.items()):
                enabled = attrdef.get("enabled", True)
                if callable(enabled):
                    enabled = enabled(self)
                if inspect.isawaitable(enabled):
                    enabled = await enabled
                if not enabled:
                    self._standard_attrdefs_cache.pop(name)

        if self._additional_attrdefs_cache is None:
            self._additional_attrdefs_cache = dict(await self.get_additional_attrdefs())
            for name, attrdef in list(self._additional_attrdefs_cache.items()):
                enabled = attrdef.get("enabled", True)
                if callable(enabled):
                    enabled = enabled(self)
                if inspect.isawaitable(enabled):
                    enabled = await enabled
                if not enabled:
                    self._additional_attrdefs_cache.pop(name)

        return self._standard_attrdefs_cache | self._additional_attrdefs_cache

    async def get_standard_attrdefs(self) -> AttributeDefinitions:
        return self.STANDARD_ATTRDEFS

    async def get_additional_attrdefs(self) -> AttributeDefinitions:
        return self.ADDITIONAL_ATTRDEFS

    def invalidate_attrdefs(self) -> None:
        self._attrs_cache = {}
        self._standard_attrdefs_cache = None
        self._additional_attrdefs_cache = None
        self._schema = None

    async def get_non_modifiable_attrs(self) -> set[str]:
        attrdefs = await self.get_attrdefs()
        return {n for (n, v) in attrdefs.items() if not v.get("modifiable")}

    async def get_modifiable_attrs(self) -> set[str]:
        attrdefs = await self.get_attrdefs()
        return {n for (n, v) in attrdefs.items() if v.get("modifiable")}

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

    async def get_attr(self, name: str) -> Attribute | None:
        value = self._attrs_cache.get(name)
        if value is not None:
            return value

        method = getattr(self, "attr_get_" + name, getattr(self, "attr_is_" + name, None))
        if method:
            value = method()
            if inspect.isawaitable(value):
                value = await value
            if value is not None:
                self._attrs_cache[name] = value
                return value

        value = getattr(self, "_" + name, None)
        if value is not None:
            self._attrs_cache[name] = value
            return value

        value = await self.attr_get_value(name)
        if value is not None:
            self._attrs_cache[name] = value
            return value

        method = getattr(self, "attr_get_default_" + name, getattr(self, "attr_is_default_" + name, None))
        if method:
            value = method()
            if inspect.isawaitable(value):
                value = await value
            if value is not None:
                self._attrs_cache[name] = value
                return value

        return None  # unsupported attribute

    async def set_attr(self, name: str, value: Attribute) -> None:
        old_value = await self.get_attr(name)
        if old_value is None:
            return

        if old_value == value:
            return

        method = getattr(self, "attr_set_" + name, None)
        if method:
            try:
                result = method(value)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                self.error("failed to set attribute %s = %s", name, json_utils.dumps(value), exc_info=True)

                raise
        elif hasattr(self, "_" + name):
            setattr(self, "_" + name, value)
        else:
            await self.attr_set_value(name, value)

        # New attributes might have been added or removed after setting an attribute; therefore new definitions might
        # have appeared or disappeared; this will also invalidate attributes cache.
        self.invalidate_attrdefs()

        if self.is_loaded():
            await main.update()  # TODO: don't update immediately, batch multiple attribute sets

            # Skip an IO loop iteration, allowing setting multiple attributes before triggering a port-update
            await asyncio.sleep(0)
            await self.trigger_update()  # TODO: don't trigger immediately, batch multiple attribute sets

            await self.handle_attr_change(name, value)

    def invalidate_attr(self, name: str) -> None:
        self._attrs_cache.pop(name, None)

    async def handle_attr_change(self, name: str, value: Attribute) -> None:
        method_name = f"handle_{name}"
        method = getattr(self, method_name, None)
        if method:
            try:
                await method(value)
            except Exception as e:
                self.error("%s failed: %s", method_name, e, exc_info=True)

    async def attr_get_value(self, name: str) -> Attribute | None:
        return None

    async def attr_set_value(self, name: str, value: Attribute) -> None:
        return None

    async def get_display_name(self) -> str:
        return await self.get_attr("display_name") or self._id

    async def get_display_value(self, value: NullablePortValue = None) -> str:
        choices = await self.get_attr("choices")
        unit = await self.get_attr("unit")
        if value is None:
            value = self.get_last_read_value()

        if value is None:
            return "unknown"  # TODO: i18n

        if choices:
            for choice in choices:
                if choice["value"] == value:
                    return choice["display_name"]

        if self.get_type() == TYPE_BOOLEAN:
            value_str = "on" if value else "off"  # TODO: i18n
        else:
            value_str = str(value)

        if unit:
            return f"{value_str}{unit}"
        else:
            return value_str

    def get_id(self) -> str:
        return self._id

    def map_id(self, new_id: str) -> None:
        self._id = new_id
        self.debug("mapped to %s", new_id)
        self.set_logger_name(new_id)

    def get_type(self) -> str:
        # This shorthand method is not implemented as an attribute getter to avoid overhead of async calls
        return self._type

    async def is_writable(self) -> bool:
        return await self.get_attr("writable")

    async def is_persisted(self) -> bool:
        return await self.get_attr("persisted")

    async def is_internal(self) -> bool:
        return await self.get_attr("internal")

    def is_integer(self) -> bool:
        # This shorthand method is not implemented as an attribute getter to avoid overhead of async calls
        return self._integer

    def is_enabled(self) -> bool:
        # This shorthand method is not implemented as an attribute getter to avoid overhead of async calls
        return self._enabled

    async def enable(self) -> None:
        if self._enabled:
            return

        self.debug("enabling")
        self._enabled = True
        self.invalidate_attr("enabled")

        # Reset port expression
        if self._expression:
            sexpression = str(self._expression)
            self.debug('resetting expression "%s"', sexpression)
            self._expression = core_expressions.parse(self.get_id(), sexpression, role=core_expressions.Role.VALUE)

            main.force_eval_expressions(self)

        try:
            await self.handle_enable()
        except Exception:
            self.error("failed to enable")
            self._enabled = False

            raise

    async def disable(self) -> None:
        if not self._enabled:
            return

        # Cancel sequence
        if self._sequence:
            self.debug("canceling current sequence")
            await self._sequence.cancel()
            self._sequence = None

        self.debug("disabling")
        self._enabled = False
        self.invalidate_attr("enabled")

        try:
            await self.handle_disable()
        except Exception:
            self.error("failed to disable")
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

    def get_expression(self) -> core_expressions.Expression | None:
        return self._expression

    async def attr_get_expression(self) -> str | None:
        writable = self._attrs_cache.get("writable")  # use cached value if available, to avoid unnecessary await
        if writable is None:
            writable = await self.is_writable()

        if not writable:
            return None

        if self._expression:
            return str(self._expression)
        else:
            return ""

    async def attr_set_expression(self, sexpression: str) -> None:
        writable = self._attrs_cache.get("writable")  # use cached value if available, to avoid unnecessary await
        if writable is None:
            writable = await self.is_writable()

        if not writable:
            self.error("refusing to set expression on non-writable port")
            raise PortError("Cannot set expression on non-writable port")

        if self._sequence:
            self.debug("canceling current sequence")
            await self._sequence.cancel()
            self._sequence = None

        if not sexpression:
            self._expression = None
            return

        try:
            self.debug('parsing expression "%s"', sexpression)
            expression = core_expressions.parse(self.get_id(), sexpression, role=core_expressions.Role.VALUE)
        except expressions_exceptions.ExpressionParseError as e:
            self.error('failed to set expression "%s": %s', sexpression, e)
            raise InvalidAttributeValue("expression", details=e.to_json()) from e

        self.debug('setting expression "%s"', expression)
        self._expression = expression

        main.force_eval_expressions(self)

    async def attr_get_transform_read(self) -> str:
        if self._transform_read:
            return str(self._transform_read)
        else:
            return ""

    async def attr_set_transform_read(self, stransform_read: str) -> None:
        if not stransform_read:
            self._transform_read = None
            return

        try:
            self.debug('parsing expression "%s"', stransform_read)
            transform_read = core_expressions.parse(
                self.get_id(), stransform_read, role=core_expressions.Role.TRANSFORM_READ
            )

            deps = transform_read.get_deps()
            for dep in deps:
                if dep.startswith("$") and len(dep) > 1 and dep[1:] != self._id:
                    raise expressions_exceptions.NonSelfDependency(port_id=dep[1:], pos=stransform_read.index(dep))

            self.debug('setting read transform "%s"', transform_read)
            self._transform_read = transform_read
        except expressions_exceptions.ExpressionParseError as e:
            self.error('failed to set transform read expression "%s": %s', stransform_read, e)

            raise InvalidAttributeValue("transform_read", details=e.to_json()) from e

    async def attr_get_transform_write(self) -> str | None:
        writable = self._attrs_cache.get("writable")  # use cached value if available, to avoid unnecessary await
        if writable is None:
            writable = await self.is_writable()

        if not writable:
            return None  # only writable ports have transform_write attributes

        if self._transform_write:
            return str(self._transform_write)
        else:
            return ""

    async def attr_set_transform_write(self, stransform_write: str) -> None:
        if not stransform_write:
            self._transform_write = None
            return

        try:
            self.debug('parsing expression "%s"', stransform_write)
            transform_write = core_expressions.parse(
                self.get_id(), stransform_write, role=core_expressions.Role.TRANSFORM_WRITE
            )

            deps = transform_write.get_deps()
            for dep in deps:
                if dep.startswith("$") and len(dep) > 1 and dep[1:] != self._id:
                    raise expressions_exceptions.NonSelfDependency(port_id=dep[1:], pos=stransform_write.index(dep))

            self.debug('setting write transform "%s"', transform_write)
            self._transform_write = transform_write
        except expressions_exceptions.ExpressionParseError as e:
            self.error('failed to set transform write expression "%s": %s', stransform_write, e)

            raise InvalidAttributeValue("transform_write", details=e.to_json()) from e

    async def get_history_interval(self) -> int:
        return await self.get_attr("history_interval")

    async def get_history_retention(self) -> int:
        return await self.get_attr("history_retention")

    def get_history_last_timestamp(self) -> int:
        return self._history_last_timestamp

    def set_history_last_timestamp(self, timestamp: int) -> None:
        self._history_last_timestamp = timestamp

    @abc.abstractmethod
    async def read_value(self) -> NullablePortValue:
        return None

    def get_last_read_value(self) -> NullablePortValue:
        return self._last_read_value[0] if self._last_read_value else None

    def set_last_read_value(self, value: NullablePortValue) -> None:
        self._last_read_value = value, int(time.time() * 1000)

    async def read_transformed_value(self) -> NullablePortValue:
        value = None
        async with self._read_value_lock:
            try:
                value = await self.read_value()
            except Exception:
                raise

        if self._transform_read:
            context = self._make_eval_context(port_values={self.get_id(): value})
            try:
                value = self.adapt_value_type(await self._transform_read.eval(context))
            except expressions_exceptions.ValueUnavailable:
                value = None

        return value

    def is_reading(self) -> bool:
        return self._read_value_lock.locked()

    async def write_value(self, value: NullablePortValue) -> None:
        pass

    async def _write_value_safe(self, value: NullablePortValue) -> None:
        """Write a value to the port, ensuring only one write at a time and updating the last written value."""

        async with self._write_value_lock:
            try:
                self._writing_value = value
                await self.write_value(value)
                self._last_written_value = value, int(time.time() * 1000)
            finally:
                self._writing_value = None

        # Do an update after every confirmed write
        await asyncio.sleep(settings.core.tick_interval / 1000.0)
        await main.update()

    def get_pending_value(self) -> NullablePortValue:
        """Return the most recent value that's about to be written to the port but hasn't been, yet."""

        try:
            return self._write_queue[-1]
        except IndexError:
            return self._writing_value

    def get_last_written_value(self) -> NullablePortValue:
        return self._last_written_value[0] if self._last_written_value else None

    async def eval_and_push_write(self, now_ms: int) -> None:
        """Evaluate the port's expression and push the resulting value to the write queue. Shield any evaluation
        exceptions from caller, but make sure to log them."""

        port_values = {p.get_id(): p.get_last_value() for p in get_all() if p.is_enabled()}
        context = self._make_eval_context(port_values, now_ms)
        expression = self.get_expression()

        try:
            value = await expression.eval(context)
        except expressions_exceptions.ExpressionEvalException as e:
            self.debug('evaluation did not complete for expression "%s": %s', expression, e)
            return
        except Exception as e:
            self.error('failed to evaluate expression "%s": %s', expression, e, exc_info=True)
            return

        assert value is not None, "Expression evaluated to None"

        adapted_value = self.adapt_value_type(value)
        self.debug(
            'expression "%s" evaluated to %s (adapted to %s)',
            expression,
            json_utils.dumps(value),
            json_utils.dumps(adapted_value),
        )

        # Only write value to port if it differs from the last value
        if self.get_last_value() != adapted_value:
            self._write_queue.append(adapted_value)

    async def _write_loop(self) -> None:
        try:
            while True:
                try:
                    value = self._write_queue.pop()
                except IndexError:
                    await asyncio.sleep(settings.core.tick_interval / 1000.0)
                    continue

                try:
                    await self.transform_and_write_value(value)
                except Exception:
                    self.error("eval failed", exc_info=True)
                    await asyncio.sleep(settings.core.tick_interval / 1000.0)
        except asyncio.CancelledError:
            self.debug("eval task cancelled")

    async def _eval_and_write(self, context: core_expressions.EvalContext) -> None:
        expression = self.get_expression()

        try:
            value = await expression.eval(context)
        except expressions_exceptions.ExpressionEvalException as e:
            self.debug('evaluation did not complete for expression "%s": %s', expression, e)
            return
        except Exception as e:
            self.error('failed to evaluate expression "%s": %s', expression, e, exc_info=True)
            return

        adapted_value = self.adapt_value_type(value)
        if adapted_value is not None:
            self.debug(
                'expression "%s" evaluated to %s (adapted to %s)',
                expression,
                json_utils.dumps(value),
                json_utils.dumps(adapted_value),
            )

            # Only write value to port if it differs from the last written value
            if not self._last_written_value or self._last_written_value[0] != adapted_value:
                try:
                    await self.transform_and_write_value(adapted_value)
                except Exception as e:
                    self.error("failed to write value: %s", e)

    async def transform_and_write_value(self, value: NullablePortValue) -> None:
        """Apply write transform (if any) and write the value to the port."""

        value_str = json_utils.dumps(value)

        if self._transform_write:
            context = self._make_eval_context(port_values={self.get_id(): value})
            try:
                value = self.adapt_value_type(await self._transform_write.eval(context))
            except expressions_exceptions.ValueUnavailable:
                value = None
            value_str = f"{value_str} ({json_utils.dumps(value)} after write transform)"

        try:
            self.debug("writing value %s", value_str)
            await self._write_value_safe(value)
            self.debug("wrote value %s", value_str)
        except Exception:
            self.error("failed to write value %s", value_str, exc_info=True)
            raise

    def _make_eval_context(
        self, port_values: dict[str, NullablePortValue], now_ms: int = 0
    ) -> core_expressions.EvalContext:
        now_ms = now_ms or int(time.time() * 1000)
        return core_expressions.EvalContext(port_values, now_ms)

    def get_last_value(self) -> NullablePortValue:
        """Returns the most recent value known to the port, preferring pending and last written values over last read
        value.
        """

        # Pending value is always the most recent known value
        pending_value = self.get_pending_value()
        if pending_value is not None:
            return pending_value

        if self._last_written_value:
            if self._last_read_value:
                if self._last_read_value[1] > self._last_written_value[1]:
                    return self._last_read_value[0]

            return self._last_written_value[0]

        if self._last_read_value:
            return self._last_read_value[0]

        return None

    def adapt_value_type(self, value: NullablePortValue) -> NullablePortValue:
        if value is None:
            return None

        if self.get_type() == TYPE_BOOLEAN:
            return bool(value)
        else:
            # Round the value if port accepts only integers
            if self.is_integer():
                return int(value)

            return float(value)

    async def set_sequence(self, values: list[PortValue], delays: list[int], repeat: int) -> None:
        if self._sequence:
            self.debug("canceling current sequence")
            await self._sequence.cancel()
            self._sequence = None

        if values:
            self._sequence = core_sequences.Sequence(
                values, delays, repeat, self.transform_and_write_value_fire_and_forget, self._on_sequence_finish
            )

            self.debug("installing sequence")
            self._sequence.start()

    def transform_and_write_value_fire_and_forget(self, value: NullablePortValue) -> None:
        asyncio_utils.fire_and_forget(self.transform_and_write_value(value))

    async def _on_sequence_finish(self) -> None:
        self.debug("sequence finished")

        self._sequence = None
        if await self.is_persisted():
            self.save_asap()

    def heart_beat_second(self) -> None:
        pass

    async def to_json(self) -> GenericJSONDict:
        attrs: GenericJSONDict = await self.get_attrs()
        attrs = dict(attrs)

        if self._enabled:
            attrs["value"] = self._last_read_value[0] if self._last_read_value else None
            attrs["pending_value"] = self.get_pending_value()
        else:
            attrs["value"] = None
            attrs["pending_value"] = None

        attrdefs: AttributeDefinitions = copy.deepcopy(await self.get_additional_attrdefs())
        for attrdef in attrdefs.values():
            # Remove unwanted fields from attribute definition
            for name in list(attrdef):
                if name.startswith("_"):
                    attrdef.pop(name)
            attrdef.pop("pattern", None)

        attrs["definitions"] = attrdefs

        return attrs

    async def load(self) -> None:
        self.debug("loading persisted data")

        data = await persist.get(self.PERSIST_COLLECTION, self.get_id()) or {}
        await self.load_from_data(data)

        self.set_loaded()
        self.initialize()

    async def reset(self) -> None:
        self.debug("resetting persisted data")
        await self.load_from_data(data={})
        self.invalidate_attrdefs()

    async def load_from_data(self, data: GenericJSONDict) -> None:
        attrs_start = ["enabled"]  # these will be loaded first, in this order
        attrs_end = ["expression"]  # these will be loaded last, in this order

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

        attrdefs = await self.get_attrdefs()

        for name, value in attr_items:
            if name in ("id", "value", "pending_value"):
                continue  # value is also among the persisted fields

            attrdef = attrdefs.get(name)
            if not attrdef:
                continue  # don't load attribute w/o definition
            if attrdef.get("persisted") is False:
                continue  # don't load attributes marked as non-persisted

            try:
                self.debug("loading %s = %s", name, json_utils.dumps(value))
                await self.set_attr(name, value)
            except Exception as e:
                self.error("failed to set attribute %s = %s: %s", name, json_utils.dumps(value), e)

        # value
        if await self.is_persisted() and data.get("value") is not None:
            self._last_read_value = data["value"], int(time.time() * 1000)
            self.debug("loaded value = %s", json_utils.dumps(data["value"]))

            if await self.is_writable():
                # Write the just-loaded value to the port
                value = data["value"]
                if self._transform_write:
                    try:
                        value = self.adapt_value_type(
                            await self._transform_write.eval(
                                self._make_eval_context(port_values={self.get_id(): value})
                            )
                        )
                    except expressions_exceptions.ValueUnavailable:
                        value = None

                await self.write_value(value)
        elif self.is_enabled():
            try:
                value = await self.read_transformed_value()
            except SkipRead:
                pass
            except Exception as e:
                self.error("failed to read value: %s", e, exc_info=True)
            else:
                self._last_read_value = value, int(time.time() * 1000)
                self.debug("read value = %s", json_utils.dumps(value))

        # various
        self._history_last_timestamp = data.get("history_last_timestamp", 0)

    async def save(self) -> None:
        if not self.is_loaded():
            return

        self.debug("persisting data")

        async with self._save_lock:
            d = await self.prepare_for_save()
            await persist.replace(self.PERSIST_COLLECTION, self._id, d)

        self._pending_save = False

    async def prepare_for_save(self) -> GenericJSONDict:
        # value
        d: GenericJSONDict = {
            "id": self.get_id(),
            "history_last_timestamp": self._history_last_timestamp,
        }

        if await self.is_persisted():
            d["value"] = self._last_read_value[0] if self._last_read_value else None
        else:
            d["value"] = None

        # attributes
        for name in await self.get_modifiable_attrs():
            v = await self.get_attr(name)
            if v is None:
                continue

            d[name] = v

        return d

    def save_asap(self) -> None:
        self.debug("marking for saving")
        self._pending_save = True

    def is_pending_save(self) -> bool:
        return self._pending_save

    async def cleanup(self) -> None:
        if self._write_task:
            self._write_task.cancel()
            await self._write_task
            self._write_task = None

    def is_loaded(self) -> bool:
        return self._loaded

    def set_loaded(self) -> None:
        self._loaded = True

    async def remove(self, persisted_data: bool = True) -> None:
        await self.cleanup()

        self.debug("removing port")
        _ports_by_id.pop(self._id, None)

        if persisted_data:
            self.debug("removing persisted data")
            await persist.remove(self.PERSIST_COLLECTION, filt={"id": self._id})
            if core_history.is_enabled():
                await core_history.remove_samples([self], background=True)

        await self.trigger_remove()

    async def trigger_add(self) -> None:
        await core_events.trigger(core_events.PortAdd(self))

    async def trigger_remove(self) -> None:
        await core_events.trigger(core_events.PortRemove(self))

    async def trigger_update(self) -> None:
        await core_events.trigger(core_events.PortUpdate(self))

    async def trigger_value_change(self, old_value: NullablePortValue, new_value: NullablePortValue) -> None:
        await core_events.trigger(core_events.ValueChange(old_value, new_value, self))

    async def get_schema(self) -> GenericJSONDict:
        if self._schema is None:
            self._schema = {"type": "object", "properties": {}, "additionalProperties": False}

            attrdefs = await self.get_attrdefs()
            for name, attrdef in attrdefs.items():
                if not attrdef.get("modifiable"):
                    continue

                if await self.get_attr(name) is None:
                    continue

                attr_schema = dict(attrdef)

                if attr_schema["type"] == "string":
                    if "min" in attr_schema:
                        attr_schema["minLength"] = attr_schema.pop("min")

                    if "max" in attr_schema:
                        attr_schema["maxLength"] = attr_schema.pop("max")
                elif attr_schema["type"] == "number":
                    if attr_schema.get("integer"):
                        attr_schema["type"] = "integer"

                    if "min" in attr_schema:
                        attr_schema["minimum"] = attr_schema.pop("min")

                    if "max" in attr_schema:
                        attr_schema["maximum"] = attr_schema.pop("max")

                if "choices" in attrdef:
                    attr_schema["enum"] = [c["value"] for c in attr_schema.pop("choices")]

                attr_schema.pop("modifiable", None)

                self._schema["properties"][name] = attr_schema

        return self._schema

    async def get_value_schema(self) -> GenericJSONDict:
        if self._value_schema is None:
            self._value_schema = {}

            c = await self.get_attr("choices")
            if c is not None:
                self._value_schema["enum"] = [i["value"] for i in c]
            else:
                m = await self.get_attr("min")
                if m is not None:
                    self._value_schema["minimum"] = m

                m = await self.get_attr("max")
                if m is not None:
                    self._value_schema["maximum"] = m

                if self.is_integer():
                    self._value_schema["type"] = "integer"
                elif self.get_type() == TYPE_BOOLEAN:
                    self._value_schema["type"] = "boolean"
                else:  # assuming number
                    self._value_schema["type"] = "number"

        return self._value_schema


class Port(BasePort, metaclass=abc.ABCMeta):
    pass


async def load(port_args: list[dict[str, Any]], trigger_add: bool = True) -> list[BasePort]:
    port_driver_classes = {}
    ports = []

    # Create ports
    for ps in port_args:
        ps = dict(ps)
        driver = ps.pop("driver", None)
        if not driver:
            raise PortLoadError("Missing port driver")

        if isinstance(driver, str):
            if driver not in port_driver_classes:
                try:
                    logger.debug("loading port driver %s", driver)
                    port_driver_classes[driver] = dynload_utils.load_attr(driver)
                except Exception as e:
                    raise PortLoadError(f"Failed to load port driver {driver}") from e

            port_class = port_driver_classes[driver]
        else:
            port_class = driver

        port_class_desc = f"{port_class.__module__}.{port_class.__name__}"

        try:
            port = port_class(**ps)
            port_id = port.get_id()

            if port_id in _ports_by_id:
                raise PortLoadError(f"A port with id {port_id} already exists")

            _ports_by_id[port.get_id()] = port
            ports.append(port)

            logger.debug("initialized %s (driver %s)", port, port_class_desc)
        except Exception as e:
            raise PortLoadError(f"Failed to initialize port from driver {port_class_desc}") from e

    # Map IDs
    for port in ports:
        if await port.get_attr("virtual"):
            continue

        old_id = port.get_id()
        new_id = settings.port_mappings.get(old_id)
        if not new_id:
            continue

        if new_id in _ports_by_id:
            raise PortLoadError(f"Cannot map port {old_id} to {new_id}: new id already exists")

        port = _ports_by_id.get(old_id)
        if not port:
            raise PortLoadError(f"Cannot map port {old_id} to {new_id}: no such port")

        try:
            port.map_id(new_id)
        except Exception as e:
            raise PortLoadError(f"Cannot map port {old_id} to {new_id}") from e

        _ports_by_id.pop(old_id)
        _ports_by_id[port.get_id()] = port

    # Load created ports
    for port in ports:
        try:
            await port.load()
        except Exception as e:
            raise PortLoadError(f"Failed to load {port}") from e

        if trigger_add:
            await port.trigger_add()

    return ports


async def load_one(cls: str | type, args: dict[str, Any], trigger_add: bool = True) -> BasePort:
    port_args = [dict(driver=cls, **args)]
    ports = await load(port_args, trigger_add=trigger_add)

    return ports[0]


def get(port_id: str) -> BasePort | None:
    return _ports_by_id.get(port_id)


def get_all() -> list[BasePort]:
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
                    port.error("save failed: %s", e, exc_info=True)

            await asyncio.sleep(settings.core.persist_interval / 1000.0)

        except asyncio.CancelledError:
            logger.debug("save task cancelled")
            break


async def init() -> None:
    global _save_loop_task

    _save_loop_task = asyncio.create_task(save_loop())


async def cleanup() -> None:
    if _save_loop_task:
        _save_loop_task.cancel()
        await _save_loop_task

    tasks = [asyncio.create_task(port.remove(persisted_data=False)) for port in _ports_by_id.values()]
    if tasks:
        await asyncio.wait(tasks)


async def reset() -> None:
    logger.debug("clearing ports persisted data")
    await persist.remove(BasePort.PERSIST_COLLECTION)


from qtoggleserver.core import main  # noqa: E402
