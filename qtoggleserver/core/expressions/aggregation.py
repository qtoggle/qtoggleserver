
from typing import Any, Dict

from .base import Evaluated
from .functions import function, Function


@function('MIN')
class MinFunction(Function):
    MIN_ARGS = 2

    async def eval(self, context: Dict[str, Any]) -> Evaluated:
        eval_args = await self.eval_args(context)

        m = eval_args[0]
        for e in eval_args[1:]:
            if e < m:
                m = e

        return m


@function('MAX')
class MaxFunction(Function):
    MIN_ARGS = 2

    async def eval(self, context: Dict[str, Any]) -> Evaluated:
        eval_args = await self.eval_args(context)

        m = eval_args[0]
        for e in eval_args[1:]:
            if e > m:
                m = e

        return m


@function('AVG')
class AvgFunction(Function):
    MIN_ARGS = 2

    async def eval(self, context: Dict[str, Any]) -> Evaluated:
        eval_args = await self.eval_args(context)

        return sum(eval_args) / len(eval_args)
