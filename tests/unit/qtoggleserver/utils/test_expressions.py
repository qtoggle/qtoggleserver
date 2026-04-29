from qtoggleserver.core.expressions import EvalContext
from qtoggleserver.utils import expressions


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
            "slave1.attr1": "val1",
            "slave1.attr2": "val2",
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
            "slave1.attr1": "val1",
            "slave2.attr2": "val2",
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
