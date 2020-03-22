
from qtoggleserver.core.typing import PortValue as CorePortValue

from .functions import function, Function


@function('AND')
class AndFunction(Function):
    MIN_ARGS = 2

    def eval(self) -> CorePortValue:
        r = True
        for e in self.eval_args():
            r = r and bool(e)

        return int(r)


@function('OR')
class OrFunction(Function):
    MIN_ARGS = 2

    def eval(self) -> CorePortValue:
        r = False
        for e in self.eval_args():
            r = r or bool(e)

        return int(r)


@function('NOT')
class NotFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    def eval(self) -> CorePortValue:
        return int(not bool(self.eval_args()[0]))


@function('XOR')
class XOrFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        e1 = bool(eval_args[0])
        e2 = bool(eval_args[1])

        return int(e1 and not e2 or e2 and not e1)
