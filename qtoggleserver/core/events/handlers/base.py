
import abc
import logging


logger = logging.getLogger(__package__)


class EventHandler(metaclass=abc.ABCMeta):
    async def handle_event(self, event):
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

        try:
            await method(*event.get_handler_args())

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
