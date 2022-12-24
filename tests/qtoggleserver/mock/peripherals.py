from typing import Any, Union

from qtoggleserver.core import ports as core_ports
from qtoggleserver.peripherals import Peripheral

from tests.qtoggleserver.mock.ports import MockBooleanPort, MockNumberPort


class MockPeripheral(Peripheral):
    def __init__(self, *, dummy_param: str, **kwargs) -> None:
        self._dummy_param: str = dummy_param
        super().__init__(**kwargs)

    async def make_port_args(self) -> list[Union[dict[str, Any], type[core_ports.BasePort]]]:
        return [
            {
                'driver': MockBooleanPort,
                'port_id': 'bid1',
                'value': False,
            },
            {
                'driver': MockNumberPort,
                'port_id': 'nid1',
                'value': 1,
            },
        ]
