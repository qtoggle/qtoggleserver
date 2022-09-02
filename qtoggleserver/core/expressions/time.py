
import time

from .base import EvalResult, EvalContext
from .functions import function, Function


@function('TIME')
class TimeFunction(Function):
    MIN_ARGS = MAX_ARGS = 0
    DEPS = ['second']

    async def _eval(self, context: EvalContext) -> EvalResult:
        return int(time.time())


@function('TIMEMS')
class TimeMSFunction(Function):
    MIN_ARGS = MAX_ARGS = 0
    DEPS = ['millisecond']

    async def _eval(self, context: EvalContext) -> EvalResult:
        return int(time.time() * 1000)
