import abc
import time

from qtoggleserver.core.typing import Attribute, AttributeDefinition


class BaseDriver(metaclass=abc.ABCMeta):
    NAME: str = ""
    DISPLAY_NAME: str | None = None
    DESCRIPTION: str | None = None
    TYPE: str = "boolean"
    MODIFIABLE: bool = False
    UNIT: str | None = None
    MIN: float | None = None
    MAX: float | None = None
    INTEGER: bool = False
    STEP: float | None = None
    CHOICES: list[dict] | None = None
    PATTERN: str | None = None
    RECONNECT: bool = False

    PERSISTED: bool = False
    CACHE_LIFETIME: int = 0

    def __init__(self) -> None:
        self._cached_value: Attribute | None = None
        self._cached_timestamp: float = 0

    def get_name(self) -> str:
        return self.NAME

    def get_display_name(self) -> str | None:
        return self.DISPLAY_NAME

    def get_description(self) -> str | None:
        return self.DESCRIPTION

    def get_type(self) -> str:
        return self.TYPE

    def is_modifiable(self) -> bool:
        return self.MODIFIABLE

    def get_unit(self) -> str | None:
        return self.UNIT

    def get_min(self) -> float | None:
        return self.MIN

    def get_max(self) -> float | None:
        return self.MAX

    def is_integer(self) -> bool:
        return self.INTEGER

    def get_step(self) -> float | None:
        return self.STEP

    def get_choices(self) -> list[dict] | None:
        return self.CHOICES

    def get_pattern(self) -> str | None:
        return self.PATTERN

    def needs_reconnect(self) -> bool:
        return self.RECONNECT

    def is_enabled(self) -> bool:
        return True

    def is_persisted(self) -> bool:
        return self.PERSISTED

    @abc.abstractmethod
    async def get_value(self) -> Attribute:
        pass

    async def set_value(self, value: Attribute) -> None:
        # Not an abstract method as we don't implement this method for non-modifiable attributes
        pass

    async def _getter(self) -> Attribute:
        if (
            self.CACHE_LIFETIME > 0
            and self._cached_value is not None
            and time.time() - self._cached_timestamp < self.CACHE_LIFETIME
        ):
            return self._cached_value

        self._cached_value = await self.get_value()
        self._cached_timestamp = time.time()

        return self._cached_value

    async def _setter(self, value: Attribute) -> None:
        self._cached_timestamp = 0
        await self.set_value(value)

    def make_attrdef(self) -> AttributeDefinition:
        return {
            "enabled": self.is_enabled,  # intentionally supplied as callabable
            "display_name": self.get_display_name(),
            "description": self.get_description(),
            "type": self.get_type(),
            "modifiable": self.is_modifiable(),
            "unit": self.get_unit(),
            "min": self.get_min(),
            "max": self.get_max(),
            "integer": self.is_integer(),
            "step": self.get_step(),
            "choices": self.get_choices(),
            "pattern": self.get_pattern(),
            "reconnect": self.needs_reconnect(),
            "getter": self._getter,
            "setter": self._setter,
        }
