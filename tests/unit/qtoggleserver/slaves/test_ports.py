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
