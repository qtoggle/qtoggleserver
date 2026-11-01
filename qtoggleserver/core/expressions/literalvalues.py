import re

from qtoggleserver.core.typing import NullablePortValue

from .base import EvalContext, EvalResult, Expression, Role
from .exceptions import EmptyExpression, UnexpectedCharacter, ValueUnavailable


_NUMBER_RE = re.compile(r"-?[0-9]+(\.[0-9]+)?")


class LiteralValue(Expression):
    def __init__(self, value: NullablePortValue, sexpression: str, role: Role) -> None:
        super().__init__(role)

        self.sexpression: str = sexpression
        self._coerced_value: EvalResult | None = value
        if isinstance(value, bool):
            self._coerced_value = int(value)

    def __str__(self) -> str:
        return self.sexpression

    async def _eval(self, context: EvalContext) -> EvalResult:
        if self._coerced_value is None:
            raise ValueUnavailable
        return self._coerced_value

    @staticmethod
    def parse(self_port_id: str | None, sexpression: str, role: Role, pos: int) -> Expression:
        stripped = sexpression.lstrip()
        pos += len(sexpression) - len(stripped)
        sexpression = stripped.rstrip()

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
            # Only base 10 digits, an optional minus sign and a dot between digits, unlike Python's int() and float()
            m = _NUMBER_RE.match(sexpression)
            if not m:
                raise UnexpectedCharacter(sexpression[0], pos)
            if m.end() < len(sexpression):
                raise UnexpectedCharacter(sexpression[m.end()], pos + m.end())

            if m.group(1):
                value = float(sexpression)
            else:
                try:
                    value = int(sexpression)
                except ValueError:  # too many digits for Python; like an overflowing float, it becomes infinity
                    value = float(sexpression)

        return LiteralValue(value, sexpression, role)
