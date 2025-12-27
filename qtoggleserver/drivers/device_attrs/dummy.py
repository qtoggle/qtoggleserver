from qtoggleserver.core.device import attrs as core_device_attrs
from qtoggleserver.core.typing import Attribute


class DummyAttrDef(core_device_attrs.AttrDefDriver):
    TYPE = "string"
    MODIFIABLE = True
    PERSISTED = True

    def __init__(self, display_name: str, description: str) -> None:
        self._display_name: str = display_name
        self._description: str = description
        self._value: str | None = None

        super().__init__()

    def get_display_name(self) -> str:
        return self._display_name

    def get_description(self) -> str:
        return self._description

    async def get_value(self) -> Attribute:
        return self._value

    async def set_value(self, value: str) -> None:
        self._value = value
