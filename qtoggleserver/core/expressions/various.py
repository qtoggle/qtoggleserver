
import time

from typing import Any, Dict, Optional

from qtoggleserver import system
from qtoggleserver.core import history

from .base import Evaluated
from .exceptions import PortValueUnavailable, ExpressionEvalError, EvalSkipped
from .functions import function, Function
from .port import PortRef


@function('AVAILABLE')
class AvailableFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    async def eval(self) -> Evaluated:
        try:
            await self.args[0].eval()
            return True

        except ExpressionEvalError:
            return False


@function('DEFAULT')
class DefaultFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    async def eval(self) -> Evaluated:
        try:
            return await self.args[0].eval()

        except ExpressionEvalError:
            return await self.args[1].eval()


@function('ACC')
class AccFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_value: Optional[float] = None

    async def eval(self) -> Evaluated:
        value, accumulator = await self.eval_args()
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

    async def eval(self) -> Evaluated:
        value, accumulator = await self.eval_args()
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

    async def eval(self) -> Evaluated:
        value, threshold1, threshold2 = await self.eval_args()

        self._last_result = int((self._last_result == 0 and value > threshold2) or
                                (self._last_result != 0 and value >= threshold1))

        return self._last_result


@function('SEQUENCE')
class SequenceFunction(Function):
    MIN_ARGS = 2
    DEPS = ['millisecond']

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_time: float = 0

    async def eval(self) -> Evaluated:
        now = time.time() * 1000

        if self._last_time == 0:
            self._last_time = now

        args = await self.eval_args()
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


@function('LUT')
class LUTFunction(Function):
    MIN_ARGS = 5

    async def eval(self) -> Evaluated:
        args = await self.eval_args()
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

            if x - p1[0] < p2[0] - x:  # Closer to p1 than to p2
                return p1[1]

            else:
                return p2[1]

        return points[length - 1][1]


@function('LUTLI')
class LUTLIFunction(Function):
    MIN_ARGS = 5

    async def eval(self) -> Evaluated:
        args = await self.eval_args()
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


@function('HISTORY')
class HistoryFunction(Function):
    MIN_ARGS = MAX_ARGS = 3
    DEPS = ['second']
    ARG_KINDS = [PortRef]
    ENABLED = history.is_enabled

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._cached_sample: Optional[Dict[str, Any]] = None
        self._cached_timestamp: int = 0
        self._cached_max_diff: Optional[float] = None

    async def eval(self) -> Evaluated:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        args = await self.eval_args()
        port, timestamp, max_diff = args

        # Transform everything to milliseconds
        timestamp *= 1000
        max_diff *= 1000
        now_ms = int(time.time() * 1000)

        # If arguments have changed from last cached values, invalidate the sample
        if self._cached_timestamp != timestamp or self._cached_max_diff != max_diff:
            self._cached_sample = None

        if self._cached_sample is not None:
            return self._cached_sample['value']

        if max_diff > 0:
            # Look through all values after given timestamp, but no newer than timestamp + max_diff, and consider the
            # oldest one
            from_timestamp = timestamp
            to_timestamp = timestamp + max_diff
            sort_desc = False
            consider_curr_value = from_timestamp <= now_ms < to_timestamp

        elif max_diff < 0:
            # Look through all values before given timestamp, but no older than timestamp - abs(max_diff), and consider
            # the newest one
            if now_ms <= timestamp:
                # Sample from the future requested, the best we've got is current value
                from_timestamp = to_timestamp = None
                consider_curr_value = True

            else:
                # +1 is needed to satisfy the inclusion/exclusion of the interval boundaries
                from_timestamp = timestamp + max_diff + 1  # max_diff is negative
                to_timestamp = timestamp + 1
                consider_curr_value = False

            sort_desc = True

        else:  # Assuming max_dif == 0
            # Look through all values after given timestamp and consider the oldest one
            from_timestamp = timestamp
            to_timestamp = None
            sort_desc = False
            consider_curr_value = from_timestamp <= now_ms

        if from_timestamp is not None or to_timestamp is not None:
            samples = await history.get_samples_slice(port, from_timestamp, to_timestamp, limit=1, sort_desc=sort_desc)
            samples = list(samples)

        else:
            samples = []

        if samples:
            self._cached_sample = samples[0]
            self._cached_timestamp = timestamp
            self._cached_max_diff = max_diff
            value = self._cached_sample['value']

        elif consider_curr_value:
            value = port.get_last_read_value()

        else:
            value = None

        if value is None:
            raise PortValueUnavailable(port.get_id())

        return value
