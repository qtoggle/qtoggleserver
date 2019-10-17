
import logging
import pytz
import subprocess
import time

from qtoggleserver.conf import settings


logger = logging.getLogger(__name__)

OLD_TIME_LIMIT = 1546304400  # January 2019


class TimezoneError(Exception):
    pass


def has_real_date_time():
    # This is to distinguish between unset date (normally around 1970) and a system that has real date time support
    return time.time() > OLD_TIME_LIMIT


def has_timezone_support():
    return bool(settings.system.timezone_hooks.get and settings.system.timezone_hooks.set)


def get_timezone():
    try:
        timezone = subprocess.check_output(settings.system.timezone_hooks.get, stderr=subprocess.STDOUT,shell=True)
        timezone = timezone.strip().decode()

        logger.debug('timezone = "%s"', timezone)

        return timezone

    except Exception as e:
        logger.error('timezone get hook call failed: %s', e)
        raise TimezoneError('timezone get hook failed: {}'.format(e))


def set_timezone(timezone):
    env = {'QS_TIMEZONE': timezone}

    try:
        subprocess.check_output(settings.system.timezone_hooks.set, env=env, stderr=subprocess.STDOUT, shell=True)
        logger.debug('timezone set to %s', timezone)

    except Exception as e:
        logger.error('timezone set hook call failed: %s', e)
        raise TimezoneError('timezone set hook failed: {}'.format(e))


def get_timezones():
    return pytz.common_timezones
