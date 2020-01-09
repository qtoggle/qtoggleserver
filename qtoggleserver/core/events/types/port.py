
from qtoggleserver.core import api as core_api
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.typing import GenericJSONDict

from .base import Event


class PortEvent(Event):
    def __init__(self, port: core_ports.BasePort, timestamp: float = None) -> None:
        self._port: core_ports.BasePort = port

        super().__init__(timestamp)

    def __str__(self) -> str:
        return f'{self._type}({self._port.get_id()}) event'

    def get_port(self) -> core_ports.BasePort:
        return self._port


class PortAdd(PortEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY
    TYPE = 'port-add'

    async def get_params(self) -> GenericJSONDict:
        return await self.get_port().to_json()


class PortRemove(PortEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY
    TYPE = 'port-remove'

    async def get_params(self) -> GenericJSONDict:
        return {'id': self.get_port().get_id()}


class PortUpdate(PortEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY
    TYPE = 'port-update'

    async def get_params(self) -> GenericJSONDict:
        return await self.get_port().to_json()

    def is_duplicate(self, event: Event) -> bool:
        return isinstance(event, self.__class__) and event.get_port() == self.get_port()


class ValueChange(PortEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY
    TYPE = 'value-change'

    async def get_params(self) -> GenericJSONDict:
        return {'id': self.get_port().get_id(), 'value': self.get_port().get_value()}

    def is_duplicate(self, event: Event) -> bool:
        return isinstance(event, self.__class__) and event.get_port() == self.get_port()
