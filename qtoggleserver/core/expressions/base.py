
from __future__ import annotations

import abc

from typing import Optional, Set, Union


class Expression(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def eval(self) -> Evaluated:
        raise NotImplementedError()

    def get_deps(self) -> Set[str]:
        # Special deps:
        #  * 'second' - used to indicate dependency on system time (seconds)
        #  * 'millisecond' - used to indicate dependency on system time (milliseconds)

        return set()

    @staticmethod
    @abc.abstractmethod
    def parse(self_port_id: Optional[str], sexpression: str, pos: int) -> Expression:
        raise NotImplementedError()


# This needs to be imported here to avoid circular import issues
from qtoggleserver.core import ports as core_ports  # noqa: E402

Evaluated = Union[bool, int, float, core_ports.BasePort]
