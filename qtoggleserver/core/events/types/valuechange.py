
from qtoggleserver.core import api as core_api

from .base import PortEvent


class ValueChange(PortEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY
    TYPE = 'value-change'

    async def get_params(self):
        return {'id': self.port.get_id(), 'value': self.port.get_value()}

    def is_duplicate(self, event):
        return isinstance(event, self.__class__) and event.port == self.port
