import abc
import dataclasses
import logging
import time

from qtoggleserver.core import events as core_events
from qtoggleserver.core import expressions as core_expressions
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.expressions import EvalContext
from qtoggleserver.core.expressions import exceptions as expression_exceptions
from qtoggleserver.core.expressions.exceptions import ExpressionEvalException
from qtoggleserver.core.typing import Attribute, Attributes, NullablePortValue
from qtoggleserver.slaves import devices as slaves_devices
from qtoggleserver.slaves import events as slaves_events
from qtoggleserver.utils import expressions as expressions_utils


ANY_VALUE = "any"

AnyNullablePortValue = str | NullablePortValue

logger = logging.getLogger(__package__)


def _is_sensitive_attr(name: str) -> bool:
    # A future "sensitive" property of attribute definitions could replace these name checks
    return name == "wifi_key" or name.endswith("_password_hash")


def _drop_sensitive_attrs(attrs: Attributes) -> Attributes:
    # Secrets must not reach filters, hooks or templates, which may publish them. Slave device attrs may come as
    # "<slave_name>:<attr_name>".
    return {n: v for n, v in attrs.items() if not _is_sensitive_attr(n.split(":")[-1])}


@dataclasses.dataclass
class _HandledEvent:
    attrs: Attributes = dataclasses.field(default_factory=dict)
    eval_context: EvalContext | None = None


class FilterEventHandler(core_events.Handler, metaclass=abc.ABCMeta):
    logger = logger

    def __init__(self, *, filter: dict | None = None, name: str | None = None) -> None:
        self._filter: dict = filter or {}
        self._filter_prepared: bool = False

        self._filter_event_types: set[str] | None = None

        self._filter_device_attrs: Attributes = {}
        self._filter_device_attr_transitions: dict[str, tuple[Attribute, Attribute]] = {}
        self._filter_device_attr_names: set[str] = set()

        self._filter_port_value: list[NullablePortValue] | core_expressions.Expression | None = None
        self._filter_port_value_transition: tuple[AnyNullablePortValue, AnyNullablePortValue] | None = None
        self._filter_port_attrs: Attributes | dict[str, list[Attribute]] = {}
        self._filter_port_attr_transitions: dict[str, tuple[Attribute, Attribute]] = {}
        self._filter_port_attr_names: set[str] = set()

        self._filter_slave_attrs: Attributes | dict[str, list[Attribute]] = {}
        self._filter_slave_attr_transitions: dict[str, tuple[Attribute, Attribute]] = {}
        self._filter_slave_attr_names: set[str] = set()

        self._filter_expression: core_expressions.Expression | None = None

        # Maintain an internal "last" state for all objects, so we can detect changes in attributes
        self._device_attrs: Attributes | dict[str, list[Attribute]] = {}
        self._port_attrs: dict[str, Attributes] = {}
        self._slave_attrs: dict[str, Attributes] = {}

        # The events being handled, with what the filter and the hooks share about them
        self._handled_events: dict[core_events.Event, _HandledEvent] = {}

        super().__init__(name=name)

    def _prepare_filter(self) -> None:
        event_types = self._filter.get("type")
        if event_types:
            if not isinstance(event_types, (list, tuple)):
                event_types = (event_types,)
            self._filter_event_types = set(event_types)

        port_value = self._filter.get("port_value")
        if port_value is not None:
            if isinstance(port_value, str):  # an expression
                try:
                    self.debug('using value expression "%s"', port_value)
                    self._filter_port_value = core_expressions.parse(
                        self_port_id=None, sexpression=port_value, role=core_expressions.Role.FILTER
                    )
                except expression_exceptions.ExpressionParseError as e:
                    self.error('failed to parse port expression "%s": %s', port_value, e)

                    raise
            else:
                if not isinstance(port_value, (list, tuple)):
                    port_value = (port_value,)

                self._filter_port_value = port_value

        self._filter_port_value_transition = self._filter.get("port_value_transition")

        self._filter_device_attrs = {
            n[7:]: v for n, v in self._filter.items() if n.startswith("device_") and not n.endswith("_transition")
        }

        self._filter_device_attr_transitions = {
            n[7:-11]: v for n, v in self._filter.items() if n.startswith("device_") and n.endswith("_transition")
        }

        self._filter_port_attrs = {
            n[5:]: v
            for n, v in self._filter.items()
            if n.startswith("port_") and n != "port_value" and not n.endswith("_transition")
        }

        self._filter_port_attr_transitions = {
            n[5:-11]: v
            for n, v in self._filter.items()
            if n.startswith("port_") and n != "port_value_transition" and n.endswith("_transition")
        }

        self._filter_slave_attrs = {
            n[6:]: v for n, v in self._filter.items() if n.startswith("slave_") and not n.endswith("_transition")
        }

        self._filter_slave_attr_transitions = {
            n[6:-11]: v for n, v in self._filter.items() if n.startswith("slave_") and n.endswith("_transition")
        }

        self._filter_device_attr_names.update(self._filter_device_attrs.keys())
        self._filter_device_attr_names.update(self._filter_device_attr_transitions.keys())

        self._filter_port_attr_names.update(self._filter_port_attrs.keys())
        self._filter_port_attr_names.update(self._filter_port_attr_transitions.keys())

        self._filter_slave_attr_names.update(self._filter_slave_attrs.keys())
        self._filter_slave_attr_names.update(self._filter_slave_attr_transitions.keys())

        filter_sexpression = self._filter.get("expression")
        if isinstance(filter_sexpression, str):
            try:
                self.debug('using filter expression "%s"', filter_sexpression)
                self._filter_expression = core_expressions.parse(
                    self_port_id=None, sexpression=filter_sexpression, role=core_expressions.Role.FILTER
                )
            except expression_exceptions.ExpressionParseError as e:
                self.error('failed to parse filter expression "%s": %s', filter_sexpression, e)

                raise

        self._filter_prepared = True
        self.debug("filter prepared")

    @staticmethod
    def _make_changed_added_removed(
        old_attrs: Attributes, new_attrs: Attributes
    ) -> tuple[dict[str, tuple[Attribute, Attribute]], Attributes, Attributes]:
        changed_attrs = {}
        added_attrs = {}
        removed_attrs = {}

        all_attr_names = set(old_attrs) | set(new_attrs)
        for n in all_attr_names:
            old_v = old_attrs.get(n)
            new_v = new_attrs.get(n)
            if old_v == new_v:
                continue

            if old_v is None:
                if new_v is not None:
                    added_attrs[n] = new_v
            elif new_v is None:
                removed_attrs[n] = old_v
            else:
                changed_attrs[n] = (old_v, new_v)

        return changed_attrs, added_attrs, removed_attrs

    @staticmethod
    def _get_value_pair(event: core_events.PortEvent) -> tuple[NullablePortValue, NullablePortValue]:
        # Only value changes carry an old and a new value. Removals carry none, but removed ports are no longer read,
        # so their last read value stands in for it.
        if isinstance(event, core_events.ValueChange):
            return event.old_value, event.new_value
        if isinstance(event, (core_events.PortAdd, core_events.PortUpdate)):
            value = event.get_params().get("value")
        else:
            value = event.get_port().get_last_read_value()

        return value, value

    async def _update_from_event(
        self, event: core_events.Event
    ) -> tuple[
        tuple[NullablePortValue, NullablePortValue],
        Attributes,
        Attributes,
        dict[str, tuple[Attribute, Attribute]],
        Attributes,
        Attributes,
    ]:
        value_pair = (None, None)
        old_attrs = {}
        new_attrs = {}
        changed_attrs = {}
        added_attrs = {}
        removed_attrs = {}

        # Events are handled some time after they're triggered, when things may have changed again, so use the attrs
        # and values that events carry (copied, as they're shared with other handlers), where they carry any
        if isinstance(event, core_events.PortEvent):
            port = event.get_port()

            value_pair = self._get_value_pair(event)
            old_attrs = self._port_attrs.get(port.get_id(), {})
            if isinstance(event, (core_events.PortAdd, core_events.PortUpdate)):
                new_attrs = dict(event.get_params())
                new_attrs.pop("value", None)
                new_attrs.pop("definitions", None)
                changed_attrs, added_attrs, removed_attrs = self._make_changed_added_removed(old_attrs, new_attrs)
                self._port_attrs[port.get_id()] = new_attrs
            elif isinstance(event, core_events.PortRemove):
                # Stop tracking before awaiting anything, so that a port add handled meanwhile isn't dropped
                removed_attrs = self._port_attrs.pop(port.get_id(), {})
                new_attrs = old_attrs = dict(old_attrs) or await port.get_attrs()
            elif isinstance(event, core_events.ValueChange):
                # Value changes carry no attrs, so use the ones from the last port add or update, falling back to the
                # current ones for a port the handler has seen neither for; either way, no attr has changed
                new_attrs = old_attrs = dict(old_attrs) or await port.get_attrs()

        elif isinstance(event, core_events.DeviceEvent):
            if isinstance(event, core_events.DeviceUpdate):
                new_attrs = _drop_sensitive_attrs(event.get_params())
            else:
                new_attrs = _drop_sensitive_attrs(await event.get_attrs())

            # Read only after awaiting, so that a device update handled meanwhile isn't reported again
            old_attrs = self._device_attrs
            changed_attrs, added_attrs, removed_attrs = self._make_changed_added_removed(old_attrs, new_attrs)
            self._device_attrs = new_attrs

        elif isinstance(event, slaves_events.SlaveDeviceEvent):
            slave = event.get_slave()

            old_attrs = self._slave_attrs.get(slave.get_name(), {})
            if isinstance(event, (slaves_events.SlaveDeviceAdd, slaves_events.SlaveDeviceUpdate)):
                slave_json = dict(event.get_params())
            else:
                slave_json = slave.to_json()

            # Merge the slave's own attrs into the properties the master keeps about it, so filters can use both
            new_attrs = _drop_sensitive_attrs(dict(slave_json, **slave_json.pop("attrs")))

            if isinstance(event, (slaves_events.SlaveDeviceAdd, slaves_events.SlaveDeviceUpdate)):
                changed_attrs, added_attrs, removed_attrs = self._make_changed_added_removed(old_attrs, new_attrs)
                self._slave_attrs[slave.get_name()] = new_attrs
            elif isinstance(event, slaves_events.SlaveDeviceRemove):
                removed_attrs = self._slave_attrs.pop(slave.get_name(), {})

        return value_pair, old_attrs, new_attrs, changed_attrs, added_attrs, removed_attrs

    @staticmethod
    async def _build_eval_context(event: core_events.Event, attrs: Attributes | None = None) -> EvalContext:
        # The same values that port expressions see, rather than the ones tracked from events
        context = await expressions_utils.build_context(int(time.time() * 1000))
        context.device_attrs = _drop_sensitive_attrs(context.device_attrs)

        if isinstance(event, core_events.PortEvent):
            port = event.get_port()
            port_id = port.get_id()

            # The read and attrs behind a port event may have been replaced by newer ones by now
            context.port_read_values[port_id] = FilterEventHandler._get_value_pair(event)[1]
            if attrs is not None:
                context.port_attrs[port_id] = attrs

            # A removed port is no longer part of the device, but its removal is still about it
            context.port_values.setdefault(port_id, port.get_last_value())
            context.port_written_values.setdefault(port_id, port.get_last_written_value())

        return context

    async def get_eval_context(self, event: core_events.Event) -> EvalContext:
        """Return the expression context for an event, the same one throughout its handling."""

        handled = self._handled_events.get(event)
        if handled is None:
            return await self._build_eval_context(event)

        if handled.eval_context is None:
            handled.eval_context = await self._build_eval_context(event, handled.attrs)

        return handled.eval_context

    @staticmethod
    def _accepts_attrs(
        attr_names: set[str],
        filter_attrs: Attributes,
        filter_attr_transitions: dict[str, tuple[Attribute, Attribute]],
        old_attrs: Attributes,
        new_attrs: Attributes,
    ) -> bool:
        for name in attr_names:
            old_value = old_attrs.get(name)
            new_value = new_attrs.get(name)

            filter_transition = filter_attr_transitions.get(name)
            if filter_transition is not None:
                old_filter_value, new_filter_value = filter_transition
                if (
                    (old_filter_value != old_value and old_filter_value != ANY_VALUE)
                    or (new_filter_value != new_value and new_filter_value != ANY_VALUE)
                    or (old_value == new_value)
                ):
                    return False

            filter_value = filter_attrs.get(name)
            if filter_value is not None:
                if isinstance(filter_value, (list, tuple)):  # a list of accepted values
                    if new_value not in filter_value:
                        return False
                elif new_value != filter_value:  # a single value
                    return False

        return True

    async def accepts_device(self, event: core_events.Event, old_attrs: Attributes, new_attrs: Attributes) -> bool:
        return self._accepts_attrs(
            self._filter_device_attr_names,
            self._filter_device_attrs,
            self._filter_device_attr_transitions,
            old_attrs,
            new_attrs,
        )

    async def accepts_port_value(
        self, event: core_events.Event, value_pair: tuple[NullablePortValue, NullablePortValue]
    ) -> bool:
        old_value, new_value = value_pair

        if self._filter_port_value_transition is not None:
            old_filter_value, new_filter_value = self._filter_port_value_transition
            if (
                (old_filter_value != old_value and old_filter_value != ANY_VALUE)
                or (new_filter_value != new_value and new_filter_value != ANY_VALUE)
                or (old_value == new_value)
            ):
                return False

        if self._filter_port_value is not None:
            if isinstance(self._filter_port_value, (list, tuple)):  # a list of accepted values
                if new_value not in self._filter_port_value:
                    return False
            elif isinstance(self._filter_port_value, core_expressions.Expression):  # an expression
                eval_context = await self.get_eval_context(event)
                try:
                    if new_value != await self._filter_port_value.eval(context=eval_context):
                        return False
                except ExpressionEvalException as e:
                    self.warning('Expression evaluation failed for "%s": %s', self._filter_port_value, e)
                    return False
            elif new_value != self._filter_port_value:
                return False

        return True

    async def accepts_port(
        self,
        event: core_events.Event,
        value_pair: tuple[NullablePortValue, NullablePortValue],
        old_attrs: Attributes,
        new_attrs: Attributes,
    ) -> bool:
        if not await self.accepts_port_value(event, value_pair):
            return False

        return self._accepts_attrs(
            self._filter_port_attr_names,
            self._filter_port_attrs,
            self._filter_port_attr_transitions,
            old_attrs,
            new_attrs,
        )

    async def accepts_slave(self, event: core_events.Event, old_attrs: Attributes, new_attrs: Attributes) -> bool:
        return self._accepts_attrs(
            self._filter_slave_attr_names,
            self._filter_slave_attrs,
            self._filter_slave_attr_transitions,
            old_attrs,
            new_attrs,
        )

    async def accepts(
        self,
        event: core_events.Event,
        value_pair: tuple[NullablePortValue, NullablePortValue],
        old_attrs: Attributes,
        new_attrs: Attributes,
        changed_attrs: dict[str, tuple[Attribute, Attribute]],
        added_attrs: Attributes,
        removed_attrs: Attributes,
    ) -> bool:
        if not self._filter_prepared:
            self._prepare_filter()

        if self._filter_event_types and event.get_type() not in self._filter_event_types:
            return False

        if isinstance(event, core_events.DeviceEvent):
            accepted = await self.accepts_device(event, old_attrs, new_attrs)
        elif isinstance(event, core_events.PortEvent):
            accepted = await self.accepts_port(event, value_pair, old_attrs, new_attrs)
        elif isinstance(event, slaves_events.SlaveDeviceEvent):
            accepted = await self.accepts_slave(event, old_attrs, new_attrs)
        else:
            accepted = True

        if not accepted:
            return False

        if self._filter_expression:
            eval_context = await self.get_eval_context(event)
            try:
                if not await self._filter_expression.eval(context=eval_context):
                    return False
            except ExpressionEvalException as e:
                self.warning('Expression evaluation failed for "%s": %s', self._filter_expression, e)
                return False

        return True

    async def handle_event(self, event: core_events.Event) -> None:
        # Share one expression context between the filter and the hooks, so they all see the same values
        self._handled_events[event] = _HandledEvent()
        try:
            await self._handle_event(event)
        finally:
            self._handled_events.pop(event, None)

    async def _handle_event(self, event: core_events.Event) -> None:
        (value_pair, old_attrs, new_attrs, changed_attrs, added_attrs, removed_attrs) = await self._update_from_event(
            event
        )
        self._handled_events[event].attrs = new_attrs

        accepted = await self.accepts(
            event, value_pair, old_attrs, new_attrs, changed_attrs, added_attrs, removed_attrs
        )

        if not accepted:
            return

        self.debug("handling event %s", event)

        try:
            await self.on_event(event)
        except Exception as e:
            self.error("failed to handle event %s: %s", event, e, exc_info=True)

        try:
            if isinstance(event, core_events.ValueChange):
                old_value, new_value = value_pair
                await self.on_value_change(event, event.get_port(), old_value, new_value, new_attrs)
            elif isinstance(event, core_events.PortUpdate):
                await self.on_port_update(
                    event,
                    event.get_port(),
                    value_pair[1],
                    old_attrs,
                    new_attrs,
                    changed_attrs,
                    added_attrs,
                    removed_attrs,
                )
            elif isinstance(event, core_events.PortAdd):
                await self.on_port_add(event, event.get_port(), value_pair[1], new_attrs)
            elif isinstance(event, core_events.PortRemove):
                await self.on_port_remove(event, event.get_port(), value_pair[1], new_attrs)
            elif isinstance(event, core_events.DeviceUpdate):
                await self.on_device_update(event, old_attrs, new_attrs, changed_attrs, added_attrs, removed_attrs)
            elif isinstance(event, core_events.FullUpdate):
                await self.on_full_update(event)
            elif isinstance(event, slaves_events.SlaveDeviceUpdate):
                await self.on_slave_device_update(
                    event, event.get_slave(), old_attrs, new_attrs, changed_attrs, added_attrs, removed_attrs
                )
            elif isinstance(event, slaves_events.SlaveDeviceAdd):
                await self.on_slave_device_add(event, event.get_slave(), new_attrs)
            elif isinstance(event, slaves_events.SlaveDeviceRemove):
                await self.on_slave_device_remove(event, event.get_slave(), new_attrs)
        except Exception as e:
            self.error("failed to handle event %s: %s", event, e, exc_info=True)

    async def on_event(self, event: core_events.Event) -> None:
        pass

    async def on_value_change(
        self,
        event: core_events.Event,
        port: core_ports.BasePort,
        old_value: NullablePortValue,
        new_value: NullablePortValue,
        attrs: Attributes,
    ) -> None:
        pass

    async def on_port_update(
        self,
        event: core_events.Event,
        port: core_ports.BasePort,
        value: NullablePortValue,
        old_attrs: Attributes,
        new_attrs: Attributes,
        changed_attrs: dict[str, tuple[Attribute, Attribute]],
        added_attrs: Attributes,
        removed_attrs: Attributes,
    ) -> None:
        pass

    async def on_port_add(
        self, event: core_events.Event, port: core_ports.BasePort, value: NullablePortValue, attrs: Attributes
    ) -> None:
        pass

    async def on_port_remove(
        self, event: core_events.Event, port: core_ports.BasePort, value: NullablePortValue, attrs: Attributes
    ) -> None:
        pass

    async def on_device_update(
        self,
        event: core_events.Event,
        old_attrs: Attributes,
        new_attrs: Attributes,
        changed_attrs: dict[str, tuple[Attribute, Attribute]],
        added_attrs: Attributes,
        removed_attrs: Attributes,
    ) -> None:
        pass

    async def on_full_update(self, event: core_events.Event) -> None:
        pass

    async def on_slave_device_update(
        self,
        event: core_events.Event,
        slave: slaves_devices.Slave,
        old_attrs: Attributes,
        new_attrs: Attributes,
        changed_attrs: dict[str, tuple[Attribute, Attribute]],
        added_attrs: Attributes,
        removed_attrs: Attributes,
    ) -> None:
        pass

    async def on_slave_device_add(
        self, event: core_events.Event, slave: slaves_devices.Slave, attrs: Attributes
    ) -> None:
        pass

    async def on_slave_device_remove(
        self, event: core_events.Event, slave: slaves_devices.Slave, attrs: Attributes
    ) -> None:
        pass
