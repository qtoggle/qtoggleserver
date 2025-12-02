from qtoggleserver.core import expressions as core_expressions
from qtoggleserver.core.ports import TYPE_BOOLEAN, TYPE_NUMBER, Port, SkipRead
from qtoggleserver.core.typing import NullablePortValue


class MockPort(Port):
    def __init__(self, port_id: str, value: NullablePortValue) -> None:
        super().__init__(port_id)

        self.set_last_read_value(value)
        self._writable: bool = False
        self._next_value: NullablePortValue = None

    async def read_value(self) -> NullablePortValue:
        if self._next_value is None:
            raise SkipRead()

        value = self._next_value
        self._next_value = None
        return value

    async def write_value(self, value: NullablePortValue) -> None:
        pass

    def set_next_value(self, value: NullablePortValue) -> None:
        self._next_value = value

    def set_writable(self, writable: bool) -> None:
        self._writable = writable
        self.invalidate_attrs()

    def set_expression(self, sexpression: str) -> None:
        expression = core_expressions.parse(self.get_id(), sexpression, role=core_expressions.Role.VALUE)
        self._expression = expression


class MockBooleanPort(MockPort):
    TYPE = TYPE_BOOLEAN


class MockNumberPort(MockPort):
    TYPE = TYPE_NUMBER
