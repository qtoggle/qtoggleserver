import time

import pytest

from qtoggleserver.core import main as core_main
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core import responses as core_responses
from qtoggleserver.core.api.funcs import ports as core_api_ports
from qtoggleserver.slaves.devices import Slave
from qtoggleserver.slaves.ports import SlavePort


@pytest.fixture
async def slave(mocker) -> Slave:
    s = Slave(
        name="slave1",
        scheme="http",
        host="192.168.1.2",
        port=80,
        path="",
        admin_password="",
    )
    mocker.patch.object(s, "is_online", return_value=True)

    return s


@pytest.fixture
async def slave_port(slave) -> SlavePort:
    return SlavePort(slave, {"id": "port1", "type": "number"})


class TestWriteValueErrorCompat:
    """Test that SlavePort.write_value() accepts both the new (500) and legacy (502/504) status codes a slave may
    use for port-error/port-timeout."""

    @pytest.mark.parametrize("status", [500, 502])
    async def test_port_error(self, slave, slave_port, mocker, status) -> None:
        mocker.patch.object(
            slave, "api_call", side_effect=core_responses.HTTPError(status, "port-error", message="boom")
        )

        with pytest.raises(core_ports.PortError) as exc_info:
            await slave_port.write_value(100)
        assert str(exc_info.value) == "boom"

    @pytest.mark.parametrize("status", [500, 504])
    async def test_port_timeout(self, slave, slave_port, mocker, status) -> None:
        mocker.patch.object(slave, "api_call", side_effect=core_responses.HTTPError(status, "port-timeout"))

        with pytest.raises(core_ports.PortTimeout):
            await slave_port.write_value(100)


class TestOnlineAttr:
    """Test the `online` attribute of a slave port, which is derived from both the local enabled state and the value
    reported by the slave device."""

    @pytest.fixture
    async def slave_port(self, slave) -> SlavePort:
        # Devices may send the attribute with a null value, as qToggle marks it optional
        return SlavePort(slave, {"id": "port1", "type": "boolean", "enabled": True, "online": None})

    async def test_null_online_means_online(self, slave_port) -> None:
        await slave_port.enable()

        assert await slave_port.get_attr("online") is True

    async def test_online_refreshed_after_enable(self, slave_port) -> None:
        # Reading the attribute while the port is still disabled used to cache a false that enabling never cleared
        assert await slave_port.get_attr("online") is False

        await slave_port.enable()

        assert await slave_port.get_attr("online") is True
        assert (await slave_port.to_json())["online"] is True

    async def test_online_refreshed_after_disable(self, slave_port) -> None:
        await slave_port.enable()
        assert await slave_port.get_attr("online") is True

        await slave_port.disable()

        assert await slave_port.get_attr("online") is False

    async def test_online_follows_slave(self, slave, slave_port, mocker) -> None:
        await slave_port.enable()
        mocker.patch.object(slave, "is_online", return_value=False)
        slave_port.invalidate_attrs()

        assert await slave_port.get_attr("online") is False

    async def test_offline_reported_by_slave(self, slave_port) -> None:
        await slave_port.enable()
        slave_port.update_cached_attrs({"id": "port1", "type": "boolean", "enabled": True, "online": False}, 0)

        assert await slave_port.get_attr("online") is False


class TestReadValueTime:
    """Test that a value received from the slave keeps the time it was taken, since it waits in a queue until the
    next read."""

    async def test_no_time_before_read(self, slave_port) -> None:
        assert slave_port.get_read_value_time() is None

    async def test_read_reports_value_time(self, slave_port) -> None:
        slave_port.push_remote_value(5, 1000)
        slave_port.push_remote_value(6, 2000)

        assert await slave_port.read_value() == 5
        assert slave_port.get_read_value_time() == 1000
        assert await slave_port.read_value() == 6
        assert slave_port.get_read_value_time() == 2000

    async def test_update_cached_attrs_value_time(self, slave_port) -> None:
        slave_port.update_cached_attrs({"id": "port1", "type": "number", "value": 5}, 1000)

        assert await slave_port.read_value() == 5
        assert slave_port.get_read_value_time() == 1000

    async def test_new_port_value_time(self, slave, freezer) -> None:
        now_ms = int(time.time() * 1000)
        port = SlavePort(slave, {"id": "port1", "type": "number", "value": 5})
        freezer.tick(10)

        assert await port.read_value() == 5
        assert port.get_read_value_time() == now_ms

    async def test_enable_stamps_with_request_start(self, slave, slave_port, freezer, mocker) -> None:
        started_ms = int(time.time() * 1000)

        async def api_call(*args, **kwargs) -> int:
            freezer.tick(10)
            return 5

        mocker.patch.object(slave, "is_ready", return_value=True)
        mocker.patch.object(slave, "api_call", side_effect=api_call)

        await slave_port.handle_enable()

        assert await slave_port.read_value() == 5
        assert slave_port.get_read_value_time() == started_ms

    async def test_value_taken_before_write_loses(self, slave, freezer, mocker) -> None:
        port = SlavePort(slave, {"id": "port1", "type": "number", "writable": True})
        await port.enable()
        mocker.patch.object(slave, "api_call")
        taken_ms = int(time.time() * 1000)
        port.push_remote_value(3, taken_ms)

        freezer.tick(1)
        await port.transform_and_write_value(5)

        freezer.tick(1)
        await core_main.read_ports(ports_to_read=[port])

        assert port.get_last_value() == 5
        assert port._last_read_value == (3, taken_ms)


class TestLegacyPersistedAttr:
    """Test the `persisted` attribute that slaves on qToggle API < 1.3 still report."""

    @pytest.fixture
    async def slave_port(self, slave) -> SlavePort:
        return SlavePort(slave, {"id": "port1", "type": "boolean", "enabled": True, "persisted": False})

    async def test_defined_when_reported(self, slave_port) -> None:
        attrdefs = await slave_port.get_attrdefs()

        assert attrdefs["persisted"]["type"] == "boolean"
        assert attrdefs["persisted"]["modifiable"] is True

    async def test_exposed_with_definition(self, slave_port) -> None:
        port_json = await slave_port.to_json()

        assert port_json["persisted"] is False
        assert port_json["definitions"]["persisted"]["type"] == "boolean"

    async def test_not_defined_when_not_reported(self, slave) -> None:
        slave_port = SlavePort(slave, {"id": "port1", "type": "boolean"})

        assert "persisted" not in await slave_port.get_attrdefs()
        assert "persisted" not in await slave_port.to_json()

    async def test_slave_definition_wins(self, slave) -> None:
        attrdef = {"type": "boolean", "modifiable": False}
        slave_port = SlavePort(
            slave,
            {
                "id": "port1",
                "type": "boolean",
                "persisted": True,
                "definitions": {
                    "persisted": attrdef,
                },
            },
        )

        assert (await slave_port.get_attrdefs())["persisted"] == attrdef

    async def test_patch_forwarded_to_slave(self, slave, slave_port, mocker) -> None:
        api_call = mocker.patch.object(slave, "api_call")

        await core_api_ports.set_port_attrs(slave_port, {"persisted": True}, ignore_extra_attrs=False)

        api_call.assert_called_once_with("PATCH", "/ports/port1", {"persisted": True}, timeout=mocker.ANY)

    async def test_patch_provisioned_when_offline(self, slave, slave_port, mocker) -> None:
        mocker.patch.object(slave, "is_online", return_value=False)
        mocker.patch.object(slave_port, "trigger_update")

        await core_api_ports.set_port_attrs(slave_port, {"persisted": True}, ignore_extra_attrs=False)

        assert slave_port.get_provisioning_attrs() == {"persisted": True}


class TestWriteRetries:
    """Test that the master neither shows nor uses the slave's write retry and enforce settings, since the slave
    retries its own writes and enforces its own values."""

    @pytest.fixture
    async def slave_port(self, slave) -> SlavePort:
        return SlavePort(
            slave,
            {
                "id": "port1",
                "type": "number",
                "writable": True,
                "write_retry_count": 3,
                "write_retry_interval": 0,
                "enforce_value": True,
            },
        )

    async def test_attrs_hidden(self, slave_port) -> None:
        attrs = await slave_port.get_attrs()

        assert "write_retry_count" not in attrs
        assert "write_retry_interval" not in attrs
        assert "enforce_value" not in attrs

    async def test_no_enforce(self, slave_port, mocker) -> None:
        slave_port._enforce_value = True
        slave_port._last_written_value = 5, 1000
        push_write = mocker.patch.object(slave_port, "push_write")

        slave_port.maybe_enforce_value(3)

        push_write.assert_not_called()

    async def test_no_retry(self, slave, slave_port, mocker) -> None:
        await slave_port.enable()
        api_call = mocker.patch.object(slave, "api_call", side_effect=core_responses.HTTPError(500, "port-error"))

        with pytest.raises(core_ports.PortError):
            await slave_port.transform_and_write_value(5)

        api_call.assert_called_once()
