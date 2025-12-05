from __future__ import annotations

from .base import (
    DEP_ASAP,
    DEP_DAY,
    DEP_HOUR,
    DEP_MINUTE,
    DEP_MONTH,
    DEP_SECOND,
    DEP_YEAR,
    EvalContext,
    EvalResult,
    Expression,
    Role,
)
from .literalvalues import LiteralValue


__all__ = [
    "DEP_ASAP",
    "DEP_DAY",
    "DEP_HOUR",
    "DEP_MINUTE",
    "DEP_MONTH",
    "DEP_SECOND",
    "DEP_YEAR",
    "EvalContext",
    "EvalResult",
    "Expression",
    "Function",
    "Role",
    "aggregation",
    "arithmetic",
    "bitwise",
    "branching",
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


# A time jump of more than one day will prevent the evaluation of expressions such as time-processing
TIME_JUMP_THRESHOLD = 86_400_000


def parse(self_port_id: str | None, sexpression: str, role: Role, pos: int = 1) -> Expression:
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
    branching,
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
