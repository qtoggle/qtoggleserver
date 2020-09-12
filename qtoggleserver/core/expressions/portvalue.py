
import re

from typing import Optional, Set

from .base import Expression
from .exceptions import UnknownPortId, DisabledPort, UndefinedPortValue, UnexpectedCharacter

# Import core.ports after defining Expression, because core.ports.BasePort depends on Expression.
from qtoggleserver.core import ports as core_ports


class PortValue(Expression):
    def __init__(self, port_id: str) -> None:
        self.port_id: str = port_id

    def __str__(self) -> str:
        return f'${self.port_id}'

    def get_deps(self) -> Set[str]:
        return {f'${self.port_id}'}

    def get_port(self) -> core_ports.BasePort:
        return core_ports.get(self.port_id)

    def eval(self) -> float:
        port = self.get_port()
        if not port:
            raise UnknownPortId(self.port_id)

        if not port.is_enabled():
            raise DisabledPort(self.port_id)

        value = port.get_value()
        if value is None:
            raise UndefinedPortValue(self.port_id)

        return float(value)

    @staticmethod
    def parse(self_port_id: Optional[str], sexpression: str, pos: int) -> Expression:
        while sexpression and sexpression[0].isspace():
            sexpression = sexpression[1:]
            pos += 1

        while sexpression and sexpression[-1].isspace():
            sexpression = sexpression[:-1]

        port_id = sexpression[1:]

        if port_id:
            m = re.search(r'[^a-zA-Z0-9_.-]', port_id)
            if m:
                p = m.start()
                raise UnexpectedCharacter(port_id[p], p + pos + 2)

            return PortValue(port_id)

        else:
            return SelfPortValue(self_port_id)


class SelfPortValue(PortValue):
    def __str__(self) -> str:
        return '$'
