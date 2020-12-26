
import abc
import calendar
import datetime
import time

from qtoggleserver import system

from .base import Evaluated
from .exceptions import InvalidArgumentValue, EvalSkipped
from .functions import function, Function


class DateUnitFunction(Function, metaclass=abc.ABCMeta):
    MIN_ARGS = 0
    MAX_ARGS = 1
    DEPS = ['second']

    async def eval(self) -> Evaluated:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        if len(self.args) > 0:
            timestamp = int(await self.args[0].eval())

        else:
            timestamp = int(time.time())

        return self.extract_unit(datetime.datetime.fromtimestamp(timestamp))

    @abc.abstractmethod
    def extract_unit(self, dt: datetime.datetime) -> int:
        raise NotImplementedError()


@function('YEAR')
class YearFunction(DateUnitFunction):
    def extract_unit(self, dt: datetime.datetime) -> int:
        return dt.year


@function('MONTH')
class MonthFunction(DateUnitFunction):
    def extract_unit(self, dt: datetime.datetime) -> int:
        return dt.month


@function('DAY')
class DayFunction(DateUnitFunction):
    def extract_unit(self, dt: datetime.datetime) -> int:
        return dt.day


@function('DOW')
class DOWFunction(DateUnitFunction):
    def extract_unit(self, dt: datetime.datetime) -> int:
        return dt.weekday()


@function('LDOM')
class LDOMFunction(DateUnitFunction):
    def extract_unit(self, dt: datetime.datetime) -> int:
        return calendar.monthrange(dt.year, dt.month)[1]


@function('HOUR')
class HourFunction(DateUnitFunction):
    def extract_unit(self, dt: datetime.datetime) -> int:
        return dt.hour


@function('MINUTE')
class MinuteFunction(DateUnitFunction):
    def extract_unit(self, dt: datetime.datetime) -> int:
        return dt.minute


@function('SECOND')
class SecondFunction(DateUnitFunction):
    def extract_unit(self, dt: datetime.datetime) -> int:
        return dt.second


@function('MILLISECOND')
class MillisecondFunction(Function):
    MIN_ARGS = MAX_ARGS = 0
    DEPS = ['millisecond']

    async def eval(self) -> Evaluated:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        return datetime.datetime.now().microsecond // 1000


@function('DATE')
class DateFunction(Function):
    MIN_ARGS = MAX_ARGS = 6
    DEPS = ['second']
    UNIT_INDEX = {u: i + 1 for i, u in enumerate(('year', 'month', 'day', 'hour', 'minute', 'second'))}

    async def eval(self) -> Evaluated:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        eval_args = [int(await self.args[i].eval()) for i in range(self.MIN_ARGS)]

        try:
            return int(datetime.datetime(*eval_args).timestamp())

        except ValueError as e:
            unit = str(e).split()[0]
            index = self.UNIT_INDEX.get(unit)
            if index is None:
                raise

            raise InvalidArgumentValue(index, eval_args[index])


@function('BOY')
class BOYFunction(Function):
    MIN_ARGS = 0
    MAX_ARGS = 1
    DEPS = ['second']

    async def eval(self) -> Evaluated:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        now = datetime.datetime.now()

        n = 0
        if len(self.args) > 0:
            n = int(await self.args[0].eval())

        dt = datetime.datetime(now.year + n, 1, 1, 0, 0, 0)
        dt = dt.astimezone(tz=datetime.timezone.utc)

        return dt.timestamp()


@function('BOM')
class BOMFunction(Function):
    MIN_ARGS = 0
    MAX_ARGS = 1
    DEPS = ['second']

    async def eval(self) -> Evaluated:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        now = datetime.datetime.now()
        n = 0
        if len(self.args) > 0:
            n = int(await self.args[0].eval())

        year, month = now.year, now.month
        if n >= 0:
            for _ in range(n):
                if month < 12:
                    month += 1

                else:
                    year += 1
                    month = 1

        else:
            for _ in range(-n):
                if month > 1:
                    month -= 1

                else:
                    year -= 1
                    month = 12

        dt = datetime.datetime(year, month, 1, 0, 0, 0)
        dt = dt.astimezone(tz=datetime.timezone.utc)

        return dt.timestamp()


@function('BOW')
class BOWFunction(Function):
    MIN_ARGS = 0
    MAX_ARGS = 2
    DEPS = ['second']

    async def eval(self) -> Evaluated:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        n = 0
        s = 0
        if len(self.args) > 0:
            n = int(await self.args[0].eval())
            if len(self.args) > 1:
                s = int(await self.args[1].eval())

        now = datetime.datetime.now()
        dt = now.replace(hour=12)  # Using mid day practically avoids problems due to DST
        if s > 0:
            dt -= datetime.timedelta(days=dt.weekday() + 7 - s)

        else:
            dt -= datetime.timedelta(days=dt.weekday())

        year, month, day = dt.year, dt.month, dt.day
        if n >= 0:
            for _ in range(n):
                last_day = calendar.monthrange(year, month)[1]
                if day + 7 <= last_day:
                    day += 7

                else:
                    day = 7 - last_day + day
                    if month < 12:
                        month += 1

                    else:
                        year += 1
                        month = 1

        else:
            for _ in range(-n):
                if day > 7:
                    day -= 7

                else:
                    if month > 1:
                        month -= 1

                    else:
                        year -= 1
                        month = 12

                    last_day = calendar.monthrange(year, month)[1]
                    day = last_day - 7 + day

        dt = datetime.datetime(year, month, day)
        dt = dt.astimezone(tz=datetime.timezone.utc)

        return dt.timestamp()


@function('BOD')
class BODFunction(Function):
    MIN_ARGS = 0
    MAX_ARGS = 1
    DEPS = ['second']

    async def eval(self) -> Evaluated:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        now = datetime.datetime.now()
        n = 0
        if len(self.args) > 0:
            n = int(await self.args[0].eval())
        dt = now + datetime.timedelta(days=n)
        dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        dt = dt.astimezone(tz=datetime.timezone.utc)

        return dt.timestamp()


@function('HMSINTERVAL')
class HMSIntervalFunction(Function):
    MIN_ARGS = MAX_ARGS = 6
    DEPS = ['second']

    async def eval(self) -> Evaluated:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        now = datetime.datetime.now().replace(microsecond=0)

        start_h, start_m, start_s, stop_h, stop_m, stop_s = await self.eval_args()

        if not (0 <= start_h <= 23):
            raise InvalidArgumentValue(1, start_h)

        if not (0 <= start_m <= 59):
            raise InvalidArgumentValue(2, start_m)

        if not (0 <= start_s <= 59):
            raise InvalidArgumentValue(3, start_s)

        if not (0 <= stop_h <= 23):
            raise InvalidArgumentValue(4, stop_h)

        if not (0 <= stop_m <= 59):
            raise InvalidArgumentValue(5, stop_m)

        if not (0 <= stop_s <= 59):
            raise InvalidArgumentValue(6, stop_s)

        start_time = datetime.time(int(start_h), int(start_m), int(start_s))
        stop_time = datetime.time(int(stop_h), int(stop_m), int(stop_s))

        start_dt = datetime.datetime.combine(now.date(), start_time)
        stop_dt = datetime.datetime.combine(now.date(), stop_time)

        return int(start_dt <= now <= stop_dt)


@function('MDINTERVAL')
class MDIntervalFunction(Function):
    MIN_ARGS = MAX_ARGS = 4
    DEPS = ['second']

    async def eval(self) -> Evaluated:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        now = datetime.datetime.now().replace(microsecond=0)

        start_m, start_d, stop_m, stop_d = await self.eval_args()

        if not (1 <= start_m <= 12):
            raise InvalidArgumentValue(1, start_m)

        try:
            start_dt = now.replace(month=int(start_m), day=int(start_d))

        except ValueError:
            raise InvalidArgumentValue(2, start_d)

        if not (1 <= stop_m <= 12):
            raise InvalidArgumentValue(3, stop_m)

        try:
            stop_dt = now.replace(month=int(stop_m), day=int(stop_d))

        except ValueError:
            raise InvalidArgumentValue(4, stop_d)

        return int(start_dt <= now <= stop_dt)
