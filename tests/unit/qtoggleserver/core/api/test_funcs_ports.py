import pytest

from qtoggleserver.conf import settings
from qtoggleserver.core import api as core_api
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.api.funcs import ports as ports_api_funcs


class TestPatchPorts:
    @pytest.fixture(autouse=True)
    def mock_slaves(self, mocker) -> None:
        mocker.patch("qtoggleserver.slaves.devices.get_all", return_value=[])

    async def test_updates_physical_port_attrs(
        self, mock_api_request_maker, mock_bool_port1, mock_persist_driver
    ) -> None:
        request = mock_api_request_maker("PATCH", "/ports", access_level=core_api.ACCESS_LEVEL_ADMIN)
        result = await ports_api_funcs.patch_ports(request, [{"id": "bid1", "tag": "newtag"}])
        assert result is None
        assert await mock_bool_port1.get_attr("tag") == "newtag"

    async def test_removes_virtual_ports_not_in_request(
        self, mock_api_request_maker, mock_vport1, mock_vport2, mock_bool_port1, mock_persist_driver
    ) -> None:
        # vport1 is in the request and should be recreated; vport2 is absent and should be removed
        request = mock_api_request_maker("PATCH", "/ports", access_level=core_api.ACCESS_LEVEL_ADMIN)
        await ports_api_funcs.patch_ports(
            request,
            [
                {"id": "vport1", "virtual": True, "type": "boolean"},
                {"id": "bid1", "tag": "newtag"},
            ],
        )
        assert core_ports.get("vport1") is not None
        assert core_ports.get("vport2") is None

    async def test_preserves_virtual_port_persisted_data(
        self, mock_api_request_maker, mock_vport1, mock_persist_driver, mocker
    ) -> None:
        # Virtual ports must be removed with persisted_data=False so their stored state survives
        spy_remove = mocker.spy(mock_vport1, "remove")
        request = mock_api_request_maker("PATCH", "/ports", access_level=core_api.ACCESS_LEVEL_ADMIN)
        await ports_api_funcs.patch_ports(request, [{"id": "vport1", "virtual": True, "type": "boolean"}])
        spy_remove.assert_called_once_with(persisted_data=False)

    async def test_does_not_reset_physical_ports(
        self, mock_api_request_maker, mock_bool_port1, mock_persist_driver, mocker
    ) -> None:
        # Unlike PUT /ports, PATCH must not reset physical port attributes to their initial state
        spy_reset_all = mocker.patch("qtoggleserver.core.ports.reset")
        spy_reset_port = mocker.spy(mock_bool_port1, "reset")
        request = mock_api_request_maker("PATCH", "/ports", access_level=core_api.ACCESS_LEVEL_ADMIN)
        await ports_api_funcs.patch_ports(request, [{"id": "bid1"}])
        spy_reset_all.assert_not_called()
        spy_reset_port.assert_not_called()

    async def test_ignores_entry_without_id(self, mock_api_request_maker, mock_persist_driver) -> None:
        request = mock_api_request_maker("PATCH", "/ports", access_level=core_api.ACCESS_LEVEL_ADMIN)
        result = await ports_api_funcs.patch_ports(request, [{"tag": "newtag"}])
        assert result is None

    async def test_ignores_unknown_port_id(self, mock_api_request_maker, mock_persist_driver) -> None:
        request = mock_api_request_maker("PATCH", "/ports", access_level=core_api.ACCESS_LEVEL_ADMIN)
        result = await ports_api_funcs.patch_ports(request, [{"id": "nonexistent", "tag": "newtag"}])
        assert result is None

    async def test_no_such_function_when_backup_disabled(self, mock_api_request_maker, mocker) -> None:
        mocker.patch.object(settings.core, "backup_support", False)
        request = mock_api_request_maker("PATCH", "/ports", access_level=core_api.ACCESS_LEVEL_ADMIN)
        with pytest.raises(core_api.APIError, match="no-such-function") as exc_info:
            await ports_api_funcs.patch_ports(request, [])
        assert exc_info.value.status == 404

    async def test_normal_user_permissions(self, mock_api_request_maker) -> None:
        request = mock_api_request_maker("PATCH", "/ports", access_level=core_api.ACCESS_LEVEL_NORMAL)
        with pytest.raises(core_api.APIError, match="forbidden") as exc_info:
            await ports_api_funcs.patch_ports(request, [])
        assert exc_info.value.status == 403

    async def test_viewonly_user_permissions(self, mock_api_request_maker) -> None:
        request = mock_api_request_maker("PATCH", "/ports", access_level=core_api.ACCESS_LEVEL_VIEWONLY)
        with pytest.raises(core_api.APIError, match="forbidden") as exc_info:
            await ports_api_funcs.patch_ports(request, [])
        assert exc_info.value.status == 403

    async def test_anonymous_user_permissions(self, mock_api_request_maker) -> None:
        request = mock_api_request_maker("PATCH", "/ports", access_level=core_api.ACCESS_LEVEL_NONE)
        with pytest.raises(core_api.APIError, match="authentication-required") as exc_info:
            await ports_api_funcs.patch_ports(request, [])
        assert exc_info.value.status == 401


class TestPatchPortValue:
    @pytest.fixture(autouse=True)
    def mock_slaves(self, mocker) -> None:
        mocker.patch("qtoggleserver.slaves.devices.get_all", return_value=[])

    async def test_no_such_port(self, mock_api_request_maker) -> None:
        request = mock_api_request_maker("PATCH", "/ports/nosuch/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        with pytest.raises(core_api.APIError, match="no-such-port") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nosuch", 100)
        assert exc_info.value.status == 404

    async def test_queues_write_via_push_write_and_wait(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        """Should route the write through the write queue (`push_write_and_wait`) rather than writing directly, and
        wait for it to actually complete."""

        mock_num_port1.set_writable(True)
        # Read value already matches the target, so the write is reported as immediately successful (no 202)
        mock_num_port1.set_last_read_value(100)
        spy = mocker.spy(mock_num_port1, "push_write_and_wait")

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        result = await ports_api_funcs.patch_port_value(request, "nid1", 100)

        assert result is None
        spy.assert_called_once_with(100)
        assert mock_num_port1.get_last_written_value() == 100

    async def test_port_timeout_raises_504(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        mock_num_port1.set_writable(True)
        mocker.patch.object(mock_num_port1, "push_write_and_wait", side_effect=core_ports.PortTimeout())

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        with pytest.raises(core_api.APIError, match="port-timeout") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert exc_info.value.status == 504

    async def test_port_error_raises_502(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        mock_num_port1.set_writable(True)
        mocker.patch.object(mock_num_port1, "push_write_and_wait", side_effect=core_ports.PortError("boom"))

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        with pytest.raises(core_api.APIError, match="port-error") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert exc_info.value.status == 502

    async def test_unexpected_error_raises_500(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        mock_num_port1.set_writable(True)
        mocker.patch.object(mock_num_port1, "push_write_and_wait", side_effect=ValueError("oops"))

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        with pytest.raises(core_api.APIError, match="unexpected-error") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert exc_info.value.status == 500

    async def test_unchanged_read_value_returns_202(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        """Should raise APIAccepted (202) if, right after the write completes, the port's read value still doesn't
        reflect the newly written target (e.g. not yet propagated back from hardware)."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_last_read_value(100)

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        with pytest.raises(core_api.APIAccepted):
            await ports_api_funcs.patch_port_value(request, "nid1", 200)

    async def test_disabled_port(self, mock_api_request_maker, mock_num_port1, mock_persist_driver) -> None:
        mock_num_port1.set_writable(True)
        mock_num_port1._enabled = False

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        with pytest.raises(core_api.APIError, match="port-disabled") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert exc_info.value.status == 400

    async def test_read_only_port(self, mock_api_request_maker, mock_num_port1, mock_persist_driver) -> None:
        mock_num_port1.set_writable(False)

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        with pytest.raises(core_api.APIError, match="read-only-port") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert exc_info.value.status == 400
