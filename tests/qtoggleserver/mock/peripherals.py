from typing import Any, Union

from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.typing import NullablePortValue
from qtoggleserver.peripherals import Peripheral, PeripheralPort


class MockPeripheralPort(PeripheralPort):
    TYPE = core_ports.TYPE_BOOLEAN

    async def read_value(self) -> NullablePortValue:
        return False


class MockPeripheral(Peripheral):
    def __init__(self, *, dummy_param: str, **kwargs) -> None:
        self._dummy_param: str = dummy_param
        super().__init__(**kwargs)

    async def make_port_args(self) -> list[Union[dict[str, Any], type[core_ports.BasePort]]]:
        return [
            {
                'driver': MockPeripheralPort,
                'id': 'id1',
            },
            {
                'driver': MockPeripheralPort,
                'id': 'id2',
            },
        ]
