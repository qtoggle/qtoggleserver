
from qtoggleserver.core import api as core_api

from .base import DeviceEvent


class DeviceUpdate(DeviceEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = 'device-update'

    async def get_params(self):
        return self.attrs

    def is_duplicate(self, event):
        return isinstance(event, self.__class__)
