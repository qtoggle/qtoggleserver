from . import TIME_JUMP_THRESHOLD
from .base import DEP_ASAP, EvalContext, EvalResult
from .functions import Function, function


@function("DELAY")
class DelayFunction(Function):
    MIN_ARGS = MAX_ARGS = 2
    DEPS = {DEP_ASAP}
    HISTORY_SIZE = 1024
    TRANSFORM_OK = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._queue: list[tuple[int, float]] = []
        self._last_value: float | None = None
        self._current_value: float | None = None

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, delay = await self.eval_args(context)

        if self._current_value is None:
            self._current_value = value
            self.pause_asap_eval()
            return value

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

        if self._queue:
            self.pause_asap_eval(self._queue[0][0] + delay)
        else:
            self.pause_asap_eval()

        return self._current_value


@function("TIMER")
class TimerFunction(Function):
    MIN_ARGS = MAX_ARGS = 4
    DEPS = {DEP_ASAP}
    TRANSFORM_OK = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._start_time_ms: int = 0

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, start_value, stop_value, timeout = await self.eval_args(context)

        if self._start_time_ms:  # timer active
            delta = context.now_ms - self._start_time_ms
            if delta >= timeout or not value:  # timer expired or value became false
                self._start_time_ms = 0
                self.pause_asap_eval()
                return stop_value
            else:
                return start_value

        else:  # timer inactive
            if value:
                # start timer
                self._start_time_ms = context.now_ms
                self.pause_asap_eval(self._start_time_ms + timeout)
                return start_value
            else:
                self.pause_asap_eval()
                return stop_value


@function("SAMPLE")
class SampleFunction(Function):
    MIN_ARGS = MAX_ARGS = 2
    DEPS = {DEP_ASAP}
    TRANSFORM_OK = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: float | None = None
        self._last_time_ms: int = 0

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, duration_ms = await self.eval_args(context)

        if context.now_ms - self._last_time_ms < duration_ms:
            self.pause_asap_eval(self._last_time_ms + duration_ms)
            return self._last_value

        self._last_time_ms = context.now_ms
        self._last_value = value
        self.pause_asap_eval(context.now_ms + duration_ms)

        return self._last_value


@function("FREEZE")
class FreezeFunction(Function):
    MIN_ARGS = MAX_ARGS = 2
    DEPS = {DEP_ASAP}
    TRANSFORM_OK = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: float | None = None
        self._last_time_ms: int = 0

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, duration_ms = await self.eval_args(context)
        if self._last_time_ms == 0:  # idle
            if value != self._last_value:  # value change detected, start timer
                self._last_time_ms = context.now_ms
                self._last_value = value
                self.pause_asap_eval(self._last_time_ms + duration_ms)
            else:
                self.pause_asap_eval()
        else:  # timer active
            if context.now_ms - self._last_time_ms >= duration_ms:  # timer expired
                self._last_time_ms = 0  # stop timer
                if value != self._last_value:  # value change detected, start timer
                    self._last_time_ms = context.now_ms
                    self._last_value = value
                    self.pause_asap_eval(self._last_time_ms + duration_ms)
                else:
                    self.pause_asap_eval()
            else:
                self.pause_asap_eval(self._last_time_ms + duration_ms)

        return self._last_value


@function("HELD")
class HeldFunction(Function):
    MIN_ARGS = MAX_ARGS = 3
    DEPS = {DEP_ASAP}
    TRANSFORM_OK = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._start_time_ms: int | None = None

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, fixed_value, duration = await self.eval_args(context)

        if value == fixed_value:
            if not self._start_time_ms:  # timer is off
                self._start_time_ms = context.now_ms
                self.pause_asap_eval(self._start_time_ms + duration)
            else:
                if context.now_ms - self._start_time_ms >= duration:
                    # If value held past duration, pause until value changes
                    self.pause_asap_eval()
        else:
            self._start_time_ms = 0  # stop timer
            self.pause_asap_eval()

        return self._start_time_ms > 0 and context.now_ms - self._start_time_ms >= duration


@function("DERIV")
class DerivFunction(Function):
    MIN_ARGS = MAX_ARGS = 2
    DEPS = {DEP_ASAP}
    TRANSFORM_OK = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: float | None = None
        self._last_time_ms: int = 0
        self._last_result: float = 0

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, sampling_interval = await self.eval_args(context)

        if self._last_value is not None:
            delta = context.now_ms - self._last_time_ms
            if delta < sampling_interval:
                self.pause_asap_eval(self._last_time_ms + sampling_interval)
                return self._last_result

            if delta > TIME_JUMP_THRESHOLD:
                self._last_value = value
                self._last_time_ms = context.now_ms
                self.pause_asap_eval(self._last_time_ms + sampling_interval)
                return 0

            self._last_result = (value - self._last_value) / delta * 1000

        self._last_value = value
        self._last_time_ms = context.now_ms
        self.pause_asap_eval(self._last_time_ms + sampling_interval)

        return self._last_result


@function("INTEG")
class IntegFunction(Function):
    MIN_ARGS = MAX_ARGS = 3
    DEPS = {DEP_ASAP}
    TRANSFORM_OK = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: float | None = None
        self._last_time_ms: int = 0

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, accumulator, sampling_interval = await self.eval_args(context)
        result = accumulator

        if self._last_value is not None:
            delta = context.now_ms - self._last_time_ms
            if delta < sampling_interval:
                self.pause_asap_eval(self._last_time_ms + sampling_interval)
                return result

            if delta > TIME_JUMP_THRESHOLD:
                self._last_value = value
                self._last_time_ms = context.now_ms
                self.pause_asap_eval(self._last_time_ms + sampling_interval)
                return result

            result += (value + self._last_value) * delta / 2000

        self._last_value = value
        self._last_time_ms = context.now_ms
        self.pause_asap_eval(self._last_time_ms + sampling_interval)

        return result


@function("FMAVG")
class FMAvgFunction(Function):
    MIN_ARGS = MAX_ARGS = 3
    DEPS = {DEP_ASAP}
    MAX_QUEUE_SIZE = 1024
    TRANSFORM_OK = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._queue: list[float] = []
        self._last_time_ms: int = 0
        self._last_result: float = 0

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, width, sampling_interval = await self.eval_args(context)
        width = min(width, self.MAX_QUEUE_SIZE)

        if self._last_time_ms > 0:
            if context.now_ms - self._last_time_ms < sampling_interval:
                self.pause_asap_eval(self._last_time_ms + sampling_interval)
                return self._last_result

        # Make room for the new element
        while len(self._queue) >= width:
            self._queue.pop(0)

        self._queue.append(value)
        self._last_time_ms = context.now_ms

        queue = self._queue[-int(width) :]
        self._last_result = sum(queue) / len(queue)
        self.pause_asap_eval(self._last_time_ms + sampling_interval)

        return self._last_result


@function("FMEDIAN")
class FMedianFunction(Function):
    MIN_ARGS = MAX_ARGS = 3
    DEPS = {DEP_ASAP}
    MAX_QUEUE_SIZE = 1024
    TRANSFORM_OK = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._queue: list[float] = []
        self._last_time_ms: int = 0
        self._last_result: float = 0

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, width, sampling_interval = await self.eval_args(context)
        width = min(width, self.MAX_QUEUE_SIZE)

        if self._last_time_ms > 0:
            if context.now_ms - self._last_time_ms < sampling_interval:
                self.pause_asap_eval(self._last_time_ms + sampling_interval)
                self.pause_asap_eval(self._last_time_ms + sampling_interval)
                return self._last_result

        # Make room for the new element
        while len(self._queue) >= width:
            self._queue.pop(0)

        self._queue.append(value)
        self._last_time_ms = context.now_ms
        self.pause_asap_eval(self._last_time_ms + sampling_interval)

        queue = self._queue[-int(width) :]
        queue.sort()
        self._last_result = queue[len(queue) // 2]

        return self._last_result
