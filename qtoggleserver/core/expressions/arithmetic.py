from .base import EvalContext, EvalResult
from .exceptions import ExpressionArithmeticError
from .functions import Function, function


@function("ADD")
class AddFunction(Function):
    MIN_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        return sum(await self.eval_args(context))


@function("SUB")
class SubFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        eval_args = await self.eval_args(context)
        return eval_args[0] - eval_args[1]


@function("MUL")
class MulFunction(Function):
    MIN_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        r = 1
        for e in await self.eval_args(context):
            r *= e

        return r


@function("DIV")
class DivFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        eval_args = await self.eval_args(context)

        if eval_args[1]:
            return eval_args[0] / eval_args[1]
        else:
            raise ExpressionArithmeticError


@function("MOD")
class ModFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        eval_args = await self.eval_args(context)

        if eval_args[1]:
            return eval_args[0] % eval_args[1]
        else:
            raise ExpressionArithmeticError


@function("POW")
class PowFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        eval_args = await self.eval_args(context)

        return eval_args[0] ** eval_args[1]
