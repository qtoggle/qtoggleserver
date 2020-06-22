
import datetime

from typing import Set

from qtoggleserver import system

from .functions import function, Function
from .exceptions import InvalidArgument, EvalSkipped


@function('YEAR')
class YearFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> float:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        return datetime.datetime.now().year


@function('MONTH')
class MonthFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> float:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        return datetime.datetime.now().month


@function('DAY')
class DayFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> float:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        return datetime.datetime.now().day


@function('DOW')
class DOWFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> float:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        return datetime.datetime.now().weekday()


@function('HOUR')
class HourFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> float:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        return datetime.datetime.now().hour


@function('MINUTE')
class MinuteFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> float:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        return datetime.datetime.now().minute


@function('SECOND')
class SecondFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> float:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        return datetime.datetime.now().second


@function('HMSINTERVAL')
class HMSIntervalFunction(Function):
    MIN_ARGS = 4
    MAX_ARGS = 6

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> float:
        if not system.date.has_real_date_time():
            raise EvalSkipped()

        now = datetime.datetime.now()

        if len(self.args) >= 6:
            start_h = self.args[0].eval()
            start_m = self.args[1].eval()
            start_s = self.args[2].eval()
            stop_h = self.args[3].eval()
            stop_m = self.args[4].eval()
            stop_s = self.args[5].eval()

            if not (0 <= start_h <= 23):
                raise InvalidArgument(1, start_h)

            if not (0 <= start_m <= 59):
                raise InvalidArgument(2, start_m)

            if not (0 <= start_s <= 59):
                raise InvalidArgument(3, start_s)

            if not (0 <= stop_h <= 23):
                raise InvalidArgument(4, stop_h)

            if not (0 <= stop_m <= 59):
                raise InvalidArgument(5, stop_m)

            if not (0 <= stop_s <= 59):
                raise InvalidArgument(6, stop_s)

            start_time = datetime.time(int(start_h), int(start_m), int(start_s))
            stop_time = datetime.time(int(stop_h), int(stop_m), int(stop_s))

        else:  # Assuming 4
            start_h = self.args[0].eval()
            start_m = self.args[1].eval()
            stop_h = self.args[2].eval()
            stop_m = self.args[3].eval()

            if not (0 <= start_h <= 23):
                raise InvalidArgument(1, start_h)

            if not (0 <= start_m <= 59):
                raise InvalidArgument(2, start_m)

            if not (0 <= stop_h <= 23):
                raise InvalidArgument(3, stop_h)

            if not (0 <= stop_m <= 59):
                raise InvalidArgument(4, stop_m)

            start_time = datetime.time(int(start_h), int(start_m), 00)
            stop_time = datetime.time(int(stop_h), int(stop_m), 59)

        start_dt = datetime.datetime.combine(now.date(), start_time)
        stop_dt = datetime.datetime.combine(now.date(), stop_time)

        return start_dt <= now <= stop_dt
