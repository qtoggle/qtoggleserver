
from __future__ import annotations

import abc

from typing import Dict, Optional, Set, Union

from .exceptions import EvalSkipped


class Expression(metaclass=abc.ABCMeta):
    def __init__(self) -> None:
        self._eval_paused_until_ms: int = 0

    @abc.abstractmethod
    async def eval(self, context: EvalContext) -> Evaluated:
        raise NotImplementedError()

    def pause_eval(self, pause_until_ms: int = 0) -> None:
        self._eval_paused_until_ms = pause_until_ms
        raise EvalSkipped()

    def is_eval_paused(self, now_ms: int) -> bool:
        return self._eval_paused_until_ms > now_ms

    def get_deps(self) -> Set[str]:
        # Special deps:
        #  * 'second' - used to indicate dependency on system time (seconds)
        #  * 'millisecond' - used to indicate dependency on system time (milliseconds)

        return set()

    @staticmethod
    @abc.abstractmethod
    def parse(self_port_id: Optional[str], sexpression: str, pos: int) -> Expression:
        raise NotImplementedError()


class EvalContext:
    def __init__(
        self,
        port_values: Dict[str, NullablePortValue],
        now_ms: int
    ) -> None:
        self.port_values: Dict[str, NullablePortValue] = port_values
        self.now_ms: int = now_ms
        self.now: float = now_ms / 1000


# This needs to be imported here to avoid circular import issues
from qtoggleserver.core import ports as core_ports  # noqa: E402
from qtoggleserver.core.typing import NullablePortValue  # noqa: E402

Evaluated = Union[bool, int, float, core_ports.BasePort]
