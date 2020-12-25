
import datetime
import os
import time

import pytest
import pytz

from freezegun import freeze_time


tz_info = pytz.timezone('Europe/Bucharest')


@pytest.fixture(scope='session')
def dummy_utc_datetime():
    return datetime.datetime(2019, 3, 14, 10, 34, 56, microsecond=654321)


@pytest.fixture(scope='session')
def dummy_local_datetime(dummy_utc_datetime):
    dt = dummy_utc_datetime.replace(tzinfo=pytz.utc)
    dt = dt.astimezone(tz_info)
    dt = dt.replace(tzinfo=None)

    os.environ['TZ'] = tz_info.zone
    time.tzset()

    return dt


@pytest.fixture(scope='session')
def local_tz_info():
    return tz_info


@pytest.fixture
def freezer(dummy_local_datetime):
    freezer = freeze_time()
    frozen_time = freezer.start()
    yield frozen_time
    freezer.stop()


@pytest.fixture(scope='session')
def dummy_timestamp():
    return 1552559696.654321
