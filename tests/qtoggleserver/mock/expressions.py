
from typing import Optional

from qtoggleserver.core.expressions import Expression, Evaluated, PortRef
from qtoggleserver.core.ports import BasePort  # This needs to be imported after qtoggleserver.core.expressions


class MockExpression(Expression):
    def __init__(self, value: Optional[float] = None) -> None:
        self.value: Optional[float] = value

    def set_value(self, value: Optional[float]) -> None:
        self.value = value

    async def eval(self) -> Evaluated:
        return self.value

    @staticmethod
    def parse(self_port_id: Optional[str], sexpression: str, pos: int) -> Expression:
        pass


class MockPortRef(PortRef):
    def __init__(self, port: BasePort) -> None:
        super().__init__(port.get_id())

        self.port: BasePort = port

    async def eval(self) -> Evaluated:
        return self.port
