
from qtoggleserver.core import api as core_api

from .base import Event


class PortEvent(Event):
    def __init__(self, port):
        self.port = port

        super().__init__()

    def __str__(self):
        return '{}({}) event'.format(self._type, self.port.get_id())


class PortAdd(PortEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY
    TYPE = 'port-add'

    async def get_params(self):
        return await self.port.to_json()


class PortRemove(PortEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY
    TYPE = 'port-remove'

    async def get_params(self):
        return {'id': self.port.get_id()}


class PortUpdate(PortEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY
    TYPE = 'port-update'

    async def get_params(self):
        return await self.port.to_json()

    def is_duplicate(self, event):
        return isinstance(event, self.__class__) and event.port == self.port


class ValueChange(PortEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY
    TYPE = 'value-change'

    async def get_params(self):
        return {'id': self.port.get_id(), 'value': self.port.get_value()}

    def is_duplicate(self, event):
        return isinstance(event, self.__class__) and event.port == self.port
