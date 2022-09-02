
import time

from .base import EvalResult, EvalContext
from .functions import function, Function


@function('TIME')
class TimeFunction(Function):
    MIN_ARGS = MAX_ARGS = 0
    DEPS = {'second'}

    async def _eval(self, context: EvalContext) -> EvalResult:
        return context.timestamp


@function('TIMEMS')
class TimeMSFunction(Function):
    MIN_ARGS = MAX_ARGS = 0
    DEPS = {'asap'}

    async def _eval(self, context: EvalContext) -> EvalResult:
        return context.now_ms
