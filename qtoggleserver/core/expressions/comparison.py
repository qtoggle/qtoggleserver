from .base import EvalContext, EvalResult
from .functions import Function, function


@function("IF")
class IfFunction(Function):
    MIN_ARGS = MAX_ARGS = 3

    async def _eval(self, context: EvalContext) -> EvalResult:
        condition_value = await self.args[0].eval(context)
        if condition_value:
            return await self.args[1].eval(context)
        else:
            return await self.args[2].eval(context)


@function("EQ")
class EqFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        eval_args = await self.eval_args(context)

        return int(eval_args[0] == eval_args[1])


@function("GT")
class GTFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        eval_args = await self.eval_args(context)

        return int(eval_args[0] > eval_args[1])


@function("GTE")
class GTEFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        eval_args = await self.eval_args(context)

        return int(eval_args[0] >= eval_args[1])


@function("LT")
class LTFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        eval_args = await self.eval_args(context)

        return int(eval_args[0] < eval_args[1])


@function("LTE")
class LTEFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        eval_args = await self.eval_args(context)

        return int(eval_args[0] <= eval_args[1])
