from qtoggleserver import persist, system
from qtoggleserver.core import history as core_history
from qtoggleserver.core import ports as core_ports

from .base import DEP_ASAP, DEP_SECOND, EvalContext, EvalResult
from .exceptions import PortValueUnavailable, RealDateTimeUnavailable, ValueUnavailable
from .functions import Function, function
from .ports import PortRef


@function("AVAILABLE")
class AvailableFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    async def _eval(self, context: EvalContext) -> EvalResult:
        try:
            return await self.args[0].eval(context) is not None
        except ValueUnavailable:
            return False


@function("DEFAULT")
class DefaultFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        default = await self.args[1].eval(context)
        try:
            value = await self.args[0].eval(context)
            if value is not None:
                return value
            else:
                return default
        except ValueUnavailable:
            return default


@function("IGNCHG")
class IgnChgFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    async def _eval(self, context: EvalContext) -> EvalResult:
        return await self.args[0].eval(context)

    def _get_deps(self) -> set[str]:
        return set()


@function("RISING")
class RisingFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: float | None = None

    async def _eval(self, context: EvalContext) -> EvalResult:
        value = await self.args[0].eval(context)

        result = False
        if self._last_value is not None and value > self._last_value:
            result = True
        self._last_value = value

        return result


@function("FALLING")
class FallingFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: float | None = None

    async def _eval(self, context: EvalContext) -> EvalResult:
        value = await self.args[0].eval(context)

        result = False
        if self._last_value is not None and value < self._last_value:
            result = True
        self._last_value = value

        return result


@function("ACC")
class AccFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: float | None = None

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, accumulator = await self.eval_args(context)
        result = accumulator

        if self._last_value is not None:
            result += value - self._last_value

        self._last_value = value

        return result


@function("ACCINC")
class AccIncFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: float | None = None

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, accumulator = await self.eval_args(context)
        result = accumulator

        if (self._last_value is not None) and (value > self._last_value):
            result += value - self._last_value

        self._last_value = value

        return result


@function("HYST")
class HystFunction(Function):
    MIN_ARGS = MAX_ARGS = 3

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_result: int = 0

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, threshold1, threshold2 = await self.eval_args(context)

        self._last_result = int(
            (self._last_result == 0 and value > threshold2) or (self._last_result != 0 and value >= threshold1)
        )

        return self._last_result


@function("ONOFFAUTO")
class OnOffAutoFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def _eval(self, context: EvalContext) -> EvalResult:
        value, auto = await self.eval_args(context)
        if value > 0:
            return True
        elif value < 0:
            return False
        else:
            return auto


@function("SEQUENCE")
class SequenceFunction(Function):
    MIN_ARGS = 2
    DEPS = {DEP_ASAP}
    TRANSFORM_OK = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._start_time_ms: int = 0

    async def _eval(self, context: EvalContext) -> EvalResult:
        if self._start_time_ms == 0:
            self._start_time_ms = context.now_ms

        args = await self.eval_args(context)
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

        delta = context.now_ms - self._start_time_ms
        delta = delta % total_delay  # work modulo total_delay, to create repeat effect
        delay_so_far = 0
        result = values[0]
        for i in range(num_values):
            delay_so_far += delays[i]
            if delay_so_far >= delta:
                self.pause_asap_eval(context.now_ms + delay_so_far - delta)
                result = values[i]
                break

        return result


@function("HISTORY")
class HistoryFunction(Function):
    MIN_ARGS = MAX_ARGS = 3
    DEPS = {DEP_SECOND}
    ARG_KINDS = [PortRef]
    ENABLED = core_history.is_enabled
    TRANSFORM_OK = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._cached_sample: persist.Sample | None = None
        self._cached_timestamp: int = 0
        self._cached_max_diff: float | None = None

    async def _eval(self, context: EvalContext) -> EvalResult:
        if not system.date.has_real_date_time():
            raise RealDateTimeUnavailable()

        args = await self.eval_args(context)
        port_id, timestamp, max_diff = args
        port = core_ports.get(port_id)
        assert port

        # Transform everything to milliseconds
        timestamp *= 1000
        max_diff *= 1000

        # If arguments have changed from last cached values, invalidate the sample
        if self._cached_timestamp != timestamp or self._cached_max_diff != max_diff:
            self._cached_sample = None

        if self._cached_sample is not None:
            return self._cached_sample[1]

        if max_diff > 0:
            # Look through all values after given timestamp, but no newer than timestamp + max_diff, and consider the
            # oldest one
            from_timestamp = timestamp
            to_timestamp = timestamp + max_diff
            sort_desc = False
            consider_curr_value = from_timestamp <= context.now_ms < to_timestamp
        elif max_diff < 0:
            # Look through all values before given timestamp, but no older than timestamp - abs(max_diff), and consider
            # the newest one
            if context.now_ms <= timestamp:
                # Sample from the future requested, the best we've got is current value
                from_timestamp = to_timestamp = None
                consider_curr_value = True
            else:
                # +1 is needed to satisfy the inclusion/exclusion of the interval boundaries
                from_timestamp = timestamp + max_diff + 1  # max_diff is negative
                to_timestamp = timestamp + 1
                consider_curr_value = False

            sort_desc = True
        else:  # assuming max_dif == 0
            # Look through all values after given timestamp and consider the oldest one
            from_timestamp = timestamp
            to_timestamp = None
            sort_desc = False
            consider_curr_value = from_timestamp <= context.now_ms

        if from_timestamp is not None or to_timestamp is not None:
            samples = await core_history.get_samples_slice(
                port, from_timestamp, to_timestamp, limit=1, sort_desc=sort_desc
            )
            samples = list(samples)
        else:
            samples = []

        if samples:
            self._cached_sample = samples[0]
            self._cached_timestamp = timestamp
            self._cached_max_diff = max_diff
            value = self._cached_sample[1]
        elif consider_curr_value:
            value = port.get_last_read_value()
        else:
            value = None

        if value is None:
            raise PortValueUnavailable(port.get_id())

        return value
