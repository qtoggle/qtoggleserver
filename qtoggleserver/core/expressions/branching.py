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


@function("LUT")
class LUTFunction(Function):
    MIN_ARGS = 5

    async def _eval(self, context: EvalContext) -> EvalResult:
        args = await self.eval_args(context)
        length = (len(args) - 1) // 2
        x = args[0]
        points = [(args[2 * i + 1], args[2 * i + 2]) for i in range(length)]
        points.sort(key=lambda p: p[0])

        if x < points[0][0]:
            return points[0][1]

        for i in range(length - 1):
            p1 = points[i]
            p2 = points[i + 1]

            if x > p2[0]:
                continue

            if x - p1[0] < p2[0] - x:  # closer to p1 than to p2
                return p1[1]
            else:
                return p2[1]

        return points[length - 1][1]


@function("LUTLI")
class LUTLIFunction(Function):
    MIN_ARGS = 5

    async def _eval(self, context: EvalContext) -> EvalResult:
        args = await self.eval_args(context)
        length = (len(args) - 1) // 2
        x = args[0]
        points = [(args[2 * i + 1], args[2 * i + 2]) for i in range(length)]
        points.sort(key=lambda p: p[0])

        if x < points[0][0]:
            return points[0][1]

        for i in range(length - 1):
            p1 = points[i]
            p2 = points[i + 1]

            if x > p2[0]:
                continue

            if p1[0] == p2[0]:
                return p1[1]

            return p1[1] + (p2[1] - p1[1]) * (x - p1[0]) / (p2[0] - p1[0])

        return points[length - 1][1]
