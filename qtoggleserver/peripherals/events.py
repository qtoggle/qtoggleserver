from qtoggleserver.core import api as core_api
from qtoggleserver.core import events as core_events
from qtoggleserver.core.typing import GenericJSONDict

from .peripheral import Peripheral


class PeripheralEvent(core_events.Event):
    def __init__(self, peripheral: Peripheral, timestamp: float | None = None) -> None:
        self._peripheral = peripheral

        super().__init__(timestamp)

    def __str__(self) -> str:
        return f"{self._type}({self._peripheral.get_id()}) event"

    def get_peripheral(self) -> Peripheral:
        return self._peripheral


class PeripheralAdd(PeripheralEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = "peripheral-add"

    async def get_params(self) -> GenericJSONDict:
        return self.get_peripheral().to_json()


class PeripheralRemove(PeripheralEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = "peripheral-remove"

    async def get_params(self) -> GenericJSONDict:
        return {"id": self.get_peripheral().get_id()}


class PeripheralUpdate(PeripheralEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = "peripheral-update"

    async def get_params(self) -> GenericJSONDict:
        return self.get_peripheral().to_json()

    def is_duplicate(self, event: core_events.Event) -> bool:
        return isinstance(event, self.__class__) and event.get_peripheral() == self.get_peripheral()
