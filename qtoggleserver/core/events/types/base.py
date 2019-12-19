
import abc
import logging

from qtoggleserver.core import api as core_api
from qtoggleserver.core.device import attrs as core_device_attrs


logger = logging.getLogger(__package__)


class Event(metaclass=abc.ABCMeta):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_NONE
    TYPE = 'base-event'

    def __init__(self):
        self._type = self.TYPE

    def __str__(self):
        return '{} event'.format(self._type)

    async def to_json(self):
        return {
            'type': self._type,
            'params': await self.get_params()
        }

    async def get_params(self):
        return {}

    def get_type(self):
        return self._type

    def is_duplicate(self, event):
        return False


class DeviceEvent(Event):
    def __init__(self):
        self.attrs = core_device_attrs.to_json()

        super().__init__()


class PortEvent(Event):
    def __init__(self, port):
        self.port = port

        super().__init__()

    def __str__(self):
        return '{}({}) event'.format(self._type, self.port.get_id())


class SlaveDeviceEvent(Event):
    def __init__(self, slave):
        self.slave = slave

        super().__init__()

    def __str__(self):
        return '{}({}) event'.format(self._type, self.slave.get_name())
