
import time

from typing import List, Optional, Set, Tuple

from .exceptions import EvalSkipped
from .functions import function, Function


@function('DELAY')
class DelayFunction(Function):
    MIN_ARGS = MAX_ARGS = 2
    HISTORY_SIZE = 1024

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._queue: List[Tuple[int, float]] = []
        self._last_value: Optional[float] = None
        self._current_value: Optional[float] = None

    def get_deps(self) -> Set[str]:
        return {'time_ms'}

    def eval(self) -> float:
        time_ms = int(time.time() * 1000)

        value = self.args[0].eval()
        delay = self.args[1].eval()

        if self._current_value is None:
            self._current_value = value

        # Detect value transitions and build history
        if value != self._last_value:
            self._last_value = value

            # Drop elements from queue if history size reached
            while len(self._queue) >= self.HISTORY_SIZE:
                self._queue.pop(0)

            self._queue.append((time_ms, value))

        # Process history
        while self._queue and (time_ms - self._queue[0][0]) >= delay:
            self._current_value = self._queue.pop(0)[1]

        return self._current_value


@function('SAMPLE')
class SampleFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: Optional[float] = None
        self._last_duration: float = 0
        self._last_time_ms: int = 0

    def get_deps(self) -> Set[str]:
        # Function depends on milliseconds only if it's time to reevaluate value
        if time.time() * 1000 - self._last_time_ms >= self._last_duration:
            return {'time_ms'}

        return super().get_deps()

    def eval(self) -> float:
        time_ms = int(time.time() * 1000)
        if time_ms - self._last_time_ms < self._last_duration:
            return self._last_value

        self._last_value = self.args[0].eval()
        self._last_duration = self.args[1].eval()
        self._last_time_ms = time_ms

        return self._last_value


@function('FREEZE')
class FreezeFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: Optional[float] = None
        self._last_duration: float = 0
        self._last_time_ms: int = 0

    def get_deps(self) -> Set[str]:
        # Function depends on milliseconds only when timer is active
        if self._last_time_ms > 0:
            return {'time_ms'}

        return super().get_deps()

    def eval(self) -> float:
        time_ms = int(time.time() * 1000)

        if self._last_time_ms == 0:  # Idle
            value = self.args[0].eval()
            if value != self._last_value:  # Value change detected, start timer
                self._last_time_ms = time_ms
                self._last_duration = self.args[1].eval()
                self._last_value = value

        else:  # Timer active
            if time_ms - self._last_time_ms > self._last_duration:  # Timer expired
                self._last_time_ms = 0
                return self.eval()  # Call eval() again, now that _last_time_ms is 0

        return self._last_value


@function('HELD')
class HeldFunction(Function):
    MIN_ARGS = MAX_ARGS = 3

    STATE_OFF = 0
    STATE_WAITING = 1
    STATE_ON = 2

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._time_ms: Optional[int] = None
        self._state = self.STATE_OFF

    def get_deps(self) -> Set[str]:
        if self._state == self.STATE_WAITING:
            return {'time_ms'}

        else:
            return super().get_deps()

    def eval(self) -> float:
        value = self.args[0].eval()
        fixed_value = self.args[1].eval()
        duration = self.args[2].eval()

        if value == fixed_value:
            time_ms = int(time.time() * 1000)

            if self._state == self.STATE_OFF:
                self._time_ms = time_ms
                self._state = self.STATE_WAITING

            elif self._state == self.STATE_WAITING:
                delta = time_ms - self._time_ms
                if delta >= duration:
                    self._state = self.STATE_ON

        else:
            self._state = self.STATE_OFF

        return self._state == self.STATE_ON


@function('DERIV')
class DerivFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: Optional[float] = None
        self._last_time: float = 0

    def get_deps(self) -> Set[str]:
        return {'time_ms'}

    def eval(self) -> float:
        value = self.args[0].eval()
        sampling_interval = self.args[1].eval() / 1000
        result = 0
        now = time.time()

        if self._last_value is not None:
            delta = now - self._last_time
            if delta < sampling_interval:
                raise EvalSkipped()

            result = (value - self._last_value) / delta

        self._last_value = value
        self._last_time = now

        return result


@function('INTEG')
class IntegFunction(Function):
    MIN_ARGS = MAX_ARGS = 3

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: Optional[float] = None
        self._last_time: float = 0

    def get_deps(self) -> Set[str]:
        return {'time_ms'}

    def eval(self) -> float:
        value = self.args[0].eval()
        accumulator = self.args[1].eval()
        sampling_interval = self.args[2].eval() / 1000
        result = accumulator
        now = time.time()

        if self._last_value is not None:
            delta = now - self._last_time
            if delta < sampling_interval:
                raise EvalSkipped()

            result += (value + self._last_value) * delta / 2

        self._last_value = value
        self._last_time = now

        return result


@function('FMAVG')
class FMAvgFunction(Function):
    MIN_ARGS = MAX_ARGS = 3
    QUEUE_SIZE = 1024

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._queue: List[float] = []
        self._last_time: float = 0

    def get_deps(self) -> Set[str]:
        return {'time_ms'}

    def eval(self) -> float:
        value = self.args[0].eval()
        width = min(self.args[1].eval(), self.QUEUE_SIZE)
        sampling_interval = self.args[2].eval() / 1000
        now = time.time()

        if self._last_time > 0:
            delta = now - self._last_time
            if delta < sampling_interval:
                raise EvalSkipped()

        # Make place for the new element
        while len(self._queue) > width:
            self._queue.pop(0)

        self._queue.append(value)
        self._last_time = now

        return sum(self._queue) / len(self._queue)


@function('FMEDIAN')
class FMedianFunction(Function):
    MIN_ARGS = MAX_ARGS = 3
    QUEUE_SIZE = 1024

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._queue: List[float] = []
        self._last_time: float = 0

    def get_deps(self) -> Set[str]:
        return {'time_ms'}

    def eval(self) -> float:
        value = self.args[0].eval()
        width = min(self.args[1].eval(), self.QUEUE_SIZE)
        sampling_interval = self.args[2].eval() / 1000
        now = time.time()

        if self._last_time > 0:
            delta = now - self._last_time
            if delta < sampling_interval:
                raise EvalSkipped()

        # Make place for the new element
        while len(self._queue) > width:
            self._queue.pop(0)

        self._queue.append(value)
        self._last_time = now

        sorted_queue = list(sorted(self._queue))

        return sorted_queue[len(sorted_queue) // 2]
