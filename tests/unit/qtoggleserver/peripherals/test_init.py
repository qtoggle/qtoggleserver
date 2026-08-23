import pytest

from qtoggleserver import peripherals, persist


class TestAdd:
    async def test_no_such_module_raises_driver_load_error(self, mock_persist_driver):
        with pytest.raises(peripherals.DriverLoadError):
            await peripherals.add({"driver": "tests.unit.qtoggleserver.mock.no_such_module.SomeClass"})

    async def test_no_such_attr_raises_driver_load_error(self, mock_persist_driver):
        with pytest.raises(peripherals.DriverLoadError):
            await peripherals.add({"driver": "tests.unit.qtoggleserver.mock.peripherals.NoSuchClass"})

    async def test_non_dynload_error_is_not_masked_as_driver_load_error(self, mock_persist_driver):
        # A bug unrelated to module/attribute lookup (here: a malformed driver path with no dot,
        # which makes load_attr's `m, attr = attr_path.rsplit(".", 1)` raise ValueError) must
        # propagate as-is instead of being reported as a misleading "no such driver" error.
        with pytest.raises(ValueError):
            await peripherals.add({"driver": "no_dot_in_this_path"})

    async def test_persists_display_name(self, mock_persist_driver):
        peripheral = await peripherals.add(
            {
                "driver": "tests.unit.qtoggleserver.mock.peripherals.MockPeripheral",
                "dummy_param": "dummy_value",
                "name": "peripheral_with_display_name",
                "display_name": "Peripheral Display Name",
            }
        )

        try:
            persisted = await persist.get("peripherals", peripheral.get_id())
            assert persisted is not None
            assert persisted["display_name"] == "Peripheral Display Name"
        finally:
            await peripherals.remove(peripheral.get_id(), persisted_data=True)

    async def test_does_not_persist_when_persisted_data_is_false(self, mock_persist_driver):
        peripheral = await peripherals.add(
            {
                "driver": "tests.unit.qtoggleserver.mock.peripherals.MockPeripheral",
                "dummy_param": "dummy_value",
                "name": "peripheral_without_persisted_data",
            },
            persisted_data=False,
        )

        try:
            assert await persist.get("peripherals", peripheral.get_id()) is None
        finally:
            await peripherals.remove(peripheral.get_id(), persisted_data=False)

    async def test_defaults_display_name_to_empty_string(self, mock_persist_driver):
        peripheral = await peripherals.add(
            {
                "driver": "tests.unit.qtoggleserver.mock.peripherals.MockPeripheral",
                "dummy_param": "dummy_value",
                "name": "peripheral_without_display_name",
            }
        )

        try:
            assert peripheral.get_display_name() == ""
            persisted = await persist.get("peripherals", peripheral.get_id())
            assert persisted is not None
            assert persisted["display_name"] == ""
        finally:
            await peripherals.remove(peripheral.get_id(), persisted_data=True)

    async def test_legacy_flat_payload_does_not_treat_display_name_as_driver_param(self, mock_persist_driver):
        peripheral = await peripherals.add(
            {
                "driver": "tests.unit.qtoggleserver.mock.peripherals.MockPeripheral",
                "dummy_param": "dummy_value",
                "name": "legacy_peripheral_with_display_name",
                "display_name": "Legacy Display Name",
            }
        )

        try:
            assert peripheral.get_params() == {"dummy_param": "dummy_value"}
        finally:
            await peripherals.remove(peripheral.get_id(), persisted_data=True)

    async def test_normalizes_legacy_null_display_name_to_empty_string(self, mock_persist_driver):
        peripheral = await peripherals.add(
            {
                "driver": "tests.unit.qtoggleserver.mock.peripherals.MockPeripheral",
                "dummy_param": "dummy_value",
                "name": "legacy_null_display_name",
                "display_name": None,
            }
        )

        try:
            assert peripheral.get_display_name() == ""
            assert peripheral.to_json()["display_name"] == ""
        finally:
            await peripherals.remove(peripheral.get_id(), persisted_data=True)
