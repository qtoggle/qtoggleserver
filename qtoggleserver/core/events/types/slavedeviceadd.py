
from qtoggleserver.core import api as core_api

from .base import SlaveDeviceEvent


class SlaveDeviceAdd(SlaveDeviceEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = 'slave-device-add'

    async def get_params(self):
        return self.slave.to_json()
