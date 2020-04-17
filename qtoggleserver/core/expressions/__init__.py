
import re

from typing import Optional

from .base import Expression


def parse(self_port_id: Optional[str], sexpression: str, pos: int = 1) -> Expression:
    while sexpression and sexpression[0].isspace():
        sexpression = sexpression[1:]
        pos += 1

    while sexpression and sexpression[-1].isspace():
        sexpression = sexpression[:-1]

    if sexpression.startswith('$'):
        return PortValue.parse(self_port_id, sexpression, pos)

    elif '(' in sexpression or ')' in sexpression:
        return Function.parse(self_port_id, sexpression, pos)

    elif re.match(r'^[a-zA-Z0-9_.-]+$', sexpression):
        return LiteralValue.parse(self_port_id, sexpression, pos)

    else:
        raise exceptions.UnexpectedCharacter(',', pos)


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
from .functions import Function
from .literalvalues import LiteralValue
from .portvalue import PortValue
