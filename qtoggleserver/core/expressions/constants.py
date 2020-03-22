
from typing import Optional

from qtoggleserver.core.typing import PortValue as CorePortValue

from .base import Expression
from .exceptions import InvalidExpression


class Constant(Expression):
    def __init__(self, value: CorePortValue, sexpression: str) -> None:
        self.value: CorePortValue = value
        self.sexpression: str = sexpression

    def __str__(self) -> str:
        return self.sexpression

    def eval(self) -> CorePortValue:
        return self.value

    @staticmethod
    def parse(self_port_id: Optional[str], sexpression: str) -> Expression:
        sexpression = sexpression.strip()

        if sexpression == 'true':
            value = 1

        elif sexpression == 'false':
            value = 0

        else:
            try:
                value = int(sexpression)

            except ValueError:
                try:
                    value = float(sexpression)

                except ValueError:
                    raise InvalidExpression(f'"{sexpression}" is not a valid constant') from None

        return Constant(value, sexpression)
