
from typing import Any

from qtoggleserver.core import api as core_api
from qtoggleserver.core.typing import GenericJSONDict

from .base import Event


# We can't use proper type annotations for ports in this module because that would create unsolvable circular imports.
# Therefore we use "Any" type annotation for BasePort instances.


class PortEvent(Event):
    def __init__(self, port: Any, timestamp: float = None) -> None:
        self._port = port

        super().__init__(timestamp)

    def __str__(self) -> str:
        return f'{self._type}({self._port.get_id()}) event'

    def get_port(self) -> Any:
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
        return {'id': self.get_port().get_id(), 'value': self.get_port().get_last_read_value()}
