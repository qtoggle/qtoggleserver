import os
import time

from collections.abc import Callable
from datetime import datetime

import pytest
import pytz

from freezegun import freeze_time

from qtoggleserver import peripherals, persist
from qtoggleserver.conf import settings
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core import vports as core_vports
from qtoggleserver.core.api.funcs import ports as ports_api_funcs
from tests.unit.qtoggleserver.mock.api import MockAPIRequest
from tests.unit.qtoggleserver.mock.peripherals import MockPeripheral
from tests.unit.qtoggleserver.mock.persist import MockPersistDriver
from tests.unit.qtoggleserver.mock.ports import MockBooleanPort, MockNumberPort


tz_info = pytz.timezone("Europe/Bucharest")


@pytest.fixture(scope="session", autouse=True)
def init_settings():
    settings.persist.driver = "qtoggleserver.drivers.persist.JSONDriver"
    settings.persist.file_path = ""


@pytest.fixture(scope="session")
def dummy_timestamp():
    return 1552559696.654321


@pytest.fixture(scope="session")
def dummy_utc_datetime():
    return datetime(2019, 3, 14, 10, 34, 56, microsecond=654321)


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
async def mock_vport1(mock_persist_driver, mocker) -> core_vports.VirtualPort:
    mocker.patch("asyncio.Lock")
    port = await ports_api_funcs.add_virtual_port({"id": "vport1", "type": "boolean"})
    yield port
    current = core_ports.get("vport1")
    if current is not None:
        await current.remove(persisted_data=False)
    await core_vports.remove("vport1")


@pytest.fixture
async def mock_vport2(mock_persist_driver, mocker) -> core_vports.VirtualPort:
    mocker.patch("asyncio.Lock")
    port = await ports_api_funcs.add_virtual_port({"id": "vport2", "type": "boolean"})
    yield port
    current = core_ports.get("vport2")
    if current is not None:
        await current.remove(persisted_data=False)
    await core_vports.remove("vport2")


@pytest.fixture
async def mock_peripheral1() -> MockPeripheral:
    peripheral = await peripherals.add(
        {
            "driver": "tests.unit.qtoggleserver.mock.peripherals.MockPeripheral",
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
            "driver": "tests.unit.qtoggleserver.mock.peripherals.MockPeripheral",
            "dummy_param": "dummy_value2",
            "name": "peripheral2",
        }
    )
    yield peripheral
    await peripherals.remove(peripheral.get_id(), persisted_data=True)


@pytest.fixture
def mock_api_request_maker() -> Callable:
    return MockAPIRequest
