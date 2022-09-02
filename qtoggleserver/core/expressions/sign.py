
from .base import Evaluated, EvalContext
from .functions import function, Function


@function('ABS')
class AbsFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    async def eval(self, context: EvalContext) -> Evaluated:
        return abs((await self.eval_args(context))[0])


@function('SGN')
class SgnFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    async def eval(self, context: EvalContext) -> Evaluated:
        e = int((await self.eval_args(context))[0])
        if e > 0:
            return 1

        elif e < 0:
            return -1

        else:
            return 0
