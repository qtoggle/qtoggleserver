import re

from qtoggleserver.core.typing import NullablePortValue as CoreNullablePortValue

from .base import EvalContext, EvalResult, Expression
from .exceptions import EmptyExpression, UnexpectedCharacter, ValueUnavailable


class LiteralValue(Expression):
    def __init__(self, value: CoreNullablePortValue, sexpression: str, role: int) -> None:
        super().__init__(role)

        self.value: CoreNullablePortValue = value
        self.sexpression: str = sexpression

    def __str__(self) -> str:
        return self.sexpression

    async def _eval(self, context: EvalContext) -> EvalResult:
        if self.value is None:
            raise ValueUnavailable

        return float(self.value)

    @staticmethod
    def parse(self_port_id: str | None, sexpression: str, role: int, pos: int) -> Expression:
        while sexpression and sexpression[0].isspace():
            sexpression = sexpression[1:]
            pos += 1

        while sexpression and sexpression[-1].isspace():
            sexpression = sexpression[:-1]

        if not sexpression:
            raise EmptyExpression()

        value: EvalResult | None

        if sexpression == "true":
            value = 1
        elif sexpression == "false":
            value = 0
        elif sexpression == "unavailable":
            value = None
        else:
            try:
                value = int(sexpression)
            except ValueError:
                try:
                    value = float(sexpression)
                except ValueError:
                    m = re.match(r"-?\d+(\.?\d+)?", sexpression)
                    if m:
                        raise UnexpectedCharacter(sexpression[m.end()], pos + m.end()) from None
                    else:
                        raise UnexpectedCharacter(sexpression[0], pos) from None

        return LiteralValue(value, sexpression, role)
