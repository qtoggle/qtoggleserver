from .base import EvalContext, EvalResult
from .functions import Function, function


@function("ABS")
class AbsFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    async def _eval(self, context: EvalContext) -> EvalResult:
        return abs((await self.eval_args(context))[0])


@function("SGN")
class SgnFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    async def _eval(self, context: EvalContext) -> EvalResult:
        e = int((await self.eval_args(context))[0])
        if e > 0:
            return 1
        elif e < 0:
            return -1
        else:
            return 0
