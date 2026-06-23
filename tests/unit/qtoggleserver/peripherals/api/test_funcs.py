import pytest

from qtoggleserver import peripherals, persist
from qtoggleserver.core import api as core_api
from qtoggleserver.core.ports import BasePort
from qtoggleserver.peripherals.api import funcs as peripherals_api_funcs
from tests.unit.qtoggleserver.mock.peripherals import MockPeripheral


MOCK_PERIPHERAL1_DATA = {
    "driver": "tests.unit.qtoggleserver.mock.peripherals.MockPeripheral",
    "params": {"dummy_param": "dummy_value1"},
    "name": "peripheral1",
    "display_name": "",
    "id": "peripheral1",
    "static": False,
    "enabled": False,
    "force_enabled": None,
    "online": False,
}

MOCK_PERIPHERAL2_DATA = {
    "driver": "tests.unit.qtoggleserver.mock.peripherals.MockPeripheral",
    "params": {"dummy_param": "dummy_value2"},
    "name": "peripheral2",
    "display_name": "",
    "id": "peripheral2",
    "static": False,
    "enabled": False,
    "force_enabled": None,
    "online": False,
}

MOCK_PERIPHERAL3_DATA = {
    "driver": "tests.unit.qtoggleserver.mock.peripherals.MockPeripheral",
    "params": {"dummy_param": "dummy_value3"},
    "name": "peripheral3",
    "display_name": "",
    "id": "peripheral3",
    "static": False,
    "enabled": False,
    "force_enabled": None,
    "online": False,
}


class TestGetPeripherals:
    async def test_ok(self, mock_api_request_maker, mock_peripheral1, mock_peripheral2):
        request = mock_api_request_maker("GET", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_ADMIN)
        result = await peripherals_api_funcs.get_peripherals(request)
        assert result == [MOCK_PERIPHERAL1_DATA, MOCK_PERIPHERAL2_DATA]

    async def test_normal_user_permissions(self, mock_api_request_maker, mock_peripheral1, mock_peripheral2):
        request = mock_api_request_maker("GET", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_NORMAL)
        with pytest.raises(core_api.APIError, match="forbidden") as e:
            await peripherals_api_funcs.get_peripherals(request)
        assert e.value.status == 403

    async def test_viewonly_user_permissions(self, mock_api_request_maker, mock_peripheral1, mock_peripheral2):
        request = mock_api_request_maker("GET", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_VIEWONLY)
        with pytest.raises(core_api.APIError, match="forbidden") as e:
            await peripherals_api_funcs.get_peripherals(request)
        assert e.value.status == 403

    async def test_anonymous_user_permissions(self, mock_api_request_maker, mock_peripheral1, mock_peripheral2):
        request = mock_api_request_maker("GET", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_NONE)
        with pytest.raises(core_api.APIError, match="authentication-required") as e:
            await peripherals_api_funcs.get_peripherals(request)
        assert e.value.status == 401


class TestPostPeripherals:
    async def test_ok_with_name(self, mock_api_request_maker, mock_peripheral1, mocker):
        mock_peripheral2 = MockPeripheral(
            name=MOCK_PERIPHERAL2_DATA["name"],
            dummy_param=MOCK_PERIPHERAL2_DATA["params"]["dummy_param"],
        )

        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")
        payload.pop("id")
        request = mock_api_request_maker("POST", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_ADMIN)

        spy_add = mocker.patch("qtoggleserver.peripherals.add", return_value=mock_peripheral2)
        spy_init_ports = mocker.patch.object(mock_peripheral2, "init_ports")
        result = await peripherals_api_funcs.post_peripherals(request, payload)

        spy_add.assert_called_once_with(payload)
        spy_init_ports.assert_called_once_with()

        assert result == MOCK_PERIPHERAL2_DATA

    async def test_ok_no_name(self, mock_api_request_maker, mock_peripheral1, mocker):
        mock_peripheral2 = MockPeripheral(dummy_param=MOCK_PERIPHERAL2_DATA["params"]["dummy_param"])

        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")
        payload.pop("name")
        payload.pop("id")
        request = mock_api_request_maker("POST", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_ADMIN)

        spy_add = mocker.patch("qtoggleserver.peripherals.add", return_value=mock_peripheral2)
        spy_init_ports = mocker.patch.object(mock_peripheral2, "init_ports")
        result = await peripherals_api_funcs.post_peripherals(request, payload)

        spy_add.assert_called_once_with(payload)
        spy_init_ports.assert_called_once_with()

        assert result.pop("id")
        assert result == dict(payload, name=None, static=False, enabled=False, force_enabled=None, online=False)

    async def test_no_such_driver(self, mock_api_request_maker, mock_peripheral1):
        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")
        payload["driver"] = "does.not.exist"
        request = mock_api_request_maker("POST", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_ADMIN)

        with pytest.raises(core_api.APIError, match="no-such-driver") as e:
            await peripherals_api_funcs.post_peripherals(request, payload)
        assert e.value.status == 404

    async def test_duplicate_peripheral(self, mock_api_request_maker, mock_peripheral1):
        payload = MOCK_PERIPHERAL1_DATA.copy()
        payload.pop("static")
        request = mock_api_request_maker("POST", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_ADMIN)

        with pytest.raises(core_api.APIError, match="duplicate-peripheral") as e:
            await peripherals_api_funcs.post_peripherals(request, payload)
        assert e.value.status == 400

    async def test_display_name_must_be_string(self, mock_api_request_maker, mock_peripheral1):
        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")
        payload["display_name"] = None
        request = mock_api_request_maker("POST", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_ADMIN)

        with pytest.raises(core_api.APIError, match="invalid-field") as e:
            await peripherals_api_funcs.post_peripherals(request, payload)
        assert e.value.status == 400

    async def test_init_ports_failure_removes_peripheral_and_triggers_remove_event(
        self, mock_api_request_maker, mock_peripheral1, mocker
    ):
        mock_peripheral2 = MockPeripheral(
            name=MOCK_PERIPHERAL2_DATA["name"],
            dummy_param=MOCK_PERIPHERAL2_DATA["params"]["dummy_param"],
        )
        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")
        request = mock_api_request_maker("POST", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_ADMIN)

        mocker.patch("qtoggleserver.peripherals.add", return_value=mock_peripheral2)
        mocker.patch.object(mock_peripheral2, "init_ports", side_effect=Exception("init failed"))
        spy_remove = mocker.patch("qtoggleserver.peripherals.remove")
        spy_trigger_add = mocker.patch.object(mock_peripheral2, "trigger_add")
        spy_trigger_remove = mocker.patch.object(mock_peripheral2, "trigger_remove")

        with pytest.raises(core_api.APIError, match="invalid-request") as e:
            await peripherals_api_funcs.post_peripherals(request, payload)

        assert e.value.status == 400
        spy_trigger_add.assert_called_once_with()
        spy_remove.assert_called_once_with(mock_peripheral2.get_id())
        spy_trigger_remove.assert_called_once_with()

    async def test_ok_with_display_name(self, mock_api_request_maker, mock_peripheral1, mocker):
        mock_peripheral2 = MockPeripheral(
            name=MOCK_PERIPHERAL2_DATA["name"],
            display_name="Peripheral Two",
            dummy_param=MOCK_PERIPHERAL2_DATA["params"]["dummy_param"],
        )
        payload = {
            **MOCK_PERIPHERAL2_DATA,
            "display_name": "Peripheral Two",
        }
        payload.pop("static")
        request = mock_api_request_maker("POST", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_ADMIN)

        spy_add = mocker.patch("qtoggleserver.peripherals.add", return_value=mock_peripheral2)
        spy_init_ports = mocker.patch.object(mock_peripheral2, "init_ports")
        result = await peripherals_api_funcs.post_peripherals(request, payload)

        spy_add.assert_called_once_with(payload)
        spy_init_ports.assert_called_once_with()
        assert result["display_name"] == "Peripheral Two"

    async def test_normal_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")
        request = mock_api_request_maker("POST", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_NORMAL)

        with pytest.raises(core_api.APIError, match="forbidden") as e:
            await peripherals_api_funcs.post_peripherals(request, payload)
        assert e.value.status == 403

    async def test_viewonly_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")
        request = mock_api_request_maker("POST", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_VIEWONLY)

        with pytest.raises(core_api.APIError, match="forbidden") as e:
            await peripherals_api_funcs.post_peripherals(request, payload)
        assert e.value.status == 403

    async def test_anonymous_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")
        request = mock_api_request_maker("POST", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_NONE)

        with pytest.raises(core_api.APIError, match="authentication-required") as e:
            await peripherals_api_funcs.post_peripherals(request, payload)
        assert e.value.status == 401


class TestDeletePeripheral:
    async def test_ok(self, mock_api_request_maker, mock_peripheral1, mocker):
        request = mock_api_request_maker(
            "DELETE", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_ADMIN
        )
        spy_cleanup_ports = mocker.patch.object(mock_peripheral1, "cleanup_ports")
        spy_remove = mocker.patch("qtoggleserver.peripherals.remove")
        spy_trigger_remove = mocker.patch.object(mock_peripheral1, "trigger_remove")
        result = await peripherals_api_funcs.delete_peripheral(request, mock_peripheral1.get_id())

        spy_cleanup_ports.assert_called_once_with(persisted_data=True)
        spy_remove.assert_called_once_with(mock_peripheral1.get_id(), persisted_data=True)
        spy_trigger_remove.assert_called_once_with()
        assert result is None

    async def test_normal_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        request = mock_api_request_maker(
            "DELETE", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_NORMAL
        )
        with pytest.raises(core_api.APIError, match="forbidden") as e:
            await peripherals_api_funcs.delete_peripheral(request, mock_peripheral1.get_id())
        assert e.value.status == 403

    async def test_viewonly_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        request = mock_api_request_maker(
            "DELETE", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_VIEWONLY
        )
        with pytest.raises(core_api.APIError, match="forbidden") as e:
            await peripherals_api_funcs.delete_peripheral(request, mock_peripheral1.get_id())
        assert e.value.status == 403

    async def test_anonymous_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        request = mock_api_request_maker(
            "DELETE", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_NONE
        )
        with pytest.raises(core_api.APIError, match="authentication-required") as e:
            await peripherals_api_funcs.delete_peripheral(request, mock_peripheral1.get_id())
        assert e.value.status == 401


class TestPatchPeripheral:
    async def test_ok(self, mock_api_request_maker, mock_peripheral1, mocker):
        mock_peripheral2 = MockPeripheral(
            name=MOCK_PERIPHERAL2_DATA["name"],
            dummy_param=MOCK_PERIPHERAL2_DATA["params"]["dummy_param"],
        )
        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")

        request = mock_api_request_maker(
            "PATCH", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_ADMIN
        )
        spy_cleanup_ports = mocker.patch.object(mock_peripheral1, "cleanup_ports")
        spy_remove = mocker.patch("qtoggleserver.peripherals.remove")
        spy_add = mocker.patch("qtoggleserver.peripherals.add", return_value=mock_peripheral2)
        spy_init_ports = mocker.patch.object(mock_peripheral2, "init_ports")
        spy_trigger_update = mocker.patch.object(mock_peripheral2, "trigger_update")

        result = await peripherals_api_funcs.patch_peripheral(request, mock_peripheral1.get_id(), payload)

        spy_cleanup_ports.assert_called_once_with(persisted_data=False)
        spy_remove.assert_called_once_with(mock_peripheral1.get_id(), persisted_data=False)
        spy_add.assert_called_once_with(payload)
        spy_init_ports.assert_called_once_with()
        spy_trigger_update.assert_called_once_with()
        assert result == MOCK_PERIPHERAL2_DATA

    async def test_preserves_persisted_data(self, mock_api_request_maker, mock_peripheral1, mocker):
        # cleanup_ports and remove must both be called with persisted_data=False when params change
        payload = MOCK_PERIPHERAL1_DATA.copy()
        payload.pop("static")
        # Change params to trigger structural change path
        payload["params"] = {"dummy_param": "new_value"}

        request = mock_api_request_maker(
            "PATCH", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_ADMIN
        )
        spy_cleanup_ports = mocker.patch.object(mock_peripheral1, "cleanup_ports")
        spy_remove = mocker.patch("qtoggleserver.peripherals.remove")
        mocker.patch("qtoggleserver.peripherals.add", return_value=mock_peripheral1)
        mocker.patch.object(mock_peripheral1, "init_ports")

        await peripherals_api_funcs.patch_peripheral(request, mock_peripheral1.get_id(), payload)

        spy_cleanup_ports.assert_called_once_with(persisted_data=False)
        spy_remove.assert_called_once_with(mock_peripheral1.get_id(), persisted_data=False)

    async def test_display_name_change_no_removal(self, mock_api_request_maker, mock_peripheral1, mocker):
        # Changing display_name should not trigger removal/re-add but should persist changes
        payload = {
            "driver": mock_peripheral1.get_driver(),
            "display_name": "New Display Name",
        }

        request = mock_api_request_maker(
            "PATCH", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_ADMIN
        )
        spy_cleanup_ports = mocker.patch.object(mock_peripheral1, "cleanup_ports")
        spy_remove = mocker.patch("qtoggleserver.peripherals.remove")
        spy_update = mocker.patch("qtoggleserver.peripherals.update")
        spy_trigger_update = mocker.patch.object(mock_peripheral1, "trigger_update")

        result = await peripherals_api_funcs.patch_peripheral(request, mock_peripheral1.get_id(), payload)

        # cleanup_ports and remove should NOT be called
        spy_cleanup_ports.assert_not_called()
        spy_remove.assert_not_called()
        # But update should be called to persist changes
        spy_update.assert_called_once_with(mock_peripheral1)
        # And trigger_update should be called
        spy_trigger_update.assert_called_once()
        # And display_name should be updated
        assert result["display_name"] == "New Display Name"

    async def test_force_enabled_change_triggers_removal(self, mock_api_request_maker, mock_peripheral1, mocker):
        # Changing force_enabled should trigger removal/re-add (structural change)
        payload = {
            "driver": mock_peripheral1.get_driver(),
            "force_enabled": True,
        }

        request = mock_api_request_maker(
            "PATCH", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_ADMIN
        )
        spy_cleanup_ports = mocker.patch.object(mock_peripheral1, "cleanup_ports")
        spy_remove = mocker.patch("qtoggleserver.peripherals.remove")
        mocker.patch("qtoggleserver.peripherals.add", return_value=mock_peripheral1)
        mocker.patch.object(mock_peripheral1, "init_ports")

        await peripherals_api_funcs.patch_peripheral(request, mock_peripheral1.get_id(), payload)

        # cleanup_ports and remove MUST be called because force_enabled is structural
        spy_cleanup_ports.assert_called_once_with(persisted_data=False)
        spy_remove.assert_called_once_with(mock_peripheral1.get_id(), persisted_data=False)

    async def test_driver_change_triggers_removal(self, mock_api_request_maker, mock_peripheral1, mocker):
        # Changing driver should trigger removal/re-add (structural change)
        payload = {
            "driver": "different.driver.class",
        }

        request = mock_api_request_maker(
            "PATCH", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_ADMIN
        )
        spy_cleanup_ports = mocker.patch.object(mock_peripheral1, "cleanup_ports")
        spy_remove = mocker.patch("qtoggleserver.peripherals.remove")
        mocker.patch("qtoggleserver.peripherals.add", return_value=mock_peripheral1)
        mocker.patch.object(mock_peripheral1, "init_ports")

        await peripherals_api_funcs.patch_peripheral(request, mock_peripheral1.get_id(), payload)

        # cleanup_ports and remove MUST be called because driver is structural
        spy_cleanup_ports.assert_called_once_with(persisted_data=False)
        spy_remove.assert_called_once_with(mock_peripheral1.get_id(), persisted_data=False)

    async def test_no_such_peripheral(self, mock_api_request_maker, mock_peripheral1):
        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")
        request = mock_api_request_maker(
            "PATCH", "/api/peripherals/nonexistent", access_level=core_api.ACCESS_LEVEL_ADMIN
        )
        with pytest.raises(core_api.APIError, match="no-such-peripheral") as e:
            await peripherals_api_funcs.patch_peripheral(request, "nonexistent", payload)
        assert e.value.status == 404

    async def test_static_peripheral_not_removable(self, mock_api_request_maker, mock_peripheral1, mocker):
        mocker.patch.object(mock_peripheral1, "is_static", return_value=True)
        payload = MOCK_PERIPHERAL1_DATA.copy()
        payload.pop("static")
        request = mock_api_request_maker(
            "PATCH", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_ADMIN
        )
        with pytest.raises(core_api.APIError, match="peripheral-not-removable") as e:
            await peripherals_api_funcs.patch_peripheral(request, mock_peripheral1.get_id(), payload)
        assert e.value.status == 400

    async def test_no_such_driver(self, mock_api_request_maker, mock_peripheral1, mocker):
        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")
        payload["driver"] = "does.not.exist"
        request = mock_api_request_maker(
            "PATCH", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_ADMIN
        )
        mocker.patch.object(mock_peripheral1, "cleanup_ports")
        mocker.patch("qtoggleserver.peripherals.remove")
        mocker.patch("qtoggleserver.peripherals.add", side_effect=peripherals.NoSuchDriver("does.not.exist"))
        with pytest.raises(core_api.APIError, match="no-such-driver") as e:
            await peripherals_api_funcs.patch_peripheral(request, mock_peripheral1.get_id(), payload)
        assert e.value.status == 404

    async def test_add_failure_restores_old_peripheral(self, mock_api_request_maker, mock_peripheral1, mocker):
        # When peripherals.add() fails, the old peripheral should be re-added
        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")
        mocker.patch.object(mock_peripheral1, "cleanup_ports")
        mocker.patch("qtoggleserver.peripherals.remove")

        restored_peripheral = MockPeripheral(
            name=MOCK_PERIPHERAL1_DATA["name"],
            dummy_param=MOCK_PERIPHERAL1_DATA["params"]["dummy_param"],
        )
        # First call raises, second call (restore) succeeds
        mock_add = mocker.patch(
            "qtoggleserver.peripherals.add",
            side_effect=[peripherals.NoSuchDriver("bad.driver"), restored_peripheral],
        )
        spy_init_ports = mocker.patch.object(restored_peripheral, "init_ports")

        request = mock_api_request_maker(
            "PATCH", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_ADMIN
        )
        with pytest.raises(core_api.APIError, match="no-such-driver"):
            await peripherals_api_funcs.patch_peripheral(request, mock_peripheral1.get_id(), payload)

        # add() called twice: once with new args, once to restore old args
        assert mock_add.call_count == 2
        restore_call_args = mock_add.call_args_list[1][0][0]
        assert restore_call_args["driver"] == mock_peripheral1.get_driver()
        assert restore_call_args["name"] == mock_peripheral1.get_name()
        assert restore_call_args["params"] == mock_peripheral1.get_params()
        spy_init_ports.assert_called_once()

    async def test_init_ports_failure_disables_new_peripheral(self, mock_api_request_maker, mock_peripheral1, mocker):
        mock_peripheral2 = MockPeripheral(
            name=MOCK_PERIPHERAL2_DATA["name"],
            dummy_param=MOCK_PERIPHERAL2_DATA["params"]["dummy_param"],
        )
        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")

        request = mock_api_request_maker(
            "PATCH", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_ADMIN
        )
        mocker.patch.object(mock_peripheral1, "cleanup_ports")
        spy_remove = mocker.patch("qtoggleserver.peripherals.remove")
        mocker.patch("qtoggleserver.peripherals.add", return_value=mock_peripheral2)
        mocker.patch.object(mock_peripheral2, "init_ports", side_effect=Exception("init failed"))
        spy_set_force_enabled = mocker.patch.object(mock_peripheral2, "set_force_enabled")
        spy_disable = mocker.patch.object(mock_peripheral2, "disable")

        with pytest.raises(core_api.APIError, match="invalid-request") as e:
            await peripherals_api_funcs.patch_peripheral(request, mock_peripheral1.get_id(), payload)
        assert e.value.status == 400
        spy_remove.assert_called_once_with(mock_peripheral1.get_id(), persisted_data=False)
        spy_set_force_enabled.assert_called_once_with(False)
        spy_disable.assert_called_once_with()

    async def test_normal_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")
        request = mock_api_request_maker(
            "PATCH", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_NORMAL
        )
        with pytest.raises(core_api.APIError, match="forbidden") as e:
            await peripherals_api_funcs.patch_peripheral(request, mock_peripheral1.get_id(), payload)
        assert e.value.status == 403

    async def test_viewonly_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")
        request = mock_api_request_maker(
            "PATCH", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_VIEWONLY
        )
        with pytest.raises(core_api.APIError, match="forbidden") as e:
            await peripherals_api_funcs.patch_peripheral(request, mock_peripheral1.get_id(), payload)
        assert e.value.status == 403

    async def test_anonymous_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")
        request = mock_api_request_maker(
            "PATCH", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_NONE
        )
        with pytest.raises(core_api.APIError, match="authentication-required") as e:
            await peripherals_api_funcs.patch_peripheral(request, mock_peripheral1.get_id(), payload)
        assert e.value.status == 401

    async def test_rename_migrates_port_data(self, mock_peripheral1, mock_persist_driver, mocker):
        from qtoggleserver.peripherals.api.funcs import _migrate_peripheral_rename

        await persist.replace(BasePort.PERSIST_COLLECTION, "peripheral1.id1", {"id": "peripheral1.id1", "tag": "t1"})
        await persist.replace(BasePort.PERSIST_COLLECTION, "peripheral1.id2", {"id": "peripheral1.id2", "tag": "t2"})

        mock_port1 = mocker.MagicMock()
        mock_port1.get_id.return_value = "peripheral1.id1"
        mock_port1.get_initial_id.return_value = "id1"
        mock_port2 = mocker.MagicMock()
        mock_port2.get_id.return_value = "peripheral1.id2"
        mock_port2.get_initial_id.return_value = "id2"
        mocker.patch.object(mock_peripheral1, "get_ports", return_value=[mock_port1, mock_port2])

        await _migrate_peripheral_rename(mock_peripheral1, "peripheral2")

        assert await persist.get(BasePort.PERSIST_COLLECTION, "peripheral2.id1") == {
            "id": "peripheral2.id1",
            "tag": "t1",
        }
        assert await persist.get(BasePort.PERSIST_COLLECTION, "peripheral2.id2") == {
            "id": "peripheral2.id2",
            "tag": "t2",
        }
        assert await persist.get(BasePort.PERSIST_COLLECTION, "peripheral1.id1") is None
        assert await persist.get(BasePort.PERSIST_COLLECTION, "peripheral1.id2") is None

    async def test_rename_removes_old_peripheral_entry(self, mock_peripheral1, mock_persist_driver, mocker):
        from qtoggleserver.peripherals.api.funcs import _migrate_peripheral_rename

        mocker.patch.object(mock_peripheral1, "get_ports", return_value=[])
        await persist.replace("peripherals", mock_peripheral1.get_id(), {"id": mock_peripheral1.get_id()})
        assert await persist.get("peripherals", mock_peripheral1.get_id()) is not None

        await _migrate_peripheral_rename(mock_peripheral1, "peripheral2")

        assert await persist.get("peripherals", mock_peripheral1.get_id()) is None

    async def test_rename_same_name_noop(self, mock_peripheral1, mock_persist_driver, mocker):
        from qtoggleserver.peripherals.api.funcs import _migrate_peripheral_rename

        await persist.replace(BasePort.PERSIST_COLLECTION, "peripheral1.id1", {"id": "peripheral1.id1", "tag": "t1"})
        mock_port = mocker.MagicMock()
        mock_port.get_id.return_value = "peripheral1.id1"
        mock_port.get_initial_id.return_value = "id1"
        mocker.patch.object(mock_peripheral1, "get_ports", return_value=[mock_port])

        await _migrate_peripheral_rename(mock_peripheral1, "peripheral1")

        # Port data should be untouched when old and new IDs are the same
        assert await persist.get(BasePort.PERSIST_COLLECTION, "peripheral1.id1") == {
            "id": "peripheral1.id1",
            "tag": "t1",
        }

    async def test_rename_not_called_when_name_unchanged(self, mock_api_request_maker, mock_peripheral1, mocker):
        spy_migrate = mocker.patch("qtoggleserver.peripherals.api.funcs._migrate_peripheral_rename")
        payload = MOCK_PERIPHERAL1_DATA.copy()
        payload.pop("static")
        request = mock_api_request_maker(
            "PATCH", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_ADMIN
        )
        mocker.patch.object(mock_peripheral1, "cleanup_ports")
        mocker.patch("qtoggleserver.peripherals.remove")
        mocker.patch("qtoggleserver.peripherals.add", return_value=mock_peripheral1)
        mocker.patch.object(mock_peripheral1, "init_ports")

        await peripherals_api_funcs.patch_peripheral(request, mock_peripheral1.get_id(), payload)

        spy_migrate.assert_not_called()

    async def test_rename_called_when_name_changes(self, mock_api_request_maker, mock_peripheral1, mocker):
        spy_migrate = mocker.patch("qtoggleserver.peripherals.api.funcs._migrate_peripheral_rename")
        mock_peripheral2 = MockPeripheral(
            name=MOCK_PERIPHERAL2_DATA["name"],
            dummy_param=MOCK_PERIPHERAL2_DATA["params"]["dummy_param"],
        )
        payload = MOCK_PERIPHERAL2_DATA.copy()
        payload.pop("static")
        request = mock_api_request_maker(
            "PATCH", f"/api/peripherals/{mock_peripheral1.get_id()}", access_level=core_api.ACCESS_LEVEL_ADMIN
        )
        mocker.patch.object(mock_peripheral1, "cleanup_ports")
        mocker.patch("qtoggleserver.peripherals.remove")
        mocker.patch("qtoggleserver.peripherals.add", return_value=mock_peripheral2)
        mocker.patch.object(mock_peripheral2, "init_ports")

        await peripherals_api_funcs.patch_peripheral(request, mock_peripheral1.get_id(), payload)

        spy_migrate.assert_called_once_with(mock_peripheral1, "peripheral2")


class TestPutPeripherals:
    async def test_ok(self, mock_api_request_maker, mock_peripheral1, mocker):
        mock_peripheral2 = MockPeripheral(
            name=MOCK_PERIPHERAL2_DATA["name"],
            dummy_param=MOCK_PERIPHERAL2_DATA["params"]["dummy_param"],
        )
        mock_peripheral3 = MockPeripheral(
            name=MOCK_PERIPHERAL3_DATA["name"],
            dummy_param=MOCK_PERIPHERAL3_DATA["params"]["dummy_param"],
        )
        payload2 = MOCK_PERIPHERAL2_DATA.copy()
        payload3 = MOCK_PERIPHERAL3_DATA.copy()
        payload2.pop("static")
        payload3.pop("static")

        request = mock_api_request_maker("PUT", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_ADMIN)
        spy_cleanup_ports = mocker.patch.object(mock_peripheral1, "cleanup_ports")
        spy_remove = mocker.patch("qtoggleserver.peripherals.remove")
        spy_add = mocker.patch("qtoggleserver.peripherals.add", side_effect=[mock_peripheral2, mock_peripheral3])
        spy_init_ports2 = mocker.patch.object(mock_peripheral2, "init_ports")
        spy_init_ports3 = mocker.patch.object(mock_peripheral3, "init_ports")
        spy_trigger_remove = mocker.patch.object(mock_peripheral1, "trigger_remove")
        spy_trigger_add2 = mocker.patch.object(mock_peripheral2, "trigger_add")
        spy_trigger_add3 = mocker.patch.object(mock_peripheral3, "trigger_add")

        result = await peripherals_api_funcs.put_peripherals(request, [payload2, payload3])

        spy_cleanup_ports.assert_called_once_with(persisted_data=True)
        spy_remove.assert_called_once_with(mock_peripheral1.get_id(), persisted_data=True)
        spy_add.assert_has_calls([mocker.call(payload2), mocker.call(payload3)])
        spy_init_ports2.assert_called_once_with()
        spy_init_ports3.assert_called_once_with()
        spy_trigger_remove.assert_called_once_with()
        spy_trigger_add2.assert_called_once_with()
        spy_trigger_add3.assert_called_once_with()

        assert result is None

    async def test_init_ports_failure_disables_failing_peripheral(
        self, mock_api_request_maker, mock_peripheral1, mocker
    ):
        failing_peripheral = MockPeripheral(
            name=MOCK_PERIPHERAL2_DATA["name"],
            dummy_param=MOCK_PERIPHERAL2_DATA["params"]["dummy_param"],
        )
        healthy_peripheral = MockPeripheral(
            name=MOCK_PERIPHERAL3_DATA["name"],
            dummy_param=MOCK_PERIPHERAL3_DATA["params"]["dummy_param"],
        )
        payload2 = MOCK_PERIPHERAL2_DATA.copy()
        payload3 = MOCK_PERIPHERAL3_DATA.copy()
        payload2.pop("static")
        payload3.pop("static")

        request = mock_api_request_maker("PUT", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_ADMIN)
        mocker.patch.object(mock_peripheral1, "cleanup_ports")
        mocker.patch("qtoggleserver.peripherals.remove")
        mocker.patch("qtoggleserver.peripherals.add", side_effect=[failing_peripheral, healthy_peripheral])
        mocker.patch.object(failing_peripheral, "init_ports", side_effect=Exception("init failed"))
        spy_init_ports_healthy = mocker.patch.object(healthy_peripheral, "init_ports")
        spy_set_force_enabled = mocker.patch.object(failing_peripheral, "set_force_enabled")
        spy_disable = mocker.patch.object(failing_peripheral, "disable")

        result = await peripherals_api_funcs.put_peripherals(request, [payload2, payload3])

        spy_set_force_enabled.assert_called_once_with(False)
        spy_disable.assert_called_once_with()
        spy_init_ports_healthy.assert_called_once_with()
        assert result is None

    async def test_normal_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        request = mock_api_request_maker("PUT", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_NORMAL)
        with pytest.raises(core_api.APIError, match="forbidden") as e:
            await peripherals_api_funcs.put_peripherals(request, [])
        assert e.value.status == 403

    async def test_viewonly_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        request = mock_api_request_maker("PUT", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_VIEWONLY)
        with pytest.raises(core_api.APIError, match="forbidden") as e:
            await peripherals_api_funcs.put_peripherals(request, [])
        assert e.value.status == 403

    async def test_anonymous_user_permissions(self, mock_api_request_maker, mock_peripheral1):
        request = mock_api_request_maker("PUT", "/api/peripherals", access_level=core_api.ACCESS_LEVEL_NONE)
        with pytest.raises(core_api.APIError, match="authentication-required") as e:
            await peripherals_api_funcs.put_peripherals(request, [])
        assert e.value.status == 401
