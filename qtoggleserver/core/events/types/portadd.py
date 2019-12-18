
from qtoggleserver.core import api as core_api

from .base import PortEvent


class PortAdd(PortEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY
    TYPE = 'port-add'

    async def get_params(self):
        return await self.port.to_json()
