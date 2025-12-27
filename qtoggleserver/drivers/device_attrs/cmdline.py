import logging

from qtoggleserver.core.device import attrs as core_device_attrs
from qtoggleserver.core.device.exceptions import DeviceAttributeException
from qtoggleserver.core.typing import Attribute
from qtoggleserver.utils.cmd import run_get_cmd, run_set_cmd


logger = logging.getLogger(__name__)


class CmdLineAttrDef(core_device_attrs.AttrDefDriver):
    def __init__(
        self,
        display_name: str,
        description: str,
        type: str,
        get_cmd: str,
        set_cmd: str | None = None,
        cache_lifetime: int = 0,
    ) -> None:
        if type not in ("boolean", "number", "string"):
            raise ValueError(f"Invalid attribute type {type}")

        self._display_name: str = display_name
        self._description: str = description
        self._type: str = type
        self._get_cmd: str = get_cmd
        self._set_cmd: str | None = set_cmd
        self._cache_lifetime: int = cache_lifetime

        super().__init__()

    def get_display_name(self) -> str:
        return self._display_name

    def get_description(self) -> str:
        return self._description

    def get_type(self) -> str:
        return self._type

    def is_modifiable(self) -> bool:
        return self._set_cmd is not None

    def get_cache_lifetime(self) -> int:
        return self._cache_lifetime

    async def get_value(self) -> Attribute:
        result = run_get_cmd(
            self._get_cmd,
            cmd_name="attrdef getter",
            required_fields=["value"],
            exc_class=DeviceAttributeException,
        )
        value = result["value"]
        if self._type == "boolean":
            return value.lower() == "true"
        elif self._type == "number":
            try:
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    logger.error('got unexpected value "%s"', value)
                    return None
        else:
            return value

    async def set_value(self, value: Attribute) -> None:
        if self._type == "boolean":
            value_str = ["false", "true"][value]
        else:
            value_str = str(value)
        run_set_cmd(self._set_cmd, cmd_name="attrdef setter", exc_class=DeviceAttributeException, value=value_str)
