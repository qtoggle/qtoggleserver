from .base import EvalContext, EvalResult
from .functions import Function, function


@function("MIN")
class MinFunction(Function):
    MIN_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        eval_args = await self.eval_args(context)

        m = eval_args[0]
        for e in eval_args[1:]:
            if e < m:
                m = e

        return m


@function("MAX")
class MaxFunction(Function):
    MIN_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        eval_args = await self.eval_args(context)

        m = eval_args[0]
        for e in eval_args[1:]:
            if e > m:
                m = e

        return m


@function("AVG")
class AvgFunction(Function):
    MIN_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        eval_args = await self.eval_args(context)

        return sum(eval_args) / len(eval_args)
