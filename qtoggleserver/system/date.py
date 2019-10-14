
import datetime
import logging
import pytz
import time


logger = logging.getLogger(__name__)

_OLD_TIME_LIMIT = 1546304400  # January 2019
_cached_timezones = None


def has_real_date_time():
    return time.time() > _OLD_TIME_LIMIT


def has_timezone_support():
    return True


def get_timezone():
    return 'Europe/Bucharest'


def get_timezones():
    global _cached_timezones

    if _cached_timezones is None:
        logger.debug('loading timezones')

        dt = datetime.datetime(1971, 1, 1)
        timezones = []
        for zone in pytz.common_timezones:
            tz = pytz.timezone(zone)
            timezones.append((tz.fromutc(dt), zone, tz))

        # Sort by UTC offset
        timezones.sort(key=lambda z: (z[2].utcoffset(dt), z[1]))

        _cached_timezones = []
        for dt, zone, tz in timezones:
            offset_str = dt.strftime('%z')
            offset_str = offset_str[:3] + ':' + offset_str[3:]  # Transform +HHMM into +HH:MM
            tz_str = 'UTC {} ({})'.format(offset_str, zone)
            _cached_timezones.append(tz_str)

    return _cached_timezones
