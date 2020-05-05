
import time

from typing import Optional, Set

from qtoggleserver.core.typing import PortValue as CorePortValue

from .exceptions import EvalSkipped
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


@function('ACCINC')
class AccIncFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: Optional[float] = None

    def eval(self) -> CorePortValue:
        value = self.args[0].eval()
        accumulator = self.args[1].eval()
        result = accumulator

        if (self._last_value is not None) and (value > self._last_value):
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


@function('SEQUENCE')
class SequenceFunction(Function):
    MIN_ARGS = 2

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_time: float = 0

    def get_deps(self) -> Set[str]:
        return {'time_ms'}

    def eval(self) -> CorePortValue:
        now = time.time() * 1000

        if self._last_time > 0:
            self._last_time = now
            raise EvalSkipped()

        args = self.eval_args()
        num_values = len(args) // 2
        values = []
        delays = []
        total_delay = 0
        for i in range(num_values):
            values.append(args[i * 2])
            delays.append(args[i * 2 + 1])
            total_delay += args[i * 2 + 1]

        if len(delays) < len(values):
            delays.append(0)

        delta = now - self._last_time
        delta = delta % total_delay  # Work modulo total_delay, to create repeat effect
        delay_so_far = 0
        result = values[0]
        for i in range(num_values):
            delay_so_far += delays[i]
            if delay_so_far >= delta:
                result = values[i]
                break

        return result
