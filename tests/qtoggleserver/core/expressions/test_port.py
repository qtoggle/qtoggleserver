import asyncio

from qtoggleserver.core.expressions import Role, parse
from qtoggleserver.core.expressions.ports import PortRef, PortValue


class TestPortValue:
    def test_parse(self, mock_num_port1, mock_num_port2):
        e = parse("nid1", "$nid2", role=Role.VALUE)
        assert isinstance(e, PortValue)
        assert e.port_id == "nid2"
        assert e.get_port() == mock_num_port2

    def test_self_parse(self, mock_num_port1):
        e = parse("nid1", "$", role=Role.VALUE)
        assert isinstance(e, PortValue)
        assert e.port_id == "nid1"
        assert e.get_port() == mock_num_port1

    def test_inexistent(self, mock_num_port1):
        e = parse("nid1", "$nid2", role=Role.VALUE)
        assert isinstance(e, PortValue)
        assert e.port_id == "nid2"
        assert e.get_port() is None

    async def test_self_value(self, mock_num_port1):
        mock_num_port1.set_writable(True)
        mock_num_port1.set_last_read_value(15)
        await mock_num_port1.set_attr("expression", "ADD($, 1)")
        mock_num_port1.set_last_read_value(25)
        await asyncio.sleep(0.1)
        assert mock_num_port1.get_last_written_value() == 16

    async def test_own_value(self, mock_num_port1):
        mock_num_port1.set_writable(True)
        mock_num_port1.set_last_read_value(15)
        await mock_num_port1.set_attr("expression", "ADD($nid1, 1)")
        mock_num_port1.set_last_read_value(25)
        await asyncio.sleep(0.1)
        assert mock_num_port1.get_last_written_value() == 16

    async def test_allow_self_dependency(self, mock_num_port1):
        mock_num_port1.set_writable(True)
        await mock_num_port1.set_attr("expression", "ADD($nid1, 10)")


class TestPortRef:
    def test_port_ref_parse(self, mock_num_port1, mock_num_port2):
        e = parse("nid1", "@nid2", role=Role.VALUE)
        assert isinstance(e, PortRef)
        assert e.port_id == "nid2"
        assert e.get_port() == mock_num_port2

    def test_port_ref_inexistent(self, mock_num_port1):
        e = parse("nid1", "@nid2", role=Role.VALUE)
        assert isinstance(e, PortRef)
        assert e.port_id == "nid2"
        assert e.get_port() is None
