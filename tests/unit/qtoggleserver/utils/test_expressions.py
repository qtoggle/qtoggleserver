import pytest

from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.expressions import EvalContext
from qtoggleserver.utils import expressions
from tests.unit.qtoggleserver.mock.ports import MockNumberPort


class TestGetDepsMap:
    @pytest.fixture(autouse=True)
    def reset_cache(self):
        expressions.invalidate_deps_map()
        yield
        expressions.invalidate_deps_map()

    def test_empty_with_no_expression_ports(self, mock_num_port1):
        """Should return empty map when no ports have expressions."""

        deps_map = expressions.get_deps_map()
        assert deps_map == {}

    def test_maps_dep_to_port(self, mock_num_port1, mock_num_port2):
        """Should map each dep string to the ports whose expressions include that dep."""

        mock_num_port1.set_expression("MUL($nid2, 2)")
        deps_map = expressions.get_deps_map()
        assert mock_num_port1 in deps_map.get("$nid2", [])

    def test_multiple_ports_same_dep(self, mock_num_port1, mock_num_port2):
        """Should list all ports depending on the same dep."""

        mock_num_port1.set_expression("MUL($nid2, 2)")
        mock_num_port2.set_expression("ADD($nid2, 1)")
        deps_map = expressions.get_deps_map()
        assert set(deps_map.get("$nid2", [])) == {mock_num_port1, mock_num_port2}

    def test_multiple_deps_per_port(self, mock_num_port1, mock_num_port2):
        """Should register a port under each of its deps."""

        mock_num_port1.set_expression("ADD($nid1, $nid2)")
        deps_map = expressions.get_deps_map()
        assert mock_num_port1 in deps_map.get("$nid1", [])
        assert mock_num_port1 in deps_map.get("$nid2", [])

    def test_is_cached(self, mock_num_port1):
        """Should return the same dict object on repeated calls without any changes."""

        mock_num_port1.set_expression("MUL($nid1, 2)")
        deps_map1 = expressions.get_deps_map()
        deps_map2 = expressions.get_deps_map()
        assert deps_map1 is deps_map2

    async def test_port_removed_excluded_from_rebuilt_map(self, mock_num_port2):
        """Should not include a removed port in the rebuilt map after removal."""

        port = await core_ports.load_one(MockNumberPort, {"port_id": "nid_temp", "value": None})
        await port.enable()
        port.set_expression("MUL($nid2, 2)")

        assert port in expressions.get_deps_map().get("$nid2", [])

        await port.remove(persisted_data=False)

        assert port not in expressions.get_deps_map().get("$nid2", [])

    def test_expression_set_included_in_rebuilt_map(self, mock_num_port1, mock_num_port2):
        """Should include a port's deps in the rebuilt map after an expression is set."""

        assert "$nid2" not in expressions.get_deps_map()

        mock_num_port1.set_expression("MUL($nid2, 2)")

        assert mock_num_port1 in expressions.get_deps_map().get("$nid2", [])

    async def test_expression_cleared_excluded_from_rebuilt_map(self, mock_num_port1):
        """Should exclude a port's deps from the rebuilt map after its expression is cleared."""

        mock_num_port1.set_expression("MUL($nid1, 2)")
        assert mock_num_port1 in expressions.get_deps_map().get("$nid1", [])

        mock_num_port1.set_writable(True)
        await mock_num_port1.attr_set_expression("")

        assert mock_num_port1 not in expressions.get_deps_map().get("$nid1", [])


class TestBuildContext:
    async def test_basic_context(self, mock_num_port1, mock_num_port2, mocker):
        """Should gather port values and attributes from all enabled ports and create EvalContext."""

        mocker.patch(
            "qtoggleserver.utils.expressions.core_ports.get_all",
            return_value=[mock_num_port1, mock_num_port2],
        )
        mocker.patch.object(mock_num_port1, "is_enabled", return_value=True)
        mocker.patch.object(mock_num_port2, "is_enabled", return_value=True)
        mocker.patch.object(mock_num_port1, "get_id", return_value="nid1")
        mocker.patch.object(mock_num_port2, "get_id", return_value="nid2")
        mocker.patch.object(mock_num_port1, "get_last_value", return_value=42)
        mocker.patch.object(mock_num_port2, "get_last_value", return_value=84)
        mocker.patch.object(mock_num_port1, "get_attrs", new_callable=mocker.AsyncMock, return_value={"attr1": "val1"})
        mocker.patch.object(mock_num_port2, "get_attrs", new_callable=mocker.AsyncMock, return_value={"attr2": "val2"})
        mocker.patch(
            "qtoggleserver.utils.expressions.core_device_attrs.get_attrs",
            new_callable=mocker.AsyncMock,
            return_value={"device_attr": "device_val"},
        )
        mocker.patch("qtoggleserver.utils.expressions.settings.slaves.enabled", False)

        context = await expressions.build_context(1000)

        assert isinstance(context, EvalContext)
        assert context.port_values == {"nid1": 42, "nid2": 84}
        assert context.port_attrs == {"nid1": {"attr1": "val1"}, "nid2": {"attr2": "val2"}}
        assert context.device_attrs == {"device_attr": "device_val"}
        assert context.now_ms == 1000
        assert context.timestamp == 1

    async def test_disabled_port_excluded(self, mock_num_port1, mock_num_port2, mocker):
        """Should exclude disabled ports from the context."""

        mocker.patch(
            "qtoggleserver.utils.expressions.core_ports.get_all",
            return_value=[mock_num_port1, mock_num_port2],
        )
        mocker.patch.object(mock_num_port1, "is_enabled", return_value=True)
        mocker.patch.object(mock_num_port2, "is_enabled", return_value=False)
        mocker.patch.object(mock_num_port1, "get_id", return_value="nid1")
        mocker.patch.object(mock_num_port1, "get_last_value", return_value=42)
        mocker.patch.object(mock_num_port1, "get_attrs", new_callable=mocker.AsyncMock, return_value={})
        mocker.patch(
            "qtoggleserver.utils.expressions.core_device_attrs.get_attrs",
            new_callable=mocker.AsyncMock,
            return_value={},
        )
        mocker.patch("qtoggleserver.utils.expressions.settings.slaves.enabled", False)

        context = await expressions.build_context(2000)

        assert context.port_values == {"nid1": 42}
        assert context.port_attrs == {"nid1": {}}
        assert context.now_ms == 2000

    async def test_no_ports(self, mocker):
        """Should handle case with no ports."""

        mocker.patch(
            "qtoggleserver.utils.expressions.core_ports.get_all",
            return_value=[],
        )
        mocker.patch(
            "qtoggleserver.utils.expressions.core_device_attrs.get_attrs",
            new_callable=mocker.AsyncMock,
            return_value={"device_attr": "device_val"},
        )
        mocker.patch("qtoggleserver.utils.expressions.settings.slaves.enabled", False)

        context = await expressions.build_context(5000)

        assert context.port_values == {}
        assert context.port_attrs == {}
        assert context.device_attrs == {"device_attr": "device_val"}
        assert context.now_ms == 5000

    async def test_with_slave_attrs(self, mock_num_port1, mocker):
        """Should include slave device attributes when slaves are enabled."""

        mock_slave = mocker.Mock()
        mocker.patch(
            "qtoggleserver.utils.expressions.core_ports.get_all",
            return_value=[mock_num_port1],
        )
        mocker.patch.object(mock_num_port1, "is_enabled", return_value=True)
        mocker.patch.object(mock_num_port1, "get_id", return_value="nid1")
        mocker.patch.object(mock_num_port1, "get_last_value", return_value=42)
        mocker.patch.object(mock_num_port1, "get_attrs", new_callable=mocker.AsyncMock, return_value={})
        mocker.patch(
            "qtoggleserver.utils.expressions.core_device_attrs.get_attrs",
            new_callable=mocker.AsyncMock,
            return_value={"device_attr": "device_val"},
        )
        mocker.patch("qtoggleserver.utils.expressions.settings.slaves.enabled", True)
        mock_slave.get_name.return_value = "slave1"
        mock_slave.get_cached_attrs.return_value = {"attr1": "val1", "attr2": "val2"}
        mocker.patch(
            "qtoggleserver.utils.expressions.slaves_devices.get_all",
            return_value=[mock_slave],
        )

        context = await expressions.build_context(3000)

        assert context.device_attrs == {
            "device_attr": "device_val",
            "slave1:attr1": "val1",
            "slave1:attr2": "val2",
        }
        assert context.now_ms == 3000

    async def test_with_multiple_slaves(self, mock_num_port1, mocker):
        """Should merge attributes from multiple slaves."""

        mock_slave1 = mocker.Mock()
        mock_slave2 = mocker.Mock()
        mocker.patch(
            "qtoggleserver.utils.expressions.core_ports.get_all",
            return_value=[mock_num_port1],
        )
        mocker.patch.object(mock_num_port1, "is_enabled", return_value=True)
        mocker.patch.object(mock_num_port1, "get_id", return_value="nid1")
        mocker.patch.object(mock_num_port1, "get_last_value", return_value=42)
        mocker.patch.object(mock_num_port1, "get_attrs", new_callable=mocker.AsyncMock, return_value={})
        mocker.patch(
            "qtoggleserver.utils.expressions.core_device_attrs.get_attrs",
            new_callable=mocker.AsyncMock,
            return_value={"device_attr": "device_val"},
        )
        mocker.patch("qtoggleserver.utils.expressions.settings.slaves.enabled", True)
        mock_slave1.get_name.return_value = "slave1"
        mock_slave1.get_cached_attrs.return_value = {"attr1": "val1"}
        mock_slave2.get_name.return_value = "slave2"
        mock_slave2.get_cached_attrs.return_value = {"attr2": "val2"}
        mocker.patch(
            "qtoggleserver.utils.expressions.slaves_devices.get_all",
            return_value=[mock_slave1, mock_slave2],
        )

        context = await expressions.build_context(4000)

        assert context.device_attrs == {
            "device_attr": "device_val",
            "slave1:attr1": "val1",
            "slave2:attr2": "val2",
        }
        assert context.now_ms == 4000

    async def test_timestamp_calculation(self, mock_num_port1, mocker):
        """Should correctly calculate timestamp from now_ms."""

        mocker.patch(
            "qtoggleserver.utils.expressions.core_ports.get_all",
            return_value=[mock_num_port1],
        )
        mocker.patch.object(mock_num_port1, "is_enabled", return_value=True)
        mocker.patch.object(mock_num_port1, "get_id", return_value="nid1")
        mocker.patch.object(mock_num_port1, "get_last_value", return_value=0)
        mocker.patch.object(mock_num_port1, "get_attrs", new_callable=mocker.AsyncMock, return_value={})
        mocker.patch(
            "qtoggleserver.utils.expressions.core_device_attrs.get_attrs",
            new_callable=mocker.AsyncMock,
            return_value={},
        )
        mocker.patch("qtoggleserver.utils.expressions.settings.slaves.enabled", False)

        context1 = await expressions.build_context(0)
        assert context1.timestamp == 0

        context2 = await expressions.build_context(1500)
        assert context2.timestamp == 1

        context3 = await expressions.build_context(1234567890000)
        assert context3.timestamp == 1234567890
