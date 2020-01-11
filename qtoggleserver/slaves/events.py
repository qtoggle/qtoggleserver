
from typing import Any

from qtoggleserver.core import api as core_api
from qtoggleserver.core import events as core_events
from qtoggleserver.core.typing import GenericJSONDict


# We can't use proper type annotations for slaves in this module because that would create unsolvable circular imports.
# Therefore we use "Any" type annotation for Slave instances.


class SlaveDeviceEvent(core_events.Event):
    def __init__(self, slave: Any, timestamp: float = None) -> None:
        self._slave = slave

        super().__init__(timestamp)

    def __str__(self) -> str:
        return f'{self._type}({self._slave.get_name()}) event'

    def get_slave(self) -> Any:
        return self._slave


class SlaveDeviceAdd(SlaveDeviceEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = 'slave-device-add'

    async def get_params(self) -> GenericJSONDict:
        return self.get_slave().to_json()


class SlaveDeviceRemove(SlaveDeviceEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = 'slave-device-remove'

    async def get_params(self) -> GenericJSONDict:
        return {'name': self.get_slave().get_name()}


class SlaveDeviceUpdate(SlaveDeviceEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = 'slave-device-update'

    async def get_params(self) -> GenericJSONDict:
        return self.get_slave().to_json()

    def is_duplicate(self, event: core_events.Event) -> bool:
        return isinstance(event, self.__class__) and event.get_slave() == self.get_slave()
