
from .functions import function, Function


@function('ABS')
class AbsFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    def eval(self) -> float:
        return abs(self.eval_args()[0])


@function('SGN')
class SgnFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    def eval(self) -> float:
        e = int(self.eval_args()[0])
        if e > 0:
            return 1

        elif e < 0:
            return -1

        else:
            return 0
