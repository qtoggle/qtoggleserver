
from qtoggleserver.core import api as core_api
from qtoggleserver.slaves import devices as slaves_devices
from qtoggleserver.core.typing import GenericJSONDict

from .base import Event


class SlaveDeviceEvent(Event):
    def __init__(self, slave: slaves_devices.Slave, timestamp: float = None) -> None:
        self._slave: slaves_devices.Slave = slave

        super().__init__(timestamp)

    def __str__(self) -> str:
        return f'{self._type}({self._slave.get_name()}) event'

    def get_slave(self) -> slaves_devices.Slave:
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

    def is_duplicate(self, event: Event) -> bool:
        return isinstance(event, self.__class__) and event.get_slave() == self.get_slave()
