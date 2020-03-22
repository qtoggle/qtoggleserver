
from typing import Optional

from qtoggleserver.core.typing import PortValue as CorePortValue

from .functions import function, Function


@function('ACC')
class AccFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: Optional[float] = None

    def eval(self) -> CorePortValue:
        value = self.args[0].eval()
        accumulator = self.args[1].eval()
        result = accumulator

        if self._last_value is not None:
            result += value - self._last_value

        self._last_value = value

        return result


@function('HYST')
class HystFunction(Function):
    MIN_ARGS = MAX_ARGS = 3

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_result: int = 0

    def eval(self) -> CorePortValue:
        value = self.args[0].eval()
        threshold1 = self.args[1].eval()
        threshold2 = self.args[2].eval()

        self._last_result = int((self._last_result == 0 and value > threshold2) or
                                (self._last_result != 0 and value >= threshold1))

        return self._last_result
