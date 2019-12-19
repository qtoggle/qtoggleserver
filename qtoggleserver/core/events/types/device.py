
from qtoggleserver.core import api as core_api
from qtoggleserver.core.device import attrs as core_device_attrs

from .base import Event


class DeviceEvent(Event):
    def __init__(self):
        self.attrs = core_device_attrs.to_json()

        super().__init__()


class DeviceUpdate(DeviceEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = 'device-update'

    async def get_params(self):
        return self.attrs

    def is_duplicate(self, event):
        return isinstance(event, self.__class__)
