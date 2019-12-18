
from qtoggleserver.core import api as core_api

from .base import PortEvent


class PortUpdate(PortEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY
    TYPE = 'port-update'

    async def get_params(self):
        return await self.port.to_json()

    def is_duplicate(self, event):
        return isinstance(event, self.__class__) and event.port == self.port
