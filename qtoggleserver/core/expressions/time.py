from .base import EvalContext, EvalResult
from .functions import Function, function


@function("TIME")
class TimeFunction(Function):
    MIN_ARGS = MAX_ARGS = 0
    DEPS = {"second"}

    async def _eval(self, context: EvalContext) -> EvalResult:
        return context.timestamp


@function("TIMEMS")
class TimeMSFunction(Function):
    MIN_ARGS = MAX_ARGS = 0
    DEPS = {"asap"}

    async def _eval(self, context: EvalContext) -> EvalResult:
        return context.now_ms
