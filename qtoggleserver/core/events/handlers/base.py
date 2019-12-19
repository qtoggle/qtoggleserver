
import abc
import logging

from qtoggleserver.core import expressions as core_expressions

from ..types import device as device_events
from ..types import port as port_events
from ..types import slave as slave_events


logger = logging.getLogger(__package__)


class BaseEventHandler(metaclass=abc.ABCMeta):
    # noinspection PyShadowingBuiltins
    def __init__(self, filter=None):
        self._filter = filter or {}
        self._filter_ready = False
        self._filter_event_types = None
        self._filter_device_attrs = {}
        self._filter_port_value = None
        self._filter_port_attrs = {}

        # Maintain an internal "last" state for all objects, so we can detect changes in various attributes
        self._device_attrs = {}
        self._port_values = {}
        self._port_attrs = {}
        self._slave_properties = {}
        self._slave_attrs = {}

    def _prepare_filter(self):
        event_types = self._filter.get('type')
        if event_types:
            if not isinstance(event_types, list):
                event_types = event_types,
            self._filter_event_types = set(event_types)

        port_value = self._filter.get('port_value')
        if port_value is not None:
            if isinstance(port_value, str):  # An expression
                try:
                    logger.debug('using value expression "%s"', port_value)
                    self._filter_port_value = core_expressions.parse(self_port_id=None, sexpression=port_value)

                except core_expressions.ExpressionError as e:
                    logger.error('failed to parse port expression "%s": %s', port_value, e)

                    raise

            else:
                self._filter_port_value = port_value

        self._filter_device_attrs = {n[7:]: v for n, v in self._filter.items()
                                     if n.startswith('device_')}

        self._filter_port_attrs = {n[5:]: v for n, v in self._filter.items()
                                   if n.startswith('port_') and n != 'port_value'}

        self._filter_slave_attrs = {n[6:]: v for n, v in self._filter.items()
                                    if n.startswith('slave_')}

        self._filter_ready = True

    async def _update_from_event(self, event):
        if isinstance(event, port_events.PortEvent):
            port = event.get_port()

            if isinstance(event, (port_events.PortAdd, port_events.PortUpdate)):
                self._port_values[port.get_id()] = port.get_value()
                self._port_attrs[port.get_id()] = await port.get_attrs()

            elif isinstance(event, port_events.PortRemove):
                self._port_values.pop(port.get_id(), None)
                self._port_attrs.pop(port.get_id(), None)

            elif isinstance(event, port_events.ValueChange):
                self._port_values[port.get_id()] = port.get_value()

        elif isinstance(event, device_events.DeviceEvent):
            self._device_attrs = event.get_attrs()

        elif isinstance(event, slave_events.SlaveDeviceEvent):
            slave = event.get_slave()

            if isinstance(event, (slave_events.SlaveDeviceAdd, slave_events.SlaveDeviceUpdate)):
                slave_json = slave.to_json()
                self._slave_attrs[slave.get_name()] = slave_json.pop('attrs')
                self._slave_properties[slave.get_name()] = slave_json

            elif isinstance(event, slave_events.SlaveDeviceRemove):
                self._slave_attrs.pop(slave.get_name(), None)
                self._slave_properties.pop(slave.get_name(), None)

    async def accepts_device(self, event):
        old_attrs = self._device_attrs
        attrs = event.get_attrs()

        for name, filter_value in self._filter_device_attrs.items():
            if isinstance(filter_value, list):
                old_filter_value, filter_value = filter_value[:2]
                if old_filter_value != old_attrs.get(name):
                    return False

            if filter_value != attrs.get(name):
                return False

        return True

    async def accepts_port_value(self, event):
        port = event.get_port()
        filter_value = self._filter_port_value
        old_value = self._port_values.get(port.get_id())
        value = port.get_value()

        if isinstance(filter_value, list):
            old_filter_value, filter_value = filter_value[:2]
            if old_filter_value != old_value:
                return False

        if isinstance(filter_value, core_expressions.Expression):
            filter_value = filter_value.eval()

        if value != filter_value:
            return False

        return True

    async def accepts_port(self, event):
        if self._filter_port_value is not None:
            if not await self.accepts_port_value(event):
                return False

        port = event.get_port()
        old_attrs = self._port_attrs.get(port.get_id(), {})
        attrs = await port.get_attrs()

        for name, filter_value in self._filter_port_attrs.items():
            if isinstance(filter_value, list):
                old_filter_value, filter_value = filter_value[:2]
                if old_filter_value != old_attrs.get(name):
                    return False

            if filter_value != attrs.get(name):
                return False

        return True

    async def accepts_slave(self, event):
        slave = event.get_slave()
        old_attrs = self._slave_properties.get(slave.get_name(), {})
        old_attrs.update(self._slave_attrs.get(slave.get_name(), {}))

        attrs = slave.to_json()
        attrs.update(attrs.pop('attrs'))  # Flatten slave master properties and attributes

        for name, filter_value in self._filter_slave_attrs.items():
            if isinstance(filter_value, list):
                old_filter_value, filter_value = filter_value[:2]
                if old_filter_value != old_attrs.get(name):
                    return False

            if filter_value != attrs.get(name):
                return False

        return True

    async def accepts(self, event):
        if not self._filter_ready:
            self._prepare_filter()

        if self._filter_event_types and event.get_type() not in self._filter_event_types:
            return False

        if isinstance(event, device_events.DeviceEvent) and not await self.accepts_device(event):
            return False

        elif isinstance(event, port_events.PortEvent) and not await self.accepts_port(event):
            return False

        elif isinstance(event, slave_events.SlaveDeviceEvent) and not await self.accepts_slave(event):
            return False

        return True

    async def handle_event(self, event):
        accepted = await self.accepts(event)
        await self._update_from_event(event)

        if not accepted:
            return

        try:
            await self.on_event(event)

        except Exception as e:
            logger.error('failed to handle event %s: %s', event, e, exc_info=True)

        _type = event.get_type()
        method_name = 'on_{}'.format(_type.replace('-', '_'))

        try:
            method = getattr(self, method_name)

        except AttributeError:
            logger.error('failed to handle event %s: no such method %s', event, method_name)
            return

        args = []
        if isinstance(event, port_events.PortEvent):
            args = [event.get_port()]

        elif isinstance(event, device_events.DeviceEvent):
            args = [event.get_attrs()]

        elif isinstance(event, slave_events.SlaveDeviceEvent):
            args = [event.get_slave()]

        try:
            await method(*args)

        except Exception as e:
            logger.error('failed to handle event %s: %s', event, e, exc_info=True)

    async def on_event(self, event):
        pass

    async def on_value_change(self, port):
        pass

    async def on_port_update(self, port):
        pass

    async def on_port_add(self, port):
        pass

    async def on_port_remove(self, port):
        pass

    async def on_device_update(self, attrs):
        pass

    async def on_slave_device_update(self, slave):
        pass

    async def on_slave_device_add(self, slave):
        pass

    async def on_slave_device_remove(self, slave):
        pass
