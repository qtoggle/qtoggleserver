
import errno
import logging
import os
import pytz
import time

from qtoggleserver.conf import settings


logger = logging.getLogger(__name__)

OLD_TIME_LIMIT = 1546304400  # January 2019
DEFAULT_TIMEZONE = 'UTC'
ZONEINFO_PATH = '/usr/share/zoneinfo/'


class TimezoneError(Exception):
    pass


def has_real_date_time():
    # This is to distinguish between unset date (normally around 1970) and a system that has real date time support
    return time.time() > OLD_TIME_LIMIT


def get_timezone():
    try:
        target = os.readlink(settings.system.timezone_file)

    except FileNotFoundError:
        logger.debug('no timezone file, assuming %s', DEFAULT_TIMEZONE)
        return DEFAULT_TIMEZONE

    except OSError as e:
        if e.errno == errno.EINVAL:
            logger.error('timezone file is not a symlink')
            raise TimezoneError('timezone file is not a symlink')

        else:
            logger.error('failed to read timezone file symlink: %s', e)
            raise TimezoneError('failed to read timezone file symlink: {}'.format(e))

    except Exception as e:
        logger.error('failed to read timezone file symlink: %s', e)
        raise TimezoneError('failed to read timezone file symlink: {}'.format(e))

    # Expects timezone file to be a symlink to the real timezone file in /usr/share/zoneinfo/
    if not target.startswith(ZONEINFO_PATH):
        raise TimezoneError('unexpected timezone file symlink target: {}'.format(target))

    return target[len(ZONEINFO_PATH):]


def set_timezone(timezone):
    logger.debug('setting timezone to %s', timezone)

    if os.path.exists(settings.system.timezone_file):
        try:
            os.remove(settings.system.timezone_file)

        except Exception as e:
            logger.error('failed to remove timezone file symlink: %s', e)
            raise TimezoneError('failed to remove timezone file symlink: {}'.format(e))

    target = os.path.join(ZONEINFO_PATH, timezone)
    if not os.path.exists(target):
        logger.error('timezone file %s does not exist', target)
        raise TimezoneError('timezone file {} does not exist'.format(target))

    try:
        os.symlink(target, settings.system.timezone_file)

    except Exception as e:
        logger.error('failed to create timezone file symlink: %s', e)
        raise TimezoneError('failed to create timezone file symlink: {}'.format(e))


def get_timezones():
    return pytz.common_timezones
