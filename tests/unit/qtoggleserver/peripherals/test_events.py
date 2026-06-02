from qtoggleserver.core import api as core_api
from qtoggleserver.peripherals import events as peripherals_events
from tests.unit.qtoggleserver.mock.peripherals import MockPeripheral


class TestPeripheralAdd:
    async def test_get_params(self):
        peripheral = MockPeripheral(name="test", dummy_param="v")
        event = peripherals_events.PeripheralAdd(peripheral)

        assert await event.get_params() == peripheral.to_json()
        assert event.TYPE == "peripheral-add"
        assert event.REQUIRED_ACCESS == core_api.ACCESS_LEVEL_ADMIN


class TestPeripheralRemove:
    async def test_get_params(self):
        peripheral = MockPeripheral(name="test", dummy_param="v")
        event = peripherals_events.PeripheralRemove(peripheral)

        assert await event.get_params() == {"id": peripheral.get_id()}
        assert event.TYPE == "peripheral-remove"
        assert event.REQUIRED_ACCESS == core_api.ACCESS_LEVEL_ADMIN


class TestPeripheralUpdate:
    async def test_get_params(self):
        peripheral = MockPeripheral(name="test", dummy_param="v")
        event = peripherals_events.PeripheralUpdate(peripheral)

        assert await event.get_params() == peripheral.to_json()
        assert event.TYPE == "peripheral-update"
        assert event.REQUIRED_ACCESS == core_api.ACCESS_LEVEL_ADMIN

    def test_is_duplicate_true_for_same_peripheral(self):
        peripheral = MockPeripheral(name="test", dummy_param="v")
        event1 = peripherals_events.PeripheralUpdate(peripheral)
        event2 = peripherals_events.PeripheralUpdate(peripheral)

        assert event1.is_duplicate(event2) is True

    def test_is_duplicate_false_for_different_peripherals(self):
        peripheral1 = MockPeripheral(name="test1", dummy_param="v")
        peripheral2 = MockPeripheral(name="test2", dummy_param="v")
        event1 = peripherals_events.PeripheralUpdate(peripheral1)
        event2 = peripherals_events.PeripheralUpdate(peripheral2)

        assert event1.is_duplicate(event2) is False
