
from qtoggleserver.core import api as core_api
from qtoggleserver.core.device import attrs as core_device_attrs

from .base import Event


class DeviceEvent(Event):
    def __init__(self, timestamp=None):
        self._attrs = core_device_attrs.to_json()

        super().__init__(timestamp)

    def get_attrs(self):
        return self._attrs


class DeviceUpdate(DeviceEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = 'device-update'

    async def get_params(self):
        return self.get_attrs()

    def is_duplicate(self, event):
        return isinstance(event, self.__class__)
