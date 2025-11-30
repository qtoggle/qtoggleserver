import asyncio

import pytest

from qtoggleserver.core.expressions import Role, parse
from qtoggleserver.core.expressions.ports import PortRef, PortValue
from qtoggleserver.core.ports import InvalidAttributeValue


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


class TestPortTransformRead:
    async def test(self, mock_num_port1):
        await mock_num_port1.set_attr("transform_read", "MUL($, 10)")
        mock_num_port1.set_last_read_value(4)
        mock_num_port1.set_next_value(5)
        assert await mock_num_port1.read_transformed_value() == 50

    async def test_non_self_dependency(self, mock_num_port1):
        """Should (indirectly) raise `NonSelfDependency` when expression depends on another port."""

        with pytest.raises(InvalidAttributeValue) as exc_info:
            await mock_num_port1.set_attr("transform_read", "MUL($another_port, 10)")
        assert exc_info.value.details == {"reason": "non-self-dependency", "token": "another_port", "pos": 4}


class TestPortTransformWrite:
    async def test(self, mock_num_port1, mocker):
        mock_num_port1.set_writable(True)
        mocker.patch.object(mock_num_port1, "write_value")

        await mock_num_port1.set_attr("transform_write", "MUL($, 10)")
        mock_num_port1.set_last_read_value(4)
        mock_num_port1.set_next_value(5)

        await mock_num_port1.transform_and_write_value(6)
        mock_num_port1.write_value.assert_called_once_with(60)

    async def test_non_self_dependency(self, mock_num_port1):
        """Should (indirectly) raise `NonSelfDependency` when expression depends on another port."""

        mock_num_port1.set_writable(True)
        with pytest.raises(InvalidAttributeValue) as exc_info:
            await mock_num_port1.set_attr("transform_write", "MUL($another_port, 10)")
        assert exc_info.value.details == {"reason": "non-self-dependency", "token": "another_port", "pos": 4}


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
