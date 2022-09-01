
import abc
import re

from typing import Any, Dict, Optional, Set

from .base import Expression, Evaluated
from .exceptions import UnknownPortId, DisabledPort, PortValueUnavailable, UnexpectedCharacter

# Import core.ports after defining Expression, because core.ports.BasePort depends on Expression.
from qtoggleserver.core import ports as core_ports


class PortExpression(Expression, metaclass=abc.ABCMeta):
    def __init__(self, port_id: str, prefix: str) -> None:
        super().__init__()

        self.port_id: str = port_id
        self.prefix: str = prefix

    def get_port(self) -> core_ports.BasePort:
        return core_ports.get(self.port_id)

    @staticmethod
    def parse(self_port_id: Optional[str], sexpression: str, pos: int) -> Expression:
        # Remove leading whitespace
        while sexpression and sexpression[0].isspace():
            sexpression = sexpression[1:]
            pos += 1

        # Remove trailing whitespace
        while sexpression and sexpression[-1].isspace():
            sexpression = sexpression[:-1]

        prefix = sexpression[0]
        port_id = sexpression[1:]

        if port_id:
            m = re.search(r'[^a-zA-Z0-9_.-]', port_id)
            if m:
                p = m.start()
                raise UnexpectedCharacter(port_id[p], p + pos + 2)

            if prefix == '$':
                return PortValue(port_id, prefix)
            else:  # Assuming prefix == '@'
                return PortRef(port_id, prefix)

        else:
            if prefix == '$':
                return SelfPortValue(self_port_id, prefix)
            else:  # Assuming prefix == '@'
                return SelfPortRef(self_port_id, prefix)


class PortValue(PortExpression):
    def __str__(self) -> str:
        return f'{self.prefix}{self.port_id}'

    def get_deps(self) -> Set[str]:
        return {f'${self.port_id}'}

    async def eval(self, context: Dict[str, Any]) -> Evaluated:
        port = self.get_port()
        if not port:
            raise UnknownPortId(self.port_id)

        if not port.is_enabled():
            raise DisabledPort(self.port_id)

        value = context.get('port_values', {}).get(self.port_id)
        if value is None:
            raise PortValueUnavailable(self.port_id)

        return value


class SelfPortValue(PortValue):
    def __str__(self) -> str:
        return self.prefix

    async def eval(self, context: Dict[str, Any]) -> Evaluated:
        port = self.get_port()
        if not port:
            raise UnknownPortId(self.port_id)

        if not port.is_enabled():
            raise DisabledPort(self.port_id)

        value = port.get_last_read_value()
        if value is None:
            raise PortValueUnavailable(self.port_id)

        return value


class PortRef(PortExpression):
    def __str__(self) -> str:
        return f'{self.prefix}{self.port_id}'

    async def eval(self, context: Dict[str, Any]) -> Evaluated:
        port = self.get_port()
        if not port:
            raise UnknownPortId(self.port_id)

        return port


class SelfPortRef(PortRef):
    def __str__(self) -> str:
        return self.prefix
