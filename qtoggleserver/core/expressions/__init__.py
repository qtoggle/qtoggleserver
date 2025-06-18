from __future__ import annotations

from qtoggleserver.core import ports as core_ports

from .base import EvalContext, EvalResult, Expression
from .exceptions import CircularDependency
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
    "check_loops",
    "parse",
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


async def check_loops(port: core_ports.BasePort, expression: Expression) -> None:
    seen_ports = {port}

    async def check_loops_rec(level: int, e: Expression) -> int:
        if isinstance(e, PortValue):
            p = e.get_port()
            if not p:
                return 0

            # A loop is detected when we stumble upon the initial port at a level deeper than 1
            if port is p and level > 1:
                return level

            # Avoid visiting the same port twice
            if p in seen_ports:
                return 0

            seen_ports.add(p)

            expr = p.get_expression()
            if expr:
                lv = await check_loops_rec(level + 1, expr)
                if lv:
                    return lv

            return 0
        elif isinstance(e, Function):
            for arg in e.args:
                lv = await check_loops_rec(level, arg)
                if lv:
                    return lv

        return 0

    if await check_loops_rec(1, expression) > 1:
        raise CircularDependency(port.get_id())


from .functions import Function  # noqa: E402
from .ports import PortExpression, PortValue  # noqa: E402
