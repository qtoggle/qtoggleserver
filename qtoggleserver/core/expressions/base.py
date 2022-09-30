from __future__ import annotations

import abc

from typing import Optional, Union

from .exceptions import EvalSkipped, ExpressionEvalError


class Expression(metaclass=abc.ABCMeta):
    def __init__(self, role: int) -> None:
        self.role: int = role
        self._asap_eval_paused_until_ms: int = 0
        self._cached_deps: Optional[set[str]] = None

    def pause_asap_eval(self, pause_until_ms: int = 0) -> None:
        self._asap_eval_paused_until_ms = pause_until_ms or int(1e13)

    def is_asap_eval_paused(self, now_ms: int) -> bool:
        return now_ms < self._asap_eval_paused_until_ms

    async def eval(self, context: EvalContext) -> EvalResult:
        self._asap_eval_paused_until_ms = 0
        try:
            return await self._eval(context)
        except EvalSkipped:
            raise
        except ExpressionEvalError:
            # Pause expression evaluation for 1 second, as it's very unlikely that a problematic expression become
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
    def parse(self_port_id: Optional[str], sexpression: str, role: int, pos: int) -> Expression:
        raise NotImplementedError()


class EvalContext:
    def __init__(
        self,
        port_values: dict[str, NullablePortValue],
        now_ms: int
    ) -> None:
        self.port_values: dict[str, NullablePortValue] = port_values
        self.now_ms: int = now_ms

    @property
    def timestamp(self) -> int:
        return int(self.now_ms / 1000)


# This needs to be imported here to avoid circular import issues
from qtoggleserver.core import ports as core_ports  # noqa: E402
from qtoggleserver.core.typing import NullablePortValue  # noqa: E402


EvalResult = Union[bool, int, float, core_ports.BasePort]
