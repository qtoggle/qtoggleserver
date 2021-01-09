
from typing import Optional


# This needs to be imported here to determine a correct order of some partially imported modules (core.ports,
# core.expressions and core.main)
from qtoggleserver.core import main

from .base import Expression, Evaluated


# A time jump of more than one day will prevent the evaluation of expressions such as time-processing
TIME_JUMP_THRESHOLD = 86400


def parse(self_port_id: Optional[str], sexpression: str, pos: int = 1) -> Expression:
    while sexpression and sexpression[0].isspace():
        sexpression = sexpression[1:]
        pos += 1

    while sexpression and sexpression[-1].isspace():
        sexpression = sexpression[:-1]

    if sexpression.startswith('$') or sexpression.startswith('@'):
        return PortExpression.parse(self_port_id, sexpression, pos)

    elif '(' in sexpression or ')' in sexpression:
        return Function.parse(self_port_id, sexpression, pos)

    else:
        return LiteralValue.parse(self_port_id, sexpression, pos)


# Import core.ports after defining Expression, because core.ports.BasePort depends on Expression.
from qtoggleserver.core import ports as core_ports


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

            expr = await p.get_expression()
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


from .exceptions import *
from .exceptions import CircularDependency
from .functions import Function
from .literalvalues import LiteralValue
from .port import PortExpression, PortValue, PortRef
