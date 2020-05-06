
import abc
import logging

from typing import Dict, List, Optional, Set, Tuple, Union

from qtoggleserver.core import events as core_events
from qtoggleserver.core import expressions as core_expressions
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.typing import Attribute, Attributes, NullablePortValue
from qtoggleserver.slaves import devices as slaves_devices
from qtoggleserver.slaves import events as slaves_events


logger = logging.getLogger(__package__)


class FilterEventHandler(core_events.Handler, metaclass=abc.ABCMeta):
    logger = logger

    def __init__(self, *, filter: dict = None, name: Optional[str] = None) -> None:
        self._filter: dict = filter or {}
        self._filter_prepared: bool = False

        self._filter_event_types: Optional[Set[str]] = None

        self._filter_device_attrs: Attributes = {}
        self._filter_device_attr_transitions: Dict[str, Tuple[Attribute, Attribute]] = {}
        self._filter_device_attr_names: Set[str] = set()

        self._filter_port_value: Optional[Union[List[NullablePortValue]], core_expressions.Expression] = None
        self._filter_port_value_transition: Optional[Tuple[NullablePortValue, NullablePortValue]] = None
        self._filter_port_attrs: Union[Attributes, Dict[str, List[Attribute]]] = {}
        self._filter_port_attr_transitions: Dict[str, Tuple[Attribute, Attribute]] = {}
        self._filter_port_attr_names: Set[str] = set()

        self._filter_slave_attrs: Union[Attributes, Dict[str, List[Attribute]]] = {}
        self._filter_slave_attr_transitions: Dict[str, Tuple[Attribute, Attribute]] = {}
        self._filter_slave_attr_names: Set[str] = set()

        # Maintain an internal "last" state for all objects, so we can detect changes in attributes and values
        self._device_attrs: Union[Attributes, Dict[str, List[Attribute]]] = {}
        self._port_values: Dict[str, NullablePortValue] = {}
        self._port_attrs: Dict[str, Attributes] = {}
        self._slave_attrs: Dict[str, Attributes] = {}

        super().__init__(name=name)

    def _prepare_filter(self) -> None:
        event_types = self._filter.get('type')
        if event_types:
            if not isinstance(event_types, list):
                event_types = (event_types,)
            self._filter_event_types = set(event_types)

        port_value = self._filter.get('port_value')
        if port_value is not None:
            if isinstance(port_value, str):  # An expression
                try:
                    self.debug('using value expression "%s"', port_value)
                    self._filter_port_value = core_expressions.parse(self_port_id=None, sexpression=port_value)

                except core_expressions.ExpressionParseError as e:
                    self.error('failed to parse port expression "%s": %s', port_value, e)

                    raise

            else:
                if not isinstance(port_value, list):
                    port_value = (port_value,)

                self._filter_port_value = port_value

        self._filter_port_value_transition = self._filter.get('port_value_transition')

        self._filter_device_attrs = {
            n[7:]: v for n, v in self._filter.items()
            if n.startswith('device_') and not n.endswith('_transition')
        }

        self._filter_device_attr_transitions = {
            n[7:-11]: v for n, v in self._filter.items()
            if n.startswith('device_') and n.endswith('_transition')
        }

        self._filter_port_attrs = {
            n[5:]: v for n, v in self._filter.items()
            if n.startswith('port_') and n != 'port_value' and not n.endswith('_transition')
        }

        self._filter_port_attr_transitions = {
            n[5:-11]: v for n, v in self._filter.items()
            if n.startswith('port_') and n != 'port_value_transition' and n.endswith('_transition')
        }

        self._filter_slave_attrs = {
            n[6:]: v for n, v in self._filter.items()
            if n.startswith('slave_') and not n.endswith('_transition')
        }

        self._filter_slave_attr_transitions = {
            n[6:-11]: v for n, v in self._filter.items()
            if n.startswith('slave_') and n.endswith('_transition')
        }

        self._filter_device_attr_names.update(self._filter_device_attrs.keys())
        self._filter_device_attr_names.update(self._filter_device_attr_transitions.keys())

        self._filter_port_attr_names.update(self._filter_port_attrs.keys())
        self._filter_port_attr_names.update(self._filter_port_attr_transitions.keys())

        self._filter_slave_attr_names.update(self._filter_slave_attrs.keys())
        self._filter_slave_attr_names.update(self._filter_slave_attr_transitions.keys())

        self._filter_prepared = True
        self.debug('filter prepared')

    @staticmethod
    def _make_changed_added_removed(old_attrs: Attributes, new_attrs: Attributes) -> Tuple[
        Dict[str, Tuple[Attribute, Attribute]],
        Attributes,
        Attributes
    ]:

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

    async def _update_from_event(self, event: core_events.Event) -> Tuple[
        Tuple[NullablePortValue, NullablePortValue],
        Attributes,
        Attributes,
        Dict[str, Tuple[Attribute, Attribute]],
        Attributes,
        Attributes
    ]:

        value_pair = (None, None)
        old_attrs = {}
        new_attrs = {}
        changed_attrs = {}
        added_attrs = {}
        removed_attrs = {}

        if isinstance(event, core_events.PortEvent):
            port = event.get_port()

            old_attrs = self._port_attrs.get(port.get_id(), {})
            new_attrs = await port.get_attrs()

            old_value = self._port_values.get(port.get_id())
            new_value = port.get_value()
            value_pair = (old_value, new_value)

            if isinstance(event, (core_events.PortAdd, core_events.PortUpdate)):
                changed_attrs, added_attrs, removed_attrs = self._make_changed_added_removed(old_attrs, new_attrs)
                self._port_values[port.get_id()] = new_value
                self._port_attrs[port.get_id()] = new_attrs

            elif isinstance(event, core_events.PortRemove):
                self._port_values.pop(port.get_id(), None)
                removed_attrs = self._port_attrs.pop(port.get_id(), {})

            elif isinstance(event, core_events.ValueChange):
                self._port_values[port.get_id()] = new_value

        elif isinstance(event, core_events.DeviceEvent):
            old_attrs = self._device_attrs
            new_attrs = event.get_attrs()

            changed_attrs, added_attrs, removed_attrs = self._make_changed_added_removed(old_attrs, new_attrs)
            self._device_attrs = new_attrs

        elif isinstance(event, slaves_events.SlaveDeviceEvent):
            slave = event.get_slave()
            slave_json = slave.to_json()

            # Flatten slave master properties and attributes
            old_attrs = self._slave_attrs.get(slave.get_name(), {})
            new_attrs = dict(slave_json, **slave_json.pop('attrs'))

            if isinstance(event, (slaves_events.SlaveDeviceAdd, slaves_events.SlaveDeviceUpdate)):
                changed_attrs, added_attrs, removed_attrs = self._make_changed_added_removed(old_attrs, new_attrs)
                self._slave_attrs[slave.get_name()] = new_attrs

            elif isinstance(event, slaves_events.SlaveDeviceRemove):
                removed_attrs = self._slave_attrs.pop(slave.get_name(), {})

        return value_pair, old_attrs, new_attrs, changed_attrs, added_attrs, removed_attrs

    @staticmethod
    def _accepts_attrs(
        attr_names: Set[str],
        filter_attrs: Attributes,
        filter_attr_transitions: Dict[str, Tuple[Attribute, Attribute]],
        old_attrs: Attributes,
        new_attrs: Attributes
    ) -> bool:

        for name in attr_names:
            old_value = old_attrs.get(name)
            new_value = new_attrs.get(name)

            filter_transition = filter_attr_transitions.get(name)
            if filter_transition is not None:
                old_filter_value, new_filter_value = filter_transition
                if ((old_filter_value != old_value and old_filter_value is not None) or
                    (new_filter_value != new_value and new_filter_value is not None)):

                    return False

            filter_value = filter_attrs.get(name)
            if filter_value is not None:
                if isinstance(filter_value, list):  # A list of accepted values
                    if new_value not in filter_value:
                        return False

                elif new_value != filter_value:  # A single value
                    return False

        return True

    async def accepts_device(self, event: core_events.Event, old_attrs: Attributes, new_attrs: Attributes) -> bool:
        return self._accepts_attrs(
            self._filter_device_attr_names,
            self._filter_device_attrs,
            self._filter_device_attr_transitions,
            old_attrs,
            new_attrs
        )

    async def accepts_port_value(
        self,
        event: core_events.Event,
        value_pair: Tuple[NullablePortValue, NullablePortValue]
    ) -> bool:

        old_value, new_value = value_pair

        if self._filter_port_value_transition is not None:
            old_filter_value, new_filter_value = self._filter_port_value_transition
            if ((old_filter_value != old_value and old_filter_value is not None) or
                (new_filter_value != new_value and new_filter_value is not None)):

                return False

        if self._filter_port_value is not None:
            if isinstance(self._filter_port_value, list):  # A list of accepted values
                if new_value not in self._filter_port_value:
                    return False

            elif isinstance(self._filter_port_value, core_expressions.Expression):  # An expression
                if new_value != self._filter_port_value.eval():
                    return False

        return True

    async def accepts_port(
        self,
        event: core_events.Event,
        value_pair: Tuple[NullablePortValue, NullablePortValue],
        old_attrs: Attributes,
        new_attrs: Attributes
    ) -> bool:

        if not await self.accepts_port_value(event, value_pair):
            return False

        return self._accepts_attrs(
            self._filter_port_attr_names,
            self._filter_port_attrs,
            self._filter_port_attr_transitions,
            old_attrs,
            new_attrs
        )

    async def accepts_slave(self, event: core_events.Event, old_attrs: Attributes, new_attrs: Attributes) -> bool:
        return self._accepts_attrs(
            self._filter_slave_attr_names,
            self._filter_slave_attrs,
            self._filter_slave_attr_transitions,
            old_attrs,
            new_attrs
        )

    async def accepts(
        self,
        event: core_events.Event,
        value_pair: Tuple[NullablePortValue, NullablePortValue],
        old_attrs: Attributes,
        new_attrs: Attributes,
        changed_attrs: Dict[str, Tuple[Attribute, Attribute]],
        added_attrs: Attributes,
        removed_attrs: Attributes
    ) -> bool:

        if not self._filter_prepared:
            self._prepare_filter()

        if self._filter_event_types and event.get_type() not in self._filter_event_types:
            return False

        if (isinstance(event, core_events.DeviceEvent) and
            not await self.accepts_device(event, old_attrs, new_attrs)):

            return False

        elif (isinstance(event, core_events.PortEvent) and
              not await self.accepts_port(event, value_pair, old_attrs, new_attrs)):

            return False

        elif (isinstance(event, slaves_events.SlaveDeviceEvent) and
              not await self.accepts_slave(event, old_attrs, new_attrs)):

            return False

        return True

    async def handle_event(self, event: core_events.Event) -> None:
        (
            value_pair,
            old_attrs,
            new_attrs,
            changed_attrs,
            added_attrs,
            removed_attrs
        ) = await self._update_from_event(event)

        accepted = await self.accepts(
            event,
            value_pair,
            old_attrs,
            new_attrs,
            changed_attrs,
            added_attrs,
            removed_attrs
        )

        if not accepted:
            return

        self.debug('handling event %s', event)

        try:
            await self.on_event(event)

        except Exception as e:
            self.error('failed to handle event %s: %s', event, e, exc_info=True)

        try:
            if isinstance(event, core_events.ValueChange):
                old_value, new_value = value_pair
                await self.on_value_change(event, event.get_port(), old_value, new_value, new_attrs)

            elif isinstance(event, core_events.PortUpdate):
                await self.on_port_update(
                    event,
                    event.get_port(),
                    old_attrs,
                    new_attrs,
                    changed_attrs,
                    added_attrs,
                    removed_attrs
                )

            elif isinstance(event, core_events.PortAdd):
                await self.on_port_add(event, event.get_port(), new_attrs)

            elif isinstance(event, core_events.PortRemove):
                await self.on_port_remove(event, event.get_port(), new_attrs)

            elif isinstance(event, core_events.DeviceUpdate):
                await self.on_device_update(event, old_attrs, new_attrs, changed_attrs, added_attrs, removed_attrs)

            elif isinstance(event, core_events.FullUpdate):
                await self.on_full_update(event)

            elif isinstance(event, slaves_events.SlaveDeviceUpdate):
                await self.on_slave_device_update(
                    event,
                    event.get_slave(),
                    old_attrs,
                    new_attrs,
                    changed_attrs,
                    added_attrs,
                    removed_attrs
                )

            elif isinstance(event, slaves_events.SlaveDeviceAdd):
                await self.on_slave_device_add(event, event.get_slave(), new_attrs)

            elif isinstance(event, slaves_events.SlaveDeviceRemove):
                await self.on_slave_device_remove(event, event.get_slave(), new_attrs)

        except Exception as e:
            self.error('failed to handle event %s: %s', event, e, exc_info=True)

    async def on_event(self, event: core_events.Event) -> None:
        pass

    async def on_value_change(
        self,
        event: core_events.Event,
        port: core_ports.BasePort,
        old_value: NullablePortValue,
        new_value: NullablePortValue,
        attrs: Attributes
    ) -> None:

        pass

    async def on_port_update(
        self,
        event: core_events.Event,
        port: core_ports.BasePort,
        old_attrs: Attributes,
        new_attrs: Attributes,
        changed_attrs: Dict[str, Tuple[Attribute, Attribute]],
        added_attrs: Attributes,
        removed_attrs: Attributes
    ) -> None:

        pass

    async def on_port_add(self, event: core_events.Event, port: core_ports.BasePort, attrs: Attributes) -> None:
        pass

    async def on_port_remove(self, event: core_events.Event, port: core_ports.BasePort, attrs: Attributes) -> None:
        pass

    async def on_device_update(
        self,
        event: core_events.Event,
        old_attrs: Attributes,
        new_attrs: Attributes,
        changed_attrs: Dict[str, Tuple[Attribute, Attribute]],
        added_attrs: Attributes,
        removed_attrs: Attributes
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
        changed_attrs: Dict[str, Tuple[Attribute, Attribute]],
        added_attrs: Attributes,
        removed_attrs: Attributes
    ) -> None:

        pass

    async def on_slave_device_add(
        self,
        event: core_events.Event,
        slave: slaves_devices.Slave,
        attrs: Attributes
    ) -> None:

        pass

    async def on_slave_device_remove(
        self,
        event: core_events.Event,
        slave: slaves_devices.Slave,
        attrs: Attributes
    ) -> None:

        pass
