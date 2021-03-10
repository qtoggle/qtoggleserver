
from qtoggleserver.core.ports import Port, TYPE_NUMBER, TYPE_BOOLEAN
from qtoggleserver.core.typing import NullablePortValue


class MockPort(Port):
    def __init__(
        self,
        port_id: str,
        value: NullablePortValue
    ) -> None:
        super().__init__(port_id)

        self.set_last_read_value(value)
        self._writable: bool = False
        self._next_value: NullablePortValue = None

    async def read_value(self) -> NullablePortValue:
        value = self._next_value
        self._next_value = None
        return value

    def set_writable(self, writable: bool) -> None:
        self._writable = writable
        self.invalidate_attrs()

    def set_next_value(self, value: NullablePortValue) -> None:
        self._next_value = value


class BooleanMockPort(MockPort):
    TYPE = TYPE_BOOLEAN


class NumberMockPort(MockPort):
    TYPE = TYPE_NUMBER
