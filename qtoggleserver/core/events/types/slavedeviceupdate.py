
from qtoggleserver.core import api as core_api

from .base import SlaveDeviceEvent


class SlaveDeviceUpdate(SlaveDeviceEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = 'slave-device-update'

    async def get_params(self):
        return self.slave.to_json()

    def is_duplicate(self, event):
        return isinstance(event, self.__class__) and event.slave == self.slave
