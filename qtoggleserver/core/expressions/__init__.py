from __future__ import annotations

from .base import EvalContext, EvalResult, Expression
from .literalvalues import LiteralValue


__all__ = [
    "ROLE_FILTER",
    "ROLE_TRANSFORM_READ",
    "ROLE_TRANSFORM_WRITE",
    "ROLE_VALUE",
    "EvalContext",
    "EvalResult",
    "Expression",
    "Function",
    "aggregation",
    "arithmetic",
    "bitwise",
    "comparison",
    "date",
    "logic",
    "parse",
    "rounding",
    "sign",
    "time",
    "timeprocessing",
    "various",
]

ROLE_VALUE = 1
ROLE_TRANSFORM_READ = 2
ROLE_TRANSFORM_WRITE = 3
ROLE_FILTER = 4

# A time jump of more than one day will prevent the evaluation of expressions such as time-processing
TIME_JUMP_THRESHOLD = 86_400_000


def parse(self_port_id: str | None, sexpression: str, role: int, pos: int = 1) -> Expression:
    while sexpression and sexpression[0].isspace():
        sexpression = sexpression[1:]
        pos += 1

    while sexpression and sexpression[-1].isspace():
        sexpression = sexpression[:-1]

    if sexpression and sexpression[0] in ("$", "@"):
        return PortExpression.parse(self_port_id, sexpression, role, pos)
    elif "(" in sexpression or ")" in sexpression:
        return Function.parse(self_port_id, sexpression, role, pos)
    else:
        return LiteralValue.parse(self_port_id, sexpression, role, pos)


from . import (  # noqa: E402
    aggregation,
    arithmetic,
    bitwise,
    comparison,
    date,
    logic,
    rounding,
    sign,
    time,
    timeprocessing,
    various,
)
from .functions import Function  # noqa: E402
from .ports import PortExpression  # noqa: E402
