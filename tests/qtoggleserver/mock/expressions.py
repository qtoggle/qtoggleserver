from qtoggleserver.core.expressions import ROLE_VALUE, EvalContext, EvalResult, Expression
from qtoggleserver.core.expressions.exceptions import PortValueUnavailable, UnknownPortId
from qtoggleserver.core.expressions.ports import PortRef, PortValue
from qtoggleserver.core.ports import BasePort


class MockExpression(Expression):
    def __init__(self, value: float | None = None) -> None:
        self.value: float | None = value

        super().__init__(role=ROLE_VALUE)

    def set_value(self, value: float | None) -> None:
        self.value = value

    async def _eval(self, context: EvalContext) -> EvalResult:
        return self.value

    @staticmethod
    def parse(self_port_id: str | None, sexpression: str, role: int, pos: int) -> Expression:
        pass


class MockPortValue(PortValue):
    def __init__(self, port: BasePort | None, port_id: str | None = None) -> None:
        super().__init__(port_id or port.get_id(), prefix="$", role=ROLE_VALUE)

        self.port: BasePort | None = port

    async def _eval(self, context: EvalContext) -> EvalResult:
        if self.port:
            value = context.port_values.get(self.port.get_id())
            if value is None:
                raise PortValueUnavailable(self.port.get_id())

            return value
        else:
            raise UnknownPortId(self.port_id)


class MockPortRef(PortRef):
    def __init__(self, port: BasePort | None, port_id: str | None = None) -> None:
        super().__init__(port_id or port.get_id(), prefix="@", role=ROLE_VALUE)

        self.port: BasePort | None = port

    async def _eval(self, context: EvalContext) -> EvalResult:
        if self.port:
            return self.port.get_id()
        else:
            raise UnknownPortId(self.port_id)
