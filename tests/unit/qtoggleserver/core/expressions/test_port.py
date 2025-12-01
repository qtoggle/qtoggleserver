import pytest

from qtoggleserver.core.expressions import Role, parse
from qtoggleserver.core.expressions.exceptions import DisabledPort, PortValueUnavailable, UnknownPortId
from qtoggleserver.core.expressions.ports import PortRef, PortValue, SelfPortRef, SelfPortValue


class TestPortValue:
    def test_parse(self, mock_num_port1, mock_num_port2):
        e = parse("nid1", "$nid2", role=Role.VALUE)
        assert isinstance(e, PortValue)
        assert e.port_id == "nid2"
        assert e.get_port() == mock_num_port2

    def test_parse_self(self, mock_num_port1):
        e = parse("nid1", "$", role=Role.VALUE)
        assert isinstance(e, SelfPortValue)
        assert e.port_id == "nid1"
        assert e.get_port() == mock_num_port1

    def test_parse_inexistent(self, mock_num_port1):
        e = parse("nid1", "$nid2", role=Role.VALUE)
        assert isinstance(e, PortValue)
        assert e.port_id == "nid2"
        assert e.get_port() is None

    async def test_eval(self, mock_num_port1, dummy_eval_context):
        """Should return the port value from supplied context."""

        e = PortValue("nid1", prefix="$", role=Role.VALUE)
        dummy_eval_context.port_values["nid1"] = 16
        assert await e._eval(dummy_eval_context) == 16

    async def test_eval_unknown(self, mock_num_port1, dummy_eval_context):
        """Should raise UnknownPortId when the referenced port doesn't exist."""

        e = PortValue("inexistent", prefix="$", role=Role.VALUE)
        with pytest.raises(UnknownPortId) as exc_info:
            await e._eval(dummy_eval_context)
        assert exc_info.value.port_id == "inexistent"

    async def test_eval_unavailable(self, mock_num_port1, dummy_eval_context):
        """Should raise PortValueUnavailable when the referenced port's value is unavailable."""

        e = PortValue("nid1", prefix="$", role=Role.VALUE)
        dummy_eval_context.port_values["nid1"] = None
        with pytest.raises(PortValueUnavailable) as exc_info:
            await e._eval(dummy_eval_context)
        assert exc_info.value.port_id == "nid1"

    async def test_eval_disabled(self, mock_num_port1, dummy_eval_context, mocker):
        """Should raise DisabledPort when the referenced port is disabled."""

        e = PortValue("nid1", prefix="$", role=Role.VALUE)
        dummy_eval_context.port_values["nid1"] = None
        mocker.patch.object(mock_num_port1, "is_enabled", return_value=False)

        with pytest.raises(DisabledPort) as exc_info:
            await e._eval(dummy_eval_context)
        assert exc_info.value.port_id == "nid1"


class TestPortRef:
    def test_parse(self, mock_num_port1, mock_num_port2):
        e = parse("nid1", "@nid2", role=Role.VALUE)
        assert isinstance(e, PortRef)
        assert e.port_id == "nid2"
        assert e.get_port() == mock_num_port2

    def test_parse_self(self, mock_num_port1):
        e = parse("nid1", "@", role=Role.VALUE)
        assert isinstance(e, SelfPortRef)
        assert e.port_id == "nid1"
        assert e.get_port() == mock_num_port1

    def test_parse_inexistent(self, mock_num_port1):
        e = parse("nid1", "@nid2", role=Role.VALUE)
        assert isinstance(e, PortRef)
        assert e.port_id == "nid2"
        assert e.get_port() is None

    async def test_eval(self, mock_num_port1, dummy_eval_context):
        """Should return the port value from supplied context."""

        e = PortRef("nid1", prefix="@", role=Role.VALUE)
        assert await e._eval(dummy_eval_context) == "nid1"

    async def test_eval_unknown(self, mock_num_port1, dummy_eval_context):
        """Should raise UnknownPortId when the referenced port doesn't exist."""

        e = PortRef("inexistent", prefix="@", role=Role.VALUE)
        with pytest.raises(UnknownPortId) as exc_info:
            await e._eval(dummy_eval_context)
        assert exc_info.value.port_id == "inexistent"
