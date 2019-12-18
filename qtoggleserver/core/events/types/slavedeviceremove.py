
from qtoggleserver.core import api as core_api

from .base import SlaveDeviceEvent


class SlaveDeviceRemove(SlaveDeviceEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = 'slave-device-remove'

    async def get_params(self):
        return {'name': self.slave.get_name()}
