from .base import EvalContext, EvalResult
from .functions import Function, function


@function("AND")
class AndFunction(Function):
    MIN_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        for arg in self.args:
            if not await arg.eval(context):
                return 0

        return 1


@function("OR")
class OrFunction(Function):
    MIN_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        for arg in self.args:
            if await arg.eval(context):
                return 1

        return 0


@function("NOT")
class NotFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    async def _eval(self, context: EvalContext) -> EvalResult:
        return int(not bool((await self.eval_args(context))[0]))


@function("XOR")
class XOrFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        eval_args = await self.eval_args(context)

        e1 = bool(eval_args[0])
        e2 = bool(eval_args[1])

        return int(e1 and not e2 or e2 and not e1)
