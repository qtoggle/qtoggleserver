from __future__ import annotations

import abc

from enum import IntEnum
from typing import TypeAlias

from qtoggleserver.core.typing import NullablePortValue

from .exceptions import ExpressionEvalException


DEP_ASAP = "asap"
DEP_SECOND = "second"
DEP_MINUTE = "minute"
DEP_HOUR = "hour"
DEP_DAY = "day"
DEP_MONTH = "month"
DEP_YEAR = "year"


class Role(IntEnum):
    """Available expression roles."""

    VALUE = 1
    TRANSFORM_READ = 2
    TRANSFORM_WRITE = 3
    FILTER = 4


class Expression(metaclass=abc.ABCMeta):
    def __init__(self, role: Role) -> None:
        self.role: Role = role
        self._asap_eval_paused_until_ms: int = 0
        self._cached_deps: set[str] | None = None

    def pause_asap_eval(self, pause_until_ms: int = 0) -> None:
        self._asap_eval_paused_until_ms = pause_until_ms or int(1e13)

    def is_asap_eval_paused(self, now_ms: int) -> bool:
        return now_ms < self._asap_eval_paused_until_ms

    async def eval(self, context: EvalContext) -> EvalResult:
        self._asap_eval_paused_until_ms = 0
        try:
            return await self._eval(context)
        except ExpressionEvalException:
            # Pause expression evaluation for 1 second, as it's very unlikely that the expression become available or
            # fixed within a second. This is a small speed optimization for expressions that depend on millisecond.
            self.pause_asap_eval(context.now_ms + 1000)
            raise

    @abc.abstractmethod
    async def _eval(self, context: EvalContext) -> EvalResult:
        raise NotImplementedError()

    def get_deps(self) -> set[str]:
        if self._cached_deps is None:
            self._cached_deps = self._get_deps()
        return self._cached_deps

    def _get_deps(self) -> set[str]:
        # Special deps:
        #  * 'second' - used to indicate dependency on system time (seconds)
        #  * 'asap' - used to indicate that evaluation should be done as soon as possible
        return set()

    @staticmethod
    @abc.abstractmethod
    def parse(self_port_id: str | None, sexpression: str, role: Role, pos: int) -> Expression:
        raise NotImplementedError()


class EvalContext:
    def __init__(self, port_values: dict[str, NullablePortValue], now_ms: int) -> None:
        self.port_values: dict[str, NullablePortValue] = port_values
        self.now_ms: int = now_ms

    @property
    def timestamp(self) -> int:
        return int(self.now_ms / 1000)

    def __str__(self) -> str:
        return f"EvalContext(now_ms={self.now_ms}, port_values={self.port_values})"


EvalResult: TypeAlias = bool | int | float | str
