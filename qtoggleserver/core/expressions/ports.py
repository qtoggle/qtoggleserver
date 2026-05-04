from __future__ import annotations

import abc
import re

from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.typing import NullablePortValue

from .base import EvalContext, EvalResult, Expression, Role
from .exceptions import DisabledPort, PortAttrUnavailable, PortValueUnavailable, UnexpectedCharacter, UnknownPortId


class PortExpression(Expression, metaclass=abc.ABCMeta):
    def __init__(self, port_id: str, prefix: str, role: Role, attr_name: str | None = None) -> None:
        super().__init__(role)

        self.port_id: str = port_id
        self.attr_name: str | None = attr_name
        self.prefix: str = prefix
        self._cached_port: core_ports.BasePort | None = None

    def get_port(self) -> core_ports.BasePort | None:
        # TODO: test what happens if a port is removed; do we need this `is_removed` check?
        port = self._cached_port
        if port is None or port.is_removed():
            port = core_ports.get(self.port_id)
            self._cached_port = port
        return port

    @staticmethod
    def parse(self_port_id: str | None, sexpression: str, role: Role, pos: int) -> Expression:
        stripped = sexpression.lstrip()
        pos += len(sexpression) - len(stripped)
        sexpression = stripped.rstrip()

        prefix = sexpression[0]
        sub_sexpression = sexpression[1:]

        if sub_sexpression:
            parts = sub_sexpression.split(":", 1)
            if len(parts) == 2:  # port attribute
                port_id, attr_name = parts
                m = re.search(r"[^a-zA-Z0-9_.-]", port_id)
                if m:
                    p = m.start()
                    raise UnexpectedCharacter(port_id[p], p + pos + 2)
                m = re.search(r"[^a-zA-Z0-9_-]", attr_name)
                if m:
                    p = m.start()
                    raise UnexpectedCharacter(attr_name[p], p + pos + len(port_id) + 2)

                if prefix == "$":
                    return PortAttr(port_id, prefix, role, attr_name)
                else:
                    raise UnexpectedCharacter(prefix, pos)
            else:
                port_id = sub_sexpression
                m = re.search(r"[^a-zA-Z0-9_.-]", port_id)
                if m:
                    p = m.start()
                    raise UnexpectedCharacter(sub_sexpression[p], p + pos + 2)

                if prefix == "$":
                    return PortValue(port_id, prefix, role)
                elif prefix == "@":
                    return PortRef(port_id, prefix, role)
                else:
                    raise UnexpectedCharacter(prefix, pos)
        else:
            if prefix == "$":
                return SelfPortValue(self_port_id, prefix, role)
            elif prefix == "@":
                return SelfPortRef(self_port_id, prefix, role)
            else:
                raise UnexpectedCharacter(prefix, pos)


class PortValue(PortExpression):
    def __str__(self) -> str:
        return f"{self.prefix}{self.port_id}"

    def _get_deps(self) -> set[str]:
        return {f"${self.port_id}"}

    def _get_value(self, context: EvalContext) -> NullablePortValue:
        return context.port_values.get(self.port_id)

    async def _eval(self, context: EvalContext) -> EvalResult:
        port = self.get_port()
        if not port:
            raise UnknownPortId(self.port_id)

        if not port.is_enabled():
            raise DisabledPort(self.port_id)

        value = self._get_value(context)
        if value is None:
            raise PortValueUnavailable(self.port_id)

        return value


class SelfPortValue(PortValue):
    def __str__(self) -> str:
        return self.prefix


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


class PortAttr(PortExpression):
    def __str__(self) -> str:
        return f"{self.prefix}{self.port_id}:{self.attr_name}"

    def _get_deps(self) -> set[str]:
        return {f"${self.port_id}:"}

    async def _eval(self, context: EvalContext) -> EvalResult:
        port = self.get_port()
        if not port:
            raise UnknownPortId(self.port_id)

        value = context.port_attrs.get(self.port_id, {}).get(self.attr_name)
        if value is None:
            raise PortAttrUnavailable(self.port_id, self.attr_name or "")

        return value
