
import time


_OLD_TIME_LIMIT = 1546304400  # January 2019


def has_real_date_time():
    return time.time() > _OLD_TIME_LIMIT
