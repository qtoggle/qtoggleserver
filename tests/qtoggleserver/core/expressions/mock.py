
from typing import Optional

from qtoggleserver.core.expressions import Expression


class MockExpression(Expression):
    def __init__(self, value: Optional[float] = None) -> None:
        self.value: Optional[float] = value

    def set_value(self, value: Optional[float]) -> None:
        self.value = value

    def eval(self) -> float:
        return self.value

    @staticmethod
    def parse(self_port_id: Optional[str], sexpression: str, pos: int) -> Expression:
        pass
