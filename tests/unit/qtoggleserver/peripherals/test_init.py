from qtoggleserver import peripherals, persist


class TestAdd:
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
