
import re

from typing import Any, Dict, Optional

from qtoggleserver.core.typing import NullablePortValue as CoreNullablePortValue

from .base import Expression, Evaluated
from .exceptions import UnexpectedCharacter, EmptyExpression, ValueUnavailable


class LiteralValue(Expression):
    def __init__(self, value: CoreNullablePortValue, sexpression: str) -> None:
        super().__init__()

        self.value: CoreNullablePortValue = value
        self.sexpression: str = sexpression

    def __str__(self) -> str:
        return self.sexpression

    async def eval(self, context: Dict[str, Any]) -> Evaluated:
        if self.value is None:
            raise ValueUnavailable

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
        elif sexpression == 'unavailable':
            value = None
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
