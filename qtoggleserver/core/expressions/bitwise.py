
from .base import Evaluated
from .functions import function, Function


@function('BITAND')
class BitAndFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def eval(self) -> Evaluated:
        r = -1
        for e in await self.eval_args():
            r &= int(e)

        return r


@function('BITOR')
class BitOrFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def eval(self) -> Evaluated:
        r = 0
        for e in await self.eval_args():
            r |= int(e)

        return r


@function('BITNOT')
class BitNotFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    async def eval(self) -> Evaluated:
        return ~int((await self.eval_args())[0])


@function('BITXOR')
class BitXOrFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def eval(self) -> Evaluated:
        eval_args = await self.eval_args()

        return int(eval_args[0]) ^ int(eval_args[1])


@function('SHL')
class SHLFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def eval(self) -> Evaluated:
        eval_args = await self.eval_args()

        return int(eval_args[0]) << int(eval_args[1])


@function('SHR')
class SHRFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def eval(self) -> Evaluated:
        eval_args = await self.eval_args()

        return int(eval_args[0]) >> int(eval_args[1])
