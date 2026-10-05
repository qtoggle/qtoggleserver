import pytest

from qtoggleserver.core import ports as core_ports
from qtoggleserver.core import responses as core_responses
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

    async def test_offline_reported_by_slave(self, slave, slave_port) -> None:
        await slave_port.enable()
        slave_port.update_cached_attrs({"id": "port1", "type": "boolean", "enabled": True, "online": False})

        assert await slave_port.get_attr("online") is False
