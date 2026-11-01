import asyncio
import gc

import pytest

from qtoggleserver.conf import settings
from qtoggleserver.core import api as core_api
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core import vports as core_vports
from qtoggleserver.core.api.funcs import ports as ports_api_funcs
from qtoggleserver.slaves import devices as slaves_devices
from qtoggleserver.slaves.devices import Slave


class TestPatchPorts:
    @pytest.fixture(autouse=True)
    def mock_slaves(self, mocker) -> None:
        mocker.patch.dict("qtoggleserver.slaves.devices._slaves_by_name", {}, clear=True)

    async def test_updates_physical_port_attrs(
        self, mock_api_request_maker, mock_bool_port1, mock_persist_driver
    ) -> None:
        request = mock_api_request_maker("PATCH", "/ports", access_level=core_api.ACCESS_LEVEL_ADMIN)
        result = await ports_api_funcs.patch_ports(request, [{"id": "bid1", "tag": "newtag"}])
        assert result is None
        assert await mock_bool_port1.get_attr("tag") == "newtag"

    async def test_queues_valid_value(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        mock_num_port1.set_writable(True)
        spy_push_write = mocker.spy(mock_num_port1, "push_write")
        spy_write = mocker.spy(mock_num_port1, "transform_and_write_value")

        request = mock_api_request_maker("PATCH", "/ports", access_level=core_api.ACCESS_LEVEL_ADMIN)
        await ports_api_funcs.patch_ports(request, [{"id": "nid1", "value": 0.3}])

        spy_push_write.assert_called_once_with(0.3)
        await asyncio.sleep(0.1)
        spy_write.assert_called_once_with(0.3)

    @pytest.mark.parametrize("value", [150, -1, True, 0.35])
    async def test_ignores_invalid_value(
        self, value, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        mock_num_port1.set_writable(True)
        mock_num_port1._min = 0
        mock_num_port1._max = 100
        mock_num_port1._step = 0.1
        spy_write = mocker.spy(mock_num_port1, "transform_and_write_value")

        request = mock_api_request_maker("PATCH", "/ports", access_level=core_api.ACCESS_LEVEL_ADMIN)
        await ports_api_funcs.patch_ports(request, [{"id": "nid1", "value": value}])

        await asyncio.sleep(0.1)
        spy_write.assert_not_called()

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


class TestPatchPort:
    async def test_rejects_own_id_in_transform(self, mock_api_request_maker, mock_num_port1, mock_persist_driver):
        """Should reject a transform that refers to the port's own id rather than `$`."""

        request = mock_api_request_maker("PATCH", "/ports/nid1", access_level=core_api.ACCESS_LEVEL_ADMIN)
        with pytest.raises(core_api.APIError) as exc_info:
            await ports_api_funcs.patch_port(request, "nid1", {"transform_read": "MUL($nid1, 10)"})

        assert exc_info.value.status == 400
        assert exc_info.value.code == "invalid-field"
        assert exc_info.value.params["details"]["reason"] == "transform-not-supported"
        assert await mock_num_port1.get_attr("transform_read") == ""


class TestPatchPortValue:
    @pytest.fixture(autouse=True)
    def mock_slaves(self, mocker) -> None:
        mocker.patch.dict("qtoggleserver.slaves.devices._slaves_by_name", {}, clear=True)

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
        spy = mocker.spy(mock_num_port1, "push_write_and_wait")

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        result = await ports_api_funcs.patch_port_value(request, "nid1", 100)

        assert result is None
        spy.assert_called_once_with(100)
        assert mock_num_port1.get_last_written_value() == 100

    async def test_accepts_float_value_on_step(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver
    ) -> None:
        mock_num_port1.set_writable(True)
        mock_num_port1._min = 0
        mock_num_port1._step = 0.1

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        await ports_api_funcs.patch_port_value(request, "nid1", 0.3)
        assert mock_num_port1.get_last_written_value() == 0.3

    async def test_rejects_float_value_off_step(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver
    ) -> None:
        mock_num_port1.set_writable(True)
        mock_num_port1._min = 0
        mock_num_port1._step = 0.1

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        with pytest.raises(core_api.APIError, match="invalid-value"):
            await ports_api_funcs.patch_port_value(request, "nid1", 0.35)

    async def test_port_timeout_raises_500(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        mock_num_port1.set_writable(True)
        mocker.patch.object(mock_num_port1, "push_write_and_wait", side_effect=core_ports.PortTimeout())

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        with pytest.raises(core_api.APIError, match="port-timeout") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert exc_info.value.status == 500

    async def test_port_error_raises_500(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        mock_num_port1.set_writable(True)
        mocker.patch.object(mock_num_port1, "push_write_and_wait", side_effect=core_ports.PortError("boom"))

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        with pytest.raises(core_api.APIError, match="port-error") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert exc_info.value.status == 500

    async def test_port_disabled_raises_400(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        """Should map a write dropped by a concurrent disable to 400 port-disabled, as the spec requires."""
        mock_num_port1.set_writable(True)
        mocker.patch.object(mock_num_port1, "push_write_and_wait", side_effect=core_ports.PortDisabled())

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        with pytest.raises(core_api.APIError, match="port-disabled") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert exc_info.value.status == 400

    async def test_unexpected_error_raises_500(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        mock_num_port1.set_writable(True)
        mocker.patch.object(mock_num_port1, "push_write_and_wait", side_effect=ValueError("oops"))

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        with pytest.raises(core_api.APIError, match="unexpected-error") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert exc_info.value.status == 500

    async def test_succeeds_even_if_read_value_not_updated(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver
    ) -> None:
        """Should return normally once the write completes, even if the port's read value doesn't (yet) reflect the
        newly written target (e.g. not yet propagated back from hardware)."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_read_value(100)

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        result = await ports_api_funcs.patch_port_value(request, "nid1", 200)
        assert result is None

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


@pytest.mark.parametrize(
    "value, min_, step, expected",
    [
        (0.3, 0, 0.1, True),
        (0.7, 0.1, 0.3, True),
        (0.35, 0, 0.1, False),
        (21.5, 10, 0.5, True),
        (5, 1, 2, True),
        (4, 1, 2, False),
        (-0.3, -1, 0.1, True),
        (1e6 + 0.1, 0, 0.1, True),
        (0.35, None, 0.1, True),
        (0.35, 0, None, True),
        (0.35, 0, 0, True),
    ],
)
def test_is_on_step(value, min_, step, expected) -> None:
    assert ports_api_funcs._is_on_step(value, min_, step) is expected


class TestPatchPortValueTimeout:
    @pytest.fixture(autouse=True)
    def mock_slaves(self, mocker) -> None:
        mocker.patch.dict("qtoggleserver.slaves.devices._slaves_by_name", {}, clear=True)

    async def test_non_integer_timeout_raises_invalid_field(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver
    ) -> None:
        mock_num_port1.set_writable(True)

        request = mock_api_request_maker(
            "PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL, query={"timeout": "abc"}
        )
        with pytest.raises(core_api.APIError, match="invalid-field") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert exc_info.value.status == 400
        assert exc_info.value.params["field"] == "timeout"

    async def test_negative_timeout_raises_invalid_field(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver
    ) -> None:
        mock_num_port1.set_writable(True)

        request = mock_api_request_maker(
            "PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL, query={"timeout": "-1"}
        )
        with pytest.raises(core_api.APIError, match="invalid-field") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert exc_info.value.status == 400
        assert exc_info.value.params["field"] == "timeout"

    async def test_too_large_timeout_raises_invalid_field(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver
    ) -> None:
        mock_num_port1.set_writable(True)

        request = mock_api_request_maker(
            "PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL, query={"timeout": "3601"}
        )
        with pytest.raises(core_api.APIError, match="invalid-field") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert exc_info.value.status == 400
        assert exc_info.value.params["field"] == "timeout"

    @pytest.mark.parametrize("timeout", ["nan", "NaN", "inf", "-inf"])
    async def test_non_finite_timeout_raises_invalid_field(
        self, timeout, mock_api_request_maker, mock_num_port1, mock_persist_driver
    ) -> None:
        mock_num_port1.set_writable(True)

        request = mock_api_request_maker(
            "PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL, query={"timeout": timeout}
        )
        with pytest.raises(core_api.APIError, match="invalid-field") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert exc_info.value.status == 400
        assert exc_info.value.params["field"] == "timeout"

    async def test_no_timeout_does_not_wait_for_confirmation(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        """Without a `timeout` query argument, the request must be responded as soon as the write completes,
        without waiting for the read value to catch up."""

        mock_num_port1.set_writable(True)
        spy = mocker.spy(mock_num_port1, "wait_for_read_value")

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        result = await ports_api_funcs.patch_port_value(request, "nid1", 100)

        assert result is None
        spy.assert_not_called()

    async def test_returns_immediately_if_value_already_matches(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        mock_num_port1.set_writable(True)
        mock_num_port1.set_read_value(100)
        spy = mocker.spy(mock_num_port1, "wait_for_read_value")

        request = mock_api_request_maker(
            "PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL, query={"timeout": "5"}
        )
        result = await ports_api_funcs.patch_port_value(request, "nid1", 100)

        assert result is None
        spy.assert_called_once()

    async def test_waits_and_succeeds_once_matching_value_is_read(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver
    ) -> None:
        mock_num_port1.set_writable(True)
        mock_num_port1.set_read_value(0)

        async def delayed_read() -> None:
            await asyncio.sleep(0.01)
            mock_num_port1.set_read_value(100)

        task = asyncio.create_task(delayed_read())

        request = mock_api_request_maker(
            "PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL, query={"timeout": "5"}
        )
        try:
            result = await ports_api_funcs.patch_port_value(request, "nid1", 100)
        finally:
            await task

        assert result is None

    async def test_raises_value_timeout_if_value_never_matches(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver
    ) -> None:
        mock_num_port1.set_writable(True)
        mock_num_port1.set_read_value(0)

        request = mock_api_request_maker(
            "PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL, query={"timeout": "0.02"}
        )
        with pytest.raises(core_api.APIError, match="value-timeout") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert exc_info.value.status == 500

    async def test_erroneous_write_skips_confirmation(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        """An erroneous write must be responded as usual, without waiting for any confirmation."""

        mock_num_port1.set_writable(True)
        mocker.patch.object(mock_num_port1, "push_write_and_wait", side_effect=core_ports.PortTimeout())
        spy = mocker.spy(mock_num_port1, "wait_for_read_value")

        request = mock_api_request_maker(
            "PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL, query={"timeout": "5"}
        )
        with pytest.raises(core_api.APIError, match="port-timeout") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert exc_info.value.status == 500
        spy.assert_not_called()

    async def test_timeout_covers_slow_write(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        """Should respond with `value-timeout` once the timeout expires during the write, and still write the
        value afterwards."""

        mock_num_port1.set_writable(True)
        mock_num_port1._write_queue.clear()

        async def slow_write(value: int) -> None:
            await asyncio.sleep(0.2)

        mocker.patch.object(mock_num_port1, "write_value", new=slow_write)

        request = mock_api_request_maker(
            "PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL, query={"timeout": "0.05"}
        )
        start = asyncio.get_running_loop().time()
        with pytest.raises(core_api.APIError, match="value-timeout") as exc_info:
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert exc_info.value.status == 500
        assert asyncio.get_running_loop().time() - start < 0.15

        await asyncio.sleep(0.3)
        assert mock_num_port1.get_last_written_value() == 100

    async def test_timeout_covers_queue_wait(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        """Should respond with `value-timeout` while the value still waits in the queue, and write it afterwards."""

        mock_num_port1.set_writable(True)
        mock_num_port1._write_queue.clear()
        written = []

        async def slow_write(value: int) -> None:
            await asyncio.sleep(0.2)
            written.append(value)

        mocker.patch.object(mock_num_port1, "write_value", new=slow_write)
        mock_num_port1.push_write(1)
        await asyncio.sleep(0.05)  # let the write loop start writing the first value

        request = mock_api_request_maker(
            "PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL, query={"timeout": "0.05"}
        )
        with pytest.raises(core_api.APIError, match="value-timeout"):
            await ports_api_funcs.patch_port_value(request, "nid1", 100)
        assert written == []

        await asyncio.sleep(0.5)
        assert written == [1, 100]

    async def test_read_wait_gets_remaining_time(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        """Should count the time spent writing against the timeout, leaving only the rest for the read wait."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_read_value(0)
        mocker.patch.object(mock_num_port1, "push_write_and_wait", new=lambda value: asyncio.sleep(0.1))
        spy = mocker.spy(mock_num_port1, "wait_for_read_value")

        request = mock_api_request_maker(
            "PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL, query={"timeout": "0.3"}
        )
        with pytest.raises(core_api.APIError, match="value-timeout"):
            await ports_api_funcs.patch_port_value(request, "nid1", 100)

        remaining = spy.call_args.kwargs["timeout"]
        assert 0 < remaining <= 0.2

    async def test_no_timeout_waits_for_slow_write(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        """Should wait for a slow write to complete when no `timeout` is given."""

        mock_num_port1.set_writable(True)
        mock_num_port1._write_queue.clear()

        async def slow_write(value: int) -> None:
            await asyncio.sleep(0.1)

        mocker.patch.object(mock_num_port1, "write_value", new=slow_write)

        request = mock_api_request_maker("PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL)
        await ports_api_funcs.patch_port_value(request, "nid1", 100)

        assert mock_num_port1.get_last_written_value() == 100

    async def test_late_write_failure_not_reported(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        """Should not leave an unhandled exception behind when a write fails after its request has timed out."""

        mock_num_port1.set_writable(True)
        mock_num_port1._write_queue.clear()
        loop_errors = []
        loop = asyncio.get_running_loop()
        mocker.patch.object(loop, "call_exception_handler", side_effect=loop_errors.append)

        async def failing_write(value: int) -> None:
            await asyncio.sleep(0.1)
            raise core_ports.PortError("write failed")

        mocker.patch.object(mock_num_port1, "write_value", new=failing_write)

        request = mock_api_request_maker(
            "PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL, query={"timeout": "0.03"}
        )
        with pytest.raises(core_api.APIError, match="value-timeout"):
            await ports_api_funcs.patch_port_value(request, "nid1", 100)

        await asyncio.sleep(0.2)
        gc.collect()
        assert loop_errors == []

    async def test_driver_timeout_error_is_not_value_timeout(
        self, mock_api_request_maker, mock_num_port1, mock_persist_driver, mocker
    ) -> None:
        """Should not mistake a `TimeoutError` raised by the write itself for an expired request timeout."""

        mock_num_port1.set_writable(True)
        mocker.patch.object(mock_num_port1, "push_write_and_wait", side_effect=TimeoutError())

        request = mock_api_request_maker(
            "PATCH", "/ports/nid1/value", access_level=core_api.ACCESS_LEVEL_NORMAL, query={"timeout": "5"}
        )
        with pytest.raises(core_api.APIError, match="unexpected-error"):
            await ports_api_funcs.patch_port_value(request, "nid1", 100)


@pytest.fixture
async def slave1(mocker):
    """Register a slave named `slave1`, which reserves the `slave1.` port id prefix."""
    mocker.patch.dict("qtoggleserver.slaves.devices._slaves_by_name", {}, clear=True)
    slave = Slave(name="slave1", scheme="http", host="192.168.1.2", port=80, path="", admin_password="")
    slaves_devices._slaves_by_name["slave1"] = slave

    return slave


@pytest.fixture
async def vport_maker(mock_persist_driver, mocker):
    """Add virtual ports through the API and clean them up when the test ends."""
    mocker.patch("asyncio.Lock")
    created = []

    async def make(port_id: str) -> core_ports.BasePort:
        port = await ports_api_funcs.add_virtual_port({"id": port_id, "type": "boolean"})
        created.append(port_id)
        return port

    yield make

    for port_id in created:
        port = core_ports.get(port_id)
        if port is not None:
            await port.remove(persisted_data=False)
        await core_vports.remove(port_id)


class TestAddVirtualPort:
    """Test that a virtual port cannot take an id inside the namespace reserved for a slave's ports."""

    async def test_refuses_id_in_slave_namespace(self, slave1, vport_maker) -> None:
        with pytest.raises(core_api.APIError, match="duplicate-port") as exc_info:
            await vport_maker("slave1.port2")
        assert exc_info.value.status == 400
        assert core_ports.get("slave1.port2") is None

    async def test_refuses_id_with_further_dots(self, slave1, vport_maker) -> None:
        with pytest.raises(core_api.APIError, match="duplicate-port"):
            await vport_maker("slave1.a.b")

    async def test_allows_id_equal_to_slave_name(self, slave1, vport_maker) -> None:
        """Test that an id with no dot is allowed, even when it matches a slave name."""
        port = await vport_maker("slave1")
        assert core_ports.get("slave1") is port

    async def test_allows_dotted_id_of_unknown_prefix(self, slave1, vport_maker) -> None:
        port = await vport_maker("other.port2")
        assert core_ports.get("other.port2") is port

    async def test_refuses_duplicate_id(self, slave1, vport_maker) -> None:
        await vport_maker("vportx")
        with pytest.raises(core_api.APIError, match="duplicate-port") as exc_info:
            await vport_maker("vportx")
        assert exc_info.value.status == 400

    async def test_no_slaves_registered(self, vport_maker, mocker) -> None:
        mocker.patch.dict("qtoggleserver.slaves.devices._slaves_by_name", {}, clear=True)
        port = await vport_maker("slave1.port2")
        assert core_ports.get("slave1.port2") is port


class TestRestoreSlaveNamespace:
    """Test how PATCH /ports tells a local port from a slave port when restoring a backup."""

    async def test_entry_in_slave_namespace_is_not_created(
        self, slave1, mock_api_request_maker, mock_persist_driver
    ) -> None:
        # The slave is offline here, so the port does not exist yet; it must not be recreated as a virtual port
        request = mock_api_request_maker("PATCH", "/ports", access_level=core_api.ACCESS_LEVEL_ADMIN)
        await ports_api_funcs.patch_ports(request, [{"id": "slave1.port1", "virtual": True, "type": "boolean"}])

        assert core_ports.get("slave1.port1") is None

    async def test_local_entry_named_after_slave_is_created(
        self, slave1, mock_api_request_maker, mock_persist_driver, mocker
    ) -> None:
        mocker.patch("asyncio.Lock")
        request = mock_api_request_maker("PATCH", "/ports", access_level=core_api.ACCESS_LEVEL_ADMIN)
        try:
            await ports_api_funcs.patch_ports(request, [{"id": "slave1", "virtual": True, "type": "boolean"}])
            assert core_ports.get("slave1") is not None
        finally:
            port = core_ports.get("slave1")
            if port is not None:
                await port.remove(persisted_data=False)
            await core_vports.remove("slave1")

    async def test_local_dotted_entry_is_created(
        self, slave1, mock_api_request_maker, mock_persist_driver, mocker
    ) -> None:
        mocker.patch("asyncio.Lock")
        request = mock_api_request_maker("PATCH", "/ports", access_level=core_api.ACCESS_LEVEL_ADMIN)
        try:
            await ports_api_funcs.patch_ports(request, [{"id": "other.port2", "virtual": True, "type": "boolean"}])
            assert core_ports.get("other.port2") is not None
        finally:
            port = core_ports.get("other.port2")
            if port is not None:
                await port.remove(persisted_data=False)
            await core_vports.remove("other.port2")
