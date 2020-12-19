
import time

from typing import Set

from .functions import function, Function


@function('TIME')
class TimeFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'second'}

    def eval(self) -> float:
        return int(time.time())


@function('TIMEMS')
class TimeMSFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'millisecond'}

    def eval(self) -> float:
        return int(time.time() * 1000)
