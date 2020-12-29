
import datetime
import os
import time

import pytest
import pytz

from freezegun import freeze_time

from qtoggleserver import persist
from qtoggleserver.core import expressions  # Required to prevent partial import errors due to circular imports
from qtoggleserver.core import ports as core_ports

from tests.qtoggleserver.mock import MockPersistDriver, NumberMockPort, BooleanMockPort


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


@pytest.fixture
def mock_persist_driver():
    persist._thread_local.driver = MockPersistDriver()
    return persist._thread_local.driver


@pytest.fixture
async def num_mock_port1() -> NumberMockPort:
    port = (await core_ports.load([{'driver': NumberMockPort, 'port_id': 'nid1', 'value': None}]))[0]
    await port.enable()

    yield port
    await port.remove(persisted_data=False)


@pytest.fixture
async def num_mock_port2() -> NumberMockPort:
    port = (await core_ports.load([{'driver': NumberMockPort, 'port_id': 'nid2', 'value': None}]))[0]
    await port.enable()

    yield port
    await port.remove(persisted_data=False)


@pytest.fixture
async def bool_mock_port1() -> BooleanMockPort:
    port = (await core_ports.load([{'driver': BooleanMockPort, 'port_id': 'bid1', 'value': None}]))[0]
    await port.enable()

    yield port
    await port.remove(persisted_data=False)


@pytest.fixture
async def bool_mock_port2() -> BooleanMockPort:
    port = (await core_ports.load([{'driver': BooleanMockPort, 'port_id': 'bid2', 'value': None}]))[0]
    await port.enable()

    yield port
    await port.remove(persisted_data=False)
