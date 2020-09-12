
import math

from .functions import function, Function


@function('FLOOR')
class FloorFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    def eval(self) -> float:
        eval_args = self.eval_args()

        return int(math.floor(eval_args[0]))


@function('CEIL')
class CeilFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    def eval(self) -> float:
        eval_args = self.eval_args()

        return int(math.ceil(eval_args[0]))


@function('ROUND')
class RoundFunction(Function):
    MIN_ARGS = 1
    MAX_ARGS = 2

    def eval(self) -> float:
        eval_args = self.eval_args()

        v = eval_args[0]
        d = 0
        if len(eval_args) == 2:
            d = eval_args[1]

        return round(v, int(d))
