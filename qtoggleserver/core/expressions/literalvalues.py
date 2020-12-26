
import re

from typing import Optional

from qtoggleserver.core.typing import PortValue as CorePortValue

from .base import Expression, Evaluated
from .exceptions import UnexpectedCharacter, EmptyExpression


class LiteralValue(Expression):
    def __init__(self, value: CorePortValue, sexpression: str) -> None:
        self.value: CorePortValue = value
        self.sexpression: str = sexpression

    def __str__(self) -> str:
        return self.sexpression

    async def eval(self) -> Evaluated:
        return float(self.value)

    @staticmethod
    def parse(self_port_id: Optional[str], sexpression: str, pos: int) -> Expression:
        while sexpression and sexpression[0].isspace():
            sexpression = sexpression[1:]
            pos += 1

        while sexpression and sexpression[-1].isspace():
            sexpression = sexpression[:-1]

        if not sexpression:
            raise EmptyExpression()

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
                    m = re.match(r'-?\d+(\.?\d+)?', sexpression)
                    if m:
                        raise UnexpectedCharacter(sexpression[m.end()], pos + m.end()) from None

                    else:
                        raise UnexpectedCharacter(sexpression[0], pos) from None

        return LiteralValue(value, sexpression)
