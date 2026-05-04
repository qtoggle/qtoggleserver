from __future__ import annotations

import abc
import re

from .base import EvalContext, EvalResult, Expression, Role
from .exceptions import DeviceAttrUnavailable, MissingAttrPrefix, TransformNotSupported, UnexpectedCharacter


_TRANSFORM_ROLES = (Role.TRANSFORM_READ, Role.TRANSFORM_WRITE)


class DeviceExpression(Expression, metaclass=abc.ABCMeta):
    def __init__(self, device_name: str | None, prefix: str, role: Role, attr_name: str | None = None) -> None:
        super().__init__(role)

        self.device_name: str | None = device_name
        self.attr_name: str | None = attr_name
        self.prefix: str = prefix

    @staticmethod
    def parse(self_port_id: str | None, sexpression: str, role: Role, pos: int) -> Expression:
        stripped = sexpression.lstrip()
        pos += len(sexpression) - len(stripped)
        sexpression = stripped.rstrip()

        prefix = sexpression[0]
        sub_sexpression = sexpression[1:]

        if prefix == "#":
            if role in _TRANSFORM_ROLES:
                raise TransformNotSupported(sexpression, pos)
            parts = sub_sexpression.split(":", 1)
            if len(parts) != 2:
                raise MissingAttrPrefix(pos + len(sub_sexpression) + 1)

            device_name, attr_name = parts
            if device_name:
                m = re.search(r"[^a-zA-Z0-9_-]", device_name)
                if m:
                    p = m.start()
                    raise UnexpectedCharacter(device_name[p], p + pos + 3)

                return SlaveDeviceAttr(device_name, prefix, role, attr_name)
            else:
                return MainDeviceAttr(prefix, role, attr_name)
        else:
            raise UnexpectedCharacter(prefix, pos)


class DeviceAttr(DeviceExpression):
    def __str__(self) -> str:
        return f"{self.prefix}{self.device_name or ''}:{self.attr_name}"

    def _get_deps(self) -> set[str]:
        return {f"#{self.device_name or ''}:"}

    async def _eval(self, context: EvalContext) -> EvalResult:
        key = f"{self.device_name}:{self.attr_name or ''}" if self.device_name else self.attr_name
        value = context.device_attrs.get(key)
        if value is None:
            raise DeviceAttrUnavailable(self.device_name or "", self.attr_name or "")

        return value


class SlaveDeviceAttr(DeviceAttr):
    pass


class MainDeviceAttr(DeviceAttr):
    def __init__(self, prefix: str, role: Role, attr_name: str | None = None) -> None:
        super().__init__(None, prefix, role, attr_name)
