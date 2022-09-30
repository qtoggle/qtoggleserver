import math

from .base import EvalContext, EvalResult
from .functions import Function, function


@function('FLOOR')
class FloorFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    async def _eval(self, context: EvalContext) -> EvalResult:
        eval_args = await self.eval_args(context)

        return int(math.floor(eval_args[0]))


@function('CEIL')
class CeilFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    async def _eval(self, context: EvalContext) -> EvalResult:
        eval_args = await self.eval_args(context)

        return int(math.ceil(eval_args[0]))


@function('ROUND')
class RoundFunction(Function):
    MIN_ARGS = 1
    MAX_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        eval_args = await self.eval_args(context)

        v = eval_args[0]
        d = 0
        if len(eval_args) == 2:
            d = eval_args[1]

        return round(v, int(d))
