from .base import DEP_ASAP, DEP_SECOND, EvalContext, EvalResult
from .functions import Function, function


@function("TIME")
class TimeFunction(Function):
    MIN_ARGS = MAX_ARGS = 0
    DEPS = {DEP_SECOND}
    TRANSFORM_OK = False

    async def _eval(self, context: EvalContext) -> EvalResult:
        return context.timestamp


@function("TIMEMS")
class TimeMSFunction(Function):
    MIN_ARGS = MAX_ARGS = 0
    DEPS = {DEP_ASAP}
    TRANSFORM_OK = False

    async def _eval(self, context: EvalContext) -> EvalResult:
        return context.now_ms
