
from typing import Any, Dict, Optional

from qtoggleserver.core.expressions import Expression, Evaluated, PortValue, PortRef
from qtoggleserver.core.expressions import UnknownPortId, PortValueUnavailable
from qtoggleserver.core.ports import BasePort  # This needs to be imported after qtoggleserver.core.expressions


class MockExpression(Expression):
    def __init__(self, value: Optional[float] = None) -> None:
        self.value: Optional[float] = value

    def set_value(self, value: Optional[float]) -> None:
        self.value = value

    async def eval(self, context: EvalContext) -> Evaluated:
        return self.value

    @staticmethod
    def parse(self_port_id: Optional[str], sexpression: str, pos: int) -> Expression:
        pass


class MockPortValue(PortValue):
    def __init__(self, port: Optional[BasePort], port_id: Optional[str] = None) -> None:
        super().__init__(port_id or port.get_id(), prefix='$')

        self.port: Optional[BasePort] = port

    async def eval(self, context: EvalContext) -> Evaluated:
        if self.port:
            value = context['port_values'].get(self.port.get_id())
            if value is None:
                raise PortValueUnavailable(self.port.get_id())

            return value

        else:
            raise UnknownPortId(self.port_id)


class MockPortRef(PortRef):
    def __init__(self, port: Optional[BasePort], port_id: Optional[str] = None) -> None:
        super().__init__(port_id or port.get_id(), prefix='@')

        self.port: Optional[BasePort] = port

    async def eval(self, context: EvalContext) -> Evaluated:
        if self.port:
            return self.port

        else:
            raise UnknownPortId(self.port_id)
