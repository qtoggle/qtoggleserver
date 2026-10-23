import asyncio
import types

import pytest

from qtoggleserver.conf import settings
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core import responses as core_responses
from qtoggleserver.slaves import devices as slaves_devices
from qtoggleserver.slaves import exceptions
from qtoggleserver.slaves.devices import Slave
from qtoggleserver.slaves.ports import SlavePort
from tests.unit.qtoggleserver.mock.ports import MockNumberPort


@pytest.fixture
async def slave() -> Slave:
    return Slave(
        name="slave1",
        scheme="http",
        host="192.168.1.2",
        port=80,
        path="",
        admin_password="",
    )


@pytest.fixture
def mock_http_client(mocker):
    http_client = mocker.MagicMock()
    http_client.fetch = mocker.AsyncMock(return_value=types.SimpleNamespace(error=None, code=200))
    mocker.patch("qtoggleserver.slaves.devices.AsyncHTTPClient", return_value=http_client)

    return http_client


class TestInterceptError:
    """Test Slave.intercept_error() attribute name adaptation."""

    async def test_expression_field(self, slave) -> None:
        """Test that an invalid expression field is prefixed with device_."""
        error = core_responses.HTTPError(400, "invalid-field", field="expression")
        intercepted = slave.intercept_error(error)
        assert isinstance(intercepted, core_responses.HTTPError)
        assert intercepted.params["field"] == "device_expression"

    async def test_history_field(self, slave) -> None:
        """Test that an invalid history_* field is prefixed with device_."""
        error = core_responses.HTTPError(400, "invalid-field", field="history_interval")
        intercepted = slave.intercept_error(error)
        assert intercepted.params["field"] == "device_history_interval"

    async def test_other_field_unchanged(self, slave) -> None:
        """Test that other invalid fields are passed through untouched."""
        error = core_responses.HTTPError(400, "invalid-field", field="name")
        assert slave.intercept_error(error) is error

    async def test_other_code_unchanged(self, slave) -> None:
        """Test that errors with a different code are passed through untouched."""
        error = core_responses.HTTPError(400, "no-such-attribute", field="expression")
        assert slave.intercept_error(error) is error

    async def test_non_http_error_unchanged(self, slave) -> None:
        """Test that non-HTTP errors are passed through untouched."""
        error = core_responses.Timeout()
        assert slave.intercept_error(error) is error


class TestAPICallError:
    """Test error propagation through Slave._api_call()."""

    async def test_intercepted_error_propagated(self, slave, mock_http_client, mocker) -> None:
        """Test that the error adapted by intercept_error() is the one being raised."""
        mocker.patch.object(
            core_responses,
            "parse",
            side_effect=core_responses.HTTPError(400, "invalid-field", field="expression"),
        )

        with pytest.raises(core_responses.HTTPError) as exc_info:
            await slave._api_call("PATCH", "/device", {"expression": "BAD("})

        assert exc_info.value.params["field"] == "device_expression"

    async def test_untouched_error_propagated(self, slave, mock_http_client, mocker) -> None:
        """Test that an error which intercept_error() leaves alone is propagated as-is."""
        error = core_responses.HTTPError(400, "invalid-field", field="name")
        mocker.patch.object(core_responses, "parse", side_effect=error)

        with pytest.raises(core_responses.HTTPError) as exc_info:
            await slave._api_call("PATCH", "/device", {"name": ""})

        assert exc_info.value is error


class TestAPICallRetry:
    """Test which failed calls Slave._api_call() retries."""

    @pytest.fixture(autouse=True)
    def setup(self, slave, mocker) -> None:
        slave._enabled = True
        mocker.patch.object(settings.slaves, "retry_interval", 0)
        mocker.patch.object(settings.slaves, "retry_count", 3)

    async def test_retries_write_that_never_reached_slave(self, slave, mock_http_client, mocker) -> None:
        mocker.patch.object(core_responses, "parse", side_effect=[core_responses.ConnectionRefused(), None])

        await slave._api_call("PATCH", "/ports/p1/value", 1)

        assert mock_http_client.fetch.call_count == 2

    async def test_does_not_retry_write_timeout(self, slave, mock_http_client, mocker) -> None:
        """The write may have reached the slave, so repeating it isn't safe."""

        mocker.patch.object(core_responses, "parse", side_effect=[core_responses.Timeout(), None])

        with pytest.raises(core_responses.Timeout):
            await slave._api_call("PATCH", "/ports/p1/value", 1)

        assert mock_http_client.fetch.call_count == 1

    async def test_retries_read_timeout(self, slave, mock_http_client, mocker) -> None:
        mocker.patch.object(core_responses, "parse", side_effect=[core_responses.Timeout(), {"name": "s"}])

        assert await slave._api_call("GET", "/device") == {"name": "s"}
        assert mock_http_client.fetch.call_count == 2

    @pytest.mark.parametrize("method", ["GET", "PATCH"])
    async def test_does_not_retry_error_answer(self, method, slave, mock_http_client, mocker) -> None:
        error = core_responses.HTTPError(500, "port-error")
        mocker.patch.object(core_responses, "parse", side_effect=[error, None])

        with pytest.raises(core_responses.HTTPError):
            await slave._api_call(method, "/ports/p1/value", 1)

        assert mock_http_client.fetch.call_count == 1

    async def test_gives_up_after_retry_count(self, slave, mock_http_client, mocker) -> None:
        mocker.patch.object(core_responses, "parse", side_effect=core_responses.ConnectionRefused())

        with pytest.raises(core_responses.ConnectionRefused):
            await slave._api_call("PATCH", "/ports/p1/value", 1)

        assert mock_http_client.fetch.call_count == 4

    async def test_retries_do_not_block_parallel_caller(self, slave, mock_http_client, mocker) -> None:
        """Retries must not take more parallel caller slots, or a call failing more than once never returns."""

        mocker.patch.object(core_responses, "parse", side_effect=core_responses.ConnectionRefused())

        async with asyncio.timeout(5):
            with pytest.raises(core_responses.ConnectionRefused):
                await slave.api_call("PATCH", "/ports/p1/value", 1)

        assert mock_http_client.fetch.call_count == 4

    async def test_newer_call_cancels_retry(self, slave, mock_http_client, mocker) -> None:
        """A call started while a retry waits replaces it, so an older write can't override a newer one."""

        async def newer_call(_) -> None:
            slave._last_api_call_ref = {}

        mocker.patch("qtoggleserver.slaves.devices.asyncio.sleep", side_effect=newer_call)
        mocker.patch.object(core_responses, "parse", side_effect=[core_responses.ConnectionRefused(), None])

        with pytest.raises(core_responses.ConnectionRefused):
            await slave._api_call("PATCH", "/ports/p1/value", 1)

        assert mock_http_client.fetch.call_count == 1


@pytest.fixture
async def local_port_maker(mocker):
    """Create local (non-slave) ports and remove them when the test ends."""
    mocker.patch("asyncio.Lock")
    created = []

    async def make(port_id: str) -> MockNumberPort:
        port = (await core_ports.load([{"driver": MockNumberPort, "port_id": port_id, "value": None}]))[0]
        created.append(port)
        return port

    yield make

    for port in created:
        await port.remove(persisted_data=False)


@pytest.fixture
def registered_slave(slave):
    slaves_devices._slaves_by_name[slave.get_name()] = slave
    yield slave
    slaves_devices._slaves_by_name.pop(slave.get_name(), None)


class TestGetPortOwner:
    """Test that a port id is attributed to a slave only by its reserved `<name>.` prefix."""

    async def test_slave_port_id(self, registered_slave) -> None:
        assert slaves_devices.get_port_owner("slave1.port1") is registered_slave

    async def test_id_with_further_dots(self, registered_slave) -> None:
        assert slaves_devices.get_port_owner("slave1.a.b") is registered_slave

    async def test_id_equal_to_slave_name(self, registered_slave) -> None:
        """Test that an id with no dot is a local port id, even when it matches a slave name."""
        assert slaves_devices.get_port_owner("slave1") is None

    async def test_id_with_slave_name_but_no_dot_after(self, registered_slave) -> None:
        assert slaves_devices.get_port_owner("slave12.port1") is None

    async def test_unknown_prefix(self, registered_slave) -> None:
        assert slaves_devices.get_port_owner("other.port1") is None

    async def test_dotted_local_id(self, registered_slave) -> None:
        assert slaves_devices.get_port_owner("a.b.c") is None


class TestIsNameUsedLocally:
    """Test the reverse check: whether a local port already holds the prefix a slave name would reserve."""

    async def test_local_port_in_namespace(self, local_port_maker) -> None:
        await local_port_maker("slave1.port2")
        assert slaves_devices.is_name_used_locally("slave1") is True

    async def test_local_port_equal_to_name(self, local_port_maker) -> None:
        """Test that a local port named exactly like the slave is not a clash."""
        await local_port_maker("slave1")
        assert slaves_devices.is_name_used_locally("slave1") is False

    async def test_unrelated_local_port(self, local_port_maker) -> None:
        await local_port_maker("other.port2")
        assert slaves_devices.is_name_used_locally("slave1") is False

    async def test_no_local_ports(self) -> None:
        assert slaves_devices.is_name_used_locally("slave1") is False

    async def test_slave_ports_ignored(self, slave, mock_persist_driver, mocker) -> None:
        """Test that the slave's own ports, which live in that namespace by design, don't count."""
        mocker.patch("asyncio.Lock")
        port = await core_ports.load_one(SlavePort, {"slave": slave, "attrs": {"id": "port1", "type": "number"}})
        try:
            assert slaves_devices.is_name_used_locally("slave1") is False
        finally:
            await port.remove(persisted_data=False)


class TestAddNameClash:
    """Test that a slave is refused when its name would reserve a prefix a local port already holds."""

    @pytest.fixture(autouse=True)
    def isolate_slaves(self, mocker) -> None:
        mocker.patch.dict("qtoggleserver.slaves.devices._slaves_by_name", {}, clear=True)

    async def test_refuses_name_used_by_local_port(self, local_port_maker, mock_persist_driver) -> None:
        await local_port_maker("slave1.port2")

        with pytest.raises(exceptions.DeviceAlreadyExists):
            await slaves_devices.add(
                scheme="http",
                host="192.168.1.2",
                port=80,
                path="",
                poll_interval=10,
                listen_enabled=False,
                name="slave1",
                enabled=False,
            )

        assert slaves_devices.get("slave1") is None

    async def test_allows_name_equal_to_local_port_id(self, local_port_maker, mock_persist_driver) -> None:
        await local_port_maker("slave1")

        slave = await slaves_devices.add(
            scheme="http",
            host="192.168.1.2",
            port=80,
            path="",
            poll_interval=10,
            listen_enabled=False,
            name="slave1",
            enabled=False,
        )

        assert slaves_devices.get("slave1") is slave


class TestRenameNameClash:
    """Test that renaming a slave into a prefix held by a local port is refused."""

    @pytest.fixture(autouse=True)
    def isolate_slaves(self, mocker) -> None:
        mocker.patch.dict("qtoggleserver.slaves.devices._slaves_by_name", {}, clear=True)

    async def test_refuses_new_name_used_by_local_port(self, slave, local_port_maker) -> None:
        await local_port_maker("slave2.port2")

        with pytest.raises(exceptions.DeviceAlreadyExists):
            await slave._handle_rename("slave2")

    async def test_slave_disabled_before_refusing(self, slave, local_port_maker, mocker) -> None:
        """Test that the spec's "the slave must be disabled" holds for a clashing rename."""
        await local_port_maker("slave2.port2")
        mocker.patch.object(slave, "is_enabled", return_value=True)
        mocker.patch.object(slave, "trigger_update")
        disable = mocker.patch.object(slave, "disable")

        with pytest.raises(exceptions.DeviceAlreadyExists):
            await slave._handle_rename("slave2")

        disable.assert_awaited_once()

    async def test_refused_through_name_change_event(self, slave, local_port_maker) -> None:
        await local_port_maker("slave2.port2")

        with pytest.raises(exceptions.DeviceAlreadyExists):
            await slave.update_cached_attrs({"name": "slave2"})

        assert slave.get_name() == "slave1"

    async def test_allows_new_name_equal_to_local_port_id(self, slave, local_port_maker, mock_persist_driver) -> None:
        await local_port_maker("slave2")

        await slave._handle_rename("slave2")


class TestAddPortFailureIsolation:
    """Test that a port which cannot be added does not stop the remaining ones. A statically configured or
    peripheral port may hold a reserved id, as both are loaded before slaves."""

    async def test_port_sync_continues_after_failure(self, slave, mock_persist_driver, mocker) -> None:
        mocker.patch.object(slave, "api_call", return_value=[{"id": "port1"}, {"id": "port2"}])
        mocker.patch.object(slave, "_save_ports")
        added = []

        async def add_port(attrs) -> None:
            if attrs["id"] == "port1":
                raise core_ports.PortLoadError("A port with id slave1.port1 already exists")
            added.append(attrs["id"])

        mocker.patch.object(slave, "_add_port", side_effect=add_port)

        await slave.fetch_and_update_ports()

        assert added == ["port2"]

    async def test_port_load_continues_after_failure(self, slave, mocker) -> None:
        mocker.patch(
            "qtoggleserver.persist.query",
            new_callable=mocker.AsyncMock,
            return_value=[{"id": "slave1.port1"}, {"id": "slave1.port2"}],
        )
        loaded = []

        async def add_port(attrs) -> None:
            if attrs["id"] == "port1":
                raise core_ports.PortLoadError("A port with id slave1.port1 already exists")
            loaded.append(attrs["id"])

        mocker.patch.object(slave, "_add_port", side_effect=add_port)

        await slave._load_ports()

        assert loaded == ["port2"]


class TestLoadNameClash:
    """Test that a clash which only persisted data can produce is reported at load time. Such data predates the
    reserved prefix rule, so loading must not fail over it."""

    @pytest.fixture(autouse=True)
    def isolate_slaves(self, mocker) -> None:
        mocker.patch.dict("qtoggleserver.slaves.devices._slaves_by_name", {}, clear=True)

    @pytest.fixture
    def persisted_slave1(self, mocker):
        mocker.patch(
            "qtoggleserver.persist.query",
            new_callable=mocker.AsyncMock,
            return_value=[
                {
                    "id": "slave1",
                    "scheme": "http",
                    "host": "192.168.1.2",
                    "port": 80,
                    "path": "",
                    "enabled": False,
                }
            ],
        )

    async def test_slave_still_loaded(self, persisted_slave1, local_port_maker, mocker) -> None:
        await local_port_maker("slave1.port2")
        mocker.patch.object(Slave, "trigger_add")

        await slaves_devices.load()

        assert slaves_devices.get("slave1") is not None

    async def test_clash_logged(self, persisted_slave1, local_port_maker, mocker, caplog) -> None:
        await local_port_maker("slave1.port2")
        mocker.patch.object(Slave, "trigger_add")

        await slaves_devices.load()

        assert "already used locally" in caplog.text

    async def test_no_clash_not_logged(self, persisted_slave1, local_port_maker, mocker, caplog) -> None:
        await local_port_maker("slave1")
        mocker.patch.object(Slave, "trigger_add")

        await slaves_devices.load()

        assert "already used locally" not in caplog.text


class TestPeripheralNameClash:
    """Test the peripheral side of the rule. A named peripheral calls its ports `<name>.<port id>`, so its name
    reserves the same prefix a slave name would."""

    @pytest.fixture(autouse=True)
    def isolate_slaves(self, mocker) -> None:
        mocker.patch.dict("qtoggleserver.slaves.devices._slaves_by_name", {}, clear=True)

    async def test_peripheral_name_counts_without_ports(self, mock_peripheral1) -> None:
        """Test that the name is taken even before the peripheral has loaded any port."""
        assert slaves_devices.is_name_used_locally("peripheral1") is True

    async def test_unrelated_peripheral_name(self, mock_peripheral1) -> None:
        assert slaves_devices.is_name_used_locally("slave1") is False

    async def test_slave_refused(self, mock_peripheral1, mock_persist_driver) -> None:
        with pytest.raises(exceptions.DeviceAlreadyExists):
            await slaves_devices.add(
                scheme="http",
                host="192.168.1.2",
                port=80,
                path="",
                poll_interval=10,
                listen_enabled=False,
                name="peripheral1",
                enabled=False,
            )

    async def test_rename_refused(self, slave, mock_peripheral1) -> None:
        with pytest.raises(exceptions.DeviceAlreadyExists):
            await slave._handle_rename("peripheral1")

    async def test_unnamed_peripheral_id_ignored(self, mocker) -> None:
        """Test that an unnamed peripheral's generated id is not treated as a name: it gives its ports no prefix."""
        unnamed = mocker.MagicMock()
        unnamed.get_name.return_value = None
        unnamed.get_id.return_value = "peripheral_abc12345"
        mocker.patch("qtoggleserver.peripherals.get_all", return_value=[unnamed])

        assert slaves_devices.is_name_used_locally("peripheral_abc12345") is False

    async def test_nameless_slave_matches_nothing(self, mocker) -> None:
        """Test that an empty name matches no unnamed peripheral. A slave added while disabled may have no name yet,
        and `get_name() == None` would otherwise match every unnamed peripheral."""
        unnamed = mocker.MagicMock()
        unnamed.get_name.return_value = None
        mocker.patch("qtoggleserver.peripherals.get_all", return_value=[unnamed])

        assert slaves_devices.is_name_used_locally(None) is False
        assert slaves_devices.is_name_used_locally("") is False
