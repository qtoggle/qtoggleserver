
import time

from typing import List, Optional, Set, Tuple

from . import TIME_JUMP_THRESHOLD

from .base import EvalResult, EvalContext
from .exceptions import EvalSkipped
from .functions import function, Function


@function('DELAY')
class DelayFunction(Function):
    MIN_ARGS = MAX_ARGS = 2
    DEPS = {'asap'}
    HISTORY_SIZE = 1024

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._queue: List[Tuple[int, float]] = []
        self._last_value: Optional[float] = None
        self._current_value: Optional[float] = None

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, delay = await self.eval_args(context)

        if self._current_value is None:
            self._current_value = value

        # Detect value transitions and build history
        if value != self._last_value:
            self._last_value = value

            # Drop elements from queue if history size reached
            while len(self._queue) >= self.HISTORY_SIZE:
                self._queue.pop(0)

            self._queue.append((context.now_ms, value))

        # Process history
        while self._queue and (context.now_ms - self._queue[0][0]) >= delay:
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
            return {'asap'}

        return super().get_deps()

    async def _eval(self, context: EvalContext) -> EvalResult:
        if context.now_ms - self._last_time_ms < self._last_duration:
            return self._last_value

        self._last_value, self._last_duration = await self.eval_args(context)
        self._last_time_ms = context.now_ms

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
            return {'asap'}

        return super().get_deps()

    async def _eval(self, context: EvalContext) -> EvalResult:
        if self._last_time_ms == 0:  # Idle
            value = await self.args[0].eval(context)
            if value != self._last_value:  # Value change detected, start timer
                self._last_time_ms = context.now_ms
                self._last_duration = await self.args[1].eval(context)
                self._last_value = value

        else:  # Timer active
            if context.now_ms - self._last_time_ms > self._last_duration:  # Timer expired
                self._last_time_ms = 0
                return await self.eval(context)  # Call eval() again, now that _last_time_ms is 0

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
            return {'asap'}

        return super().get_deps()

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, fixed_value, duration = await self.eval_args(context)

        if value == fixed_value:
            if self._state == self.STATE_OFF:
                self._time_ms = context.now_ms
                self._state = self.STATE_WAITING
            elif self._state == self.STATE_WAITING:
                delta = context.now_ms - self._time_ms
                if delta >= duration:
                    self._state = self.STATE_ON
        else:
            self._state = self.STATE_OFF

        return self._state == self.STATE_ON


@function('DERIV')
class DerivFunction(Function):
    MIN_ARGS = MAX_ARGS = 2
    DEPS = {'asap'}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: Optional[float] = None
        self._last_time_ms: int = 0

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, sampling_interval = await self.eval_args(context)
        result = 0

        if self._last_value is not None:
            delta = context.now_ms - self._last_time_ms
            if delta < sampling_interval:
                raise EvalSkipped()

            if delta > TIME_JUMP_THRESHOLD:
                self._last_value = value
                self._last_time_ms = context.now_ms
                raise EvalSkipped()

            result = (value - self._last_value) / delta / 1000

        self._last_value = value
        self._last_time_ms = context.now_ms

        return result


@function('INTEG')
class IntegFunction(Function):
    MIN_ARGS = MAX_ARGS = 3
    DEPS = {'asap'}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: Optional[float] = None
        self._last_time_ms: int = 0

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, accumulator, sampling_interval = await self.eval_args(context)
        result = accumulator

        if self._last_value is not None:
            delta = context.now_ms - self._last_time_ms
            if delta < sampling_interval:
                self.pause_asap_eval(self._last_time_ms + sampling_interval)
                raise EvalSkipped()

            if delta > TIME_JUMP_THRESHOLD:
                self._last_value = value
                self._last_time_ms = context.now_ms
                raise EvalSkipped()

            result += (value + self._last_value) * delta / 2000

        self._last_value = value
        self._last_time_ms = context.now_ms

        return result


@function('FMAVG')
class FMAvgFunction(Function):
    MIN_ARGS = MAX_ARGS = 3
    DEPS = {'asap'}
    QUEUE_SIZE = 1024

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._queue: List[float] = []
        self._last_time_ms: int = 0

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, width, sampling_interval = await self.eval_args(context)
        width = min(width, self.QUEUE_SIZE)

        if self._last_time_ms > 0:
            delta = context.now_ms - self._last_time_ms
            if delta < sampling_interval:
                raise EvalSkipped()

            if delta > TIME_JUMP_THRESHOLD:
                self._last_time_ms = context.now_ms
                raise EvalSkipped()

        # Make place for the new element
        while len(self._queue) >= width:
            self._queue.pop(0)

        self._queue.append(value)
        self._last_time_ms = context.now_ms

        queue = self._queue[-int(width):]

        return sum(queue) / len(queue)


@function('FMEDIAN')
class FMedianFunction(Function):
    MIN_ARGS = MAX_ARGS = 3
    DEPS = {'asap'}
    QUEUE_SIZE = 1024

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._queue: List[float] = []
        self._last_time_ms: int = 0

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, width, sampling_interval = await self.eval_args(context)
        width = min(width, self.QUEUE_SIZE)

        if self._last_time_ms > 0:
            delta = context.now_ms - self._last_time_ms
            if delta < sampling_interval:
                raise EvalSkipped()

            if delta > TIME_JUMP_THRESHOLD:
                self._last_time_ms = context.now_ms
                raise EvalSkipped()

        # Make place for the new element
        while len(self._queue) >= width:
            self._queue.pop(0)

        self._queue.append(value)
        self._last_time_ms = context.now_ms

        queue = self._queue[-int(width):]
        queue.sort()

        return queue[len(queue) // 2]
