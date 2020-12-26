
from .base import Evaluated
from .exceptions import ExpressionArithmeticError
from .functions import function, Function


@function('ADD')
class AddFunction(Function):
    MIN_ARGS = 2

    async def eval(self) -> Evaluated:
        return sum(await self.eval_args())


@function('SUB')
class SubFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def eval(self) -> Evaluated:
        eval_args = await self.eval_args()
        return eval_args[0] - eval_args[1]


@function('MUL')
class MulFunction(Function):
    MIN_ARGS = 2

    async def eval(self) -> Evaluated:
        r = 1
        for e in await self.eval_args():
            r *= e

        return r


@function('DIV')
class DivFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def eval(self) -> Evaluated:
        eval_args = await self.eval_args()

        if eval_args[1]:
            return eval_args[0] / eval_args[1]

        else:
            raise ExpressionArithmeticError


@function('MOD')
class ModFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def eval(self) -> Evaluated:
        eval_args = await self.eval_args()

        if eval_args[1]:
            return eval_args[0] % eval_args[1]

        else:
            raise ExpressionArithmeticError


@function('POW')
class PowFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def eval(self) -> Evaluated:
        eval_args = await self.eval_args()

        return eval_args[0] ** eval_args[1]
