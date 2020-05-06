
from qtoggleserver.core import api as core_api
from qtoggleserver.core.device import attrs as core_device_attrs
from qtoggleserver.core.typing import Attributes, GenericJSONDict

from .base import Event


class DeviceEvent(Event):
    def __init__(self, timestamp: float = None) -> None:
        self._attrs: Attributes = core_device_attrs.to_json()

        super().__init__(timestamp)

    def get_attrs(self) -> Attributes:
        return self._attrs


class DeviceUpdate(DeviceEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = 'device-update'

    async def get_params(self) -> GenericJSONDict:
        return self.get_attrs()

    def is_duplicate(self, event: Event) -> bool:
        return isinstance(event, self.__class__)


class FullUpdate(DeviceEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY
    TYPE = 'full-update'

    def is_duplicate(self, event: Event) -> bool:
        return isinstance(event, self.__class__)
