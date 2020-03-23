
import datetime
import time

from typing import Iterable

import pytz

from qtoggleserver.conf import settings
from qtoggleserver.utils.cmd import run_get_cmd, run_set_cmd


OLD_TIME_LIMIT = 1546304400  # January 2019


class DateError(Exception):
    pass


def has_real_date_time() -> bool:
    # This is to distinguish between unset date (normally around 1970) and a system that has real date time support
    return time.time() > OLD_TIME_LIMIT


def has_set_date_support() -> bool:
    return bool(settings.system.date.set_cmd)


def set_date(date: datetime.datetime) -> None:
    date_str = date.strftime(settings.system.date.set_format)
    run_set_cmd(settings.system.date.set_cmd, cmd_name='date', exc_class=DateError, date=date_str)


def has_timezone_support() -> bool:
    return bool(settings.system.timezone.get_cmd and settings.system.timezone.set_cmd)


def get_timezone() -> str:
    return run_get_cmd(
        settings.system.timezone.get_cmd,
        cmd_name='timezone',
        exc_class=DateError,
        required_fields=['timezone']
    )['timezone']


def set_timezone(timezone: str) -> None:
    run_set_cmd(settings.system.timezone.set_cmd, cmd_name='timezone', exc_class=DateError, timezone=timezone)


def get_timezones() -> Iterable[str]:
    return pytz.common_timezones
