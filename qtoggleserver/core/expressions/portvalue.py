
from typing import Optional, Set

from qtoggleserver.core.typing import PortValue as CorePortValue

from .base import Expression
from .exceptions import IncompleteExpression

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

    def eval(self) -> CorePortValue:
        port = self.get_port()
        if not port:
            raise IncompleteExpression(f'Unknown port {self.port_id}')

        if not port.is_enabled():
            raise IncompleteExpression(f'{port} is disabled')

        value = port.get_value()
        if value is None:
            raise IncompleteExpression(f'Value of port {port} is undefined')

        return float(value)

    @staticmethod
    def parse(self_port_id: Optional[str], sexpression: str) -> Expression:
        sexpression = sexpression.strip()
        port_id = sexpression.strip('$')

        if port_id:
            return PortValue(port_id)

        else:
            return SelfPortValue(self_port_id)


class SelfPortValue(PortValue):
    def __str__(self) -> str:
        return '$'
