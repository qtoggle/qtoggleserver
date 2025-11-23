from .base import DEP_ASAP, DEP_SECOND, EvalContext, EvalResult
from .functions import Function, function


@function("TIME")
class TimeFunction(Function):
    MIN_ARGS = MAX_ARGS = 0
    DEPS = {DEP_SECOND}

    async def _eval(self, context: EvalContext) -> EvalResult:
        return context.timestamp


@function("TIMEMS")
class TimeMSFunction(Function):
    MIN_ARGS = MAX_ARGS = 0
    DEPS = {DEP_ASAP}

    async def _eval(self, context: EvalContext) -> EvalResult:
        return context.now_ms
