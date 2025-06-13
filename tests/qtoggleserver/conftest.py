import datetime
import os
import time

from typing import Callable

import pytest
import pytz

from freezegun import freeze_time

from qtoggleserver import peripherals, persist
from qtoggleserver.conf import settings
from qtoggleserver.core import ports as core_ports
from tests.qtoggleserver.mock.api import MockAPIRequest
from tests.qtoggleserver.mock.peripherals import MockPeripheral
from tests.qtoggleserver.mock.persist import MockPersistDriver
from tests.qtoggleserver.mock.ports import MockBooleanPort, MockNumberPort


tz_info = pytz.timezone("Europe/Bucharest")


@pytest.fixture(scope="session", autouse=True)
def init_settings():
    settings.persist.driver = "qtoggleserver.drivers.persist.JSONDriver"
    settings.persist.file_path = ""


@pytest.fixture(scope="session")
def dummy_utc_datetime():
    return datetime.datetime(2019, 3, 14, 10, 34, 56, microsecond=654321)


@pytest.fixture(scope="session")
def dummy_local_datetime(dummy_utc_datetime):
    dt = dummy_utc_datetime.replace(tzinfo=pytz.utc)
    dt = dt.astimezone(tz_info)
    dt = dt.replace(tzinfo=None)

    os.environ["TZ"] = tz_info.zone
    time.tzset()

    return dt


@pytest.fixture(scope="session")
def local_tz_info():
    return tz_info


@pytest.fixture
def freezer(dummy_local_datetime):
    freezer = freeze_time()
    frozen_time = freezer.start()
    yield frozen_time
    freezer.stop()


@pytest.fixture(scope="session")
def dummy_timestamp():
    return 1552559696.654321


@pytest.fixture
def mock_persist_driver():
    persist._thread_local.driver = MockPersistDriver()
    return persist._thread_local.driver


@pytest.fixture
async def mock_num_port1(mocker) -> MockNumberPort:
    mocker.patch("asyncio.Lock")
    port = (await core_ports.load([{"driver": MockNumberPort, "port_id": "nid1", "value": None}]))[0]
    await port.enable()

    yield port
    await port.remove(persisted_data=False)


@pytest.fixture
async def mock_num_port2(mocker) -> MockNumberPort:
    mocker.patch("asyncio.Lock")
    port = (await core_ports.load([{"driver": MockNumberPort, "port_id": "nid2", "value": None}]))[0]
    await port.enable()

    yield port
    await port.remove(persisted_data=False)


@pytest.fixture
async def mock_bool_port1(mocker) -> MockBooleanPort:
    mocker.patch("asyncio.Lock")
    port = (await core_ports.load([{"driver": MockBooleanPort, "port_id": "bid1", "value": None}]))[0]
    await port.enable()

    yield port
    await port.remove(persisted_data=False)


@pytest.fixture
async def mock_bool_port2(mocker) -> MockBooleanPort:
    mocker.patch("asyncio.Lock")
    port = (await core_ports.load([{"driver": MockBooleanPort, "port_id": "bid2", "value": None}]))[0]
    await port.enable()

    yield port
    await port.remove(persisted_data=False)


@pytest.fixture
async def mock_peripheral1() -> MockPeripheral:
    peripheral = await peripherals.add(
        {
            "driver": "tests.qtoggleserver.mock.peripherals.MockPeripheral",
            "dummy_param": "dummy_value1",
            "name": "peripheral1",
        }
    )
    yield peripheral
    await peripherals.remove(peripheral.get_id(), persisted_data=True)


@pytest.fixture
async def mock_peripheral2() -> MockPeripheral:
    peripheral = await peripherals.add(
        {
            "driver": "tests.qtoggleserver.mock.peripherals.MockPeripheral",
            "dummy_param": "dummy_value2",
            "name": "peripheral2",
        }
    )
    yield peripheral
    await peripherals.remove(peripheral.get_id(), persisted_data=True)


@pytest.fixture
def mock_api_request_maker() -> Callable:
    return MockAPIRequest
