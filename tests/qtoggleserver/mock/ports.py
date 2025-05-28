from qtoggleserver.core.ports import TYPE_BOOLEAN, TYPE_NUMBER, Port, SkipRead
from qtoggleserver.core.typing import NullablePortValue


class MockPort(Port):
    def __init__(self, port_id: str, value: NullablePortValue) -> None:
        super().__init__(port_id)

        self.set_last_read_value(value)
        self._writable: bool = False
        self._next_value: NullablePortValue = None
        self._last_written_value: NullablePortValue = None

    async def read_value(self) -> NullablePortValue:
        if self._next_value is None:
            raise SkipRead()

        value = self._next_value
        self._next_value = None
        return value

    async def write_value(self, value: NullablePortValue) -> None:
        self._last_written_value = value

    def set_next_value(self, value: NullablePortValue) -> None:
        self._next_value = value

    def set_writable(self, writable: bool) -> None:
        self._writable = writable
        self.invalidate_attrs()

    def get_last_written_value(self) -> NullablePortValue:
        return self._last_written_value


class MockBooleanPort(MockPort):
    TYPE = TYPE_BOOLEAN


class MockNumberPort(MockPort):
    TYPE = TYPE_NUMBER
