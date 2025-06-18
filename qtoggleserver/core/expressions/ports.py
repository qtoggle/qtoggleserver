from __future__ import annotations

import abc
import re

from qtoggleserver.core import ports as core_ports

from . import ROLE_TRANSFORM_READ, ROLE_TRANSFORM_WRITE
from .base import EvalContext, EvalResult, Expression
from .exceptions import DisabledPort, PortValueUnavailable, UnexpectedCharacter, UnknownPortId


class PortExpression(Expression, metaclass=abc.ABCMeta):
    def __init__(self, port_id: str, prefix: str, role: int) -> None:
        super().__init__(role)

        self.port_id: str = port_id
        self.prefix: str = prefix

    def get_port(self) -> core_ports.BasePort:
        return core_ports.get(self.port_id)

    @staticmethod
    def parse(self_port_id: str | None, sexpression: str, role: int, pos: int) -> Expression:
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
            m = re.search(r"[^a-zA-Z0-9_.-]", port_id)
            if m:
                p = m.start()
                raise UnexpectedCharacter(port_id[p], p + pos + 2)

            if prefix == "$":
                return PortValue(port_id, prefix, role)
            else:  # assuming prefix == '@'
                return PortRef(port_id, prefix, role)
        else:
            if prefix == "$":
                return SelfPortValue(self_port_id, prefix, role)
            else:  # assuming prefix == '@'
                return SelfPortRef(self_port_id, prefix, role)


class PortValue(PortExpression):
    def __str__(self) -> str:
        return f"{self.prefix}{self.port_id}"

    def _get_deps(self) -> set[str]:
        return {f"${self.port_id}"}

    async def _eval(self, context: EvalContext) -> EvalResult:
        port = self.get_port()
        if not port:
            raise UnknownPortId(self.port_id)

        if not port.is_enabled():
            raise DisabledPort(self.port_id)

        value = context.port_values.get(self.port_id)
        if value is None:
            raise PortValueUnavailable(self.port_id)

        return value


class SelfPortValue(PortValue):
    def __str__(self) -> str:
        return self.prefix

    async def _eval(self, context: EvalContext) -> EvalResult:
        if self.role in (ROLE_TRANSFORM_READ, ROLE_TRANSFORM_WRITE):
            return await super()._eval(context)

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
        return f"{self.prefix}{self.port_id}"

    async def _eval(self, context: EvalContext) -> EvalResult:
        port = self.get_port()
        if not port:
            raise UnknownPortId(self.port_id)

        return port.get_id()


class SelfPortRef(PortRef):
    def __str__(self) -> str:
        return self.prefix
