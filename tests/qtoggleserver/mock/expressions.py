from typing import Optional

from qtoggleserver.core.expressions import (
    ROLE_VALUE,
    EvalContext,
    EvalResult,
    Expression,
    PortRef,
    PortValue,
    PortValueUnavailable,
    UnknownPortId,
)
from qtoggleserver.core.ports import BasePort  # this needs to be imported after qtoggleserver.core.expressions


class MockExpression(Expression):
    def __init__(self, value: Optional[float] = None) -> None:
        self.value: Optional[float] = value

        super().__init__(role=ROLE_VALUE)

    def set_value(self, value: Optional[float]) -> None:
        self.value = value

    async def _eval(self, context: EvalContext) -> EvalResult:
        return self.value

    @staticmethod
    def parse(self_port_id: Optional[str], sexpression: str, role: int, pos: int) -> Expression:
        pass


class MockPortValue(PortValue):
    def __init__(self, port: Optional[BasePort], port_id: Optional[str] = None) -> None:
        super().__init__(port_id or port.get_id(), prefix='$', role=ROLE_VALUE)

        self.port: Optional[BasePort] = port

    async def _eval(self, context: EvalContext) -> EvalResult:
        if self.port:
            value = context.port_values.get(self.port.get_id())
            if value is None:
                raise PortValueUnavailable(self.port.get_id())

            return value
        else:
            raise UnknownPortId(self.port_id)


class MockPortRef(PortRef):
    def __init__(self, port: Optional[BasePort], port_id: Optional[str] = None) -> None:
        super().__init__(port_id or port.get_id(), prefix='@', role=ROLE_VALUE)

        self.port: Optional[BasePort] = port

    async def _eval(self, context: EvalContext) -> EvalResult:
        if self.port:
            return self.port
        else:
            raise UnknownPortId(self.port_id)
