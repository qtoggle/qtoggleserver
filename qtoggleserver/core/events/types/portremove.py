
from qtoggleserver.core import api as core_api

from .base import PortEvent


class PortRemove(PortEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY
    TYPE = 'port-remove'

    async def get_params(self):
        return {'id': self.port.get_id()}
