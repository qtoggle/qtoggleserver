
from .base import Evaluated
from .functions import function, Function


@function('IF')
class IfFunction(Function):
    MIN_ARGS = MAX_ARGS = 3

    async def eval(self) -> Evaluated:
        eval_args = await self.eval_args()

        if eval_args[0]:
            return eval_args[1]

        else:
            return eval_args[2]


@function('EQ')
class EqFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def eval(self) -> Evaluated:
        eval_args = await self.eval_args()

        return int(eval_args[0] == eval_args[1])


@function('GT')
class GTFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def eval(self) -> Evaluated:
        eval_args = await self.eval_args()

        return int(eval_args[0] > eval_args[1])


@function('GTE')
class GTEFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def eval(self) -> Evaluated:
        eval_args = await self.eval_args()

        return int(eval_args[0] >= eval_args[1])


@function('LT')
class LTFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def eval(self) -> Evaluated:
        eval_args = await self.eval_args()

        return int(eval_args[0] < eval_args[1])


@function('LTE')
class LTEFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def eval(self) -> Evaluated:
        eval_args = await self.eval_args()

        return int(eval_args[0] <= eval_args[1])
