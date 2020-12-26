
from qtoggleserver.core.ports import Port
from qtoggleserver.core.typing import NullablePortValue


class MockPort(Port):
    def __init__(self, port_id: str, value: NullablePortValue) -> None:
        super().__init__(port_id)

        self.set_value(value)

    async def read_value(self) -> NullablePortValue:
        pass
