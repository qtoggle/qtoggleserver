
import logging
import pytz
import subprocess
import time

from qtoggleserver.conf import settings


logger = logging.getLogger(__name__)

OLD_TIME_LIMIT = 1546304400  # January 2019


class DateError(Exception):
    pass


def has_real_date_time():
    # This is to distinguish between unset date (normally around 1970) and a system that has real date time support
    return time.time() > OLD_TIME_LIMIT


def has_date_support():
    return bool(settings.system.date.set)


def set_date(date):
    date_str = date.strftime(settings.system.date.set_format)
    env = {'QS_DATE': date_str}

    try:
        subprocess.check_output(settings.system.date.set, env=env, stderr=subprocess.STDOUT, shell=True)
        logger.debug('date set to %s', date.strftime('%Y-%m-%dT%H:%M:%S'))

    except Exception as e:
        logger.error('date set hook call failed: %s', e)
        raise DateError('date set hook failed: {}'.format(e))


def has_timezone_support():
    return bool(settings.system.timezone.get_hook and settings.system.timezone.set_hook)


def get_timezone():
    try:
        timezone = subprocess.check_output(settings.system.timezone.get_hook, stderr=subprocess.STDOUT, shell=True)
        timezone = timezone.strip().decode()

        logger.debug('timezone = %s', timezone)

        return timezone

    except Exception as e:
        logger.error('timezone get hook call failed: %s', e)
        raise DateError('timezone get hook failed: {}'.format(e))


def set_timezone(timezone):
    env = {'QS_TIMEZONE': timezone}

    try:
        subprocess.check_output(settings.system.timezone.set_hook, env=env, stderr=subprocess.STDOUT, shell=True)
        logger.debug('timezone set to %s', timezone)

    except Exception as e:
        logger.error('timezone set hook call failed: %s', e)
        raise DateError('timezone set hook failed: {}'.format(e))


def get_timezones():
    return pytz.common_timezones
