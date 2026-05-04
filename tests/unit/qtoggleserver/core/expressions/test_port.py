import pytest

from qtoggleserver.core.expressions import Role, parse
from qtoggleserver.core.expressions.exceptions import (
    DisabledPort,
    PortAttrUnavailable,
    PortValueUnavailable,
    UnknownPortId,
)
from qtoggleserver.core.expressions.ports import PortAttr, PortRef, PortValue, SelfPortRef, SelfPortValue


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


class TestGetPortCache:
    def test_cache_populated_on_first_call(self, mock_num_port1):
        """get_port() should populate the cache after the first lookup."""

        e = PortValue("nid1", prefix="$", role=Role.VALUE)
        assert e._cached_port is None
        port = e.get_port()
        assert port is mock_num_port1
        assert e._cached_port is mock_num_port1

    def test_cache_hit_on_second_call(self, mock_num_port1):
        """get_port() called twice should return the same object without re-lookup."""

        e = PortValue("nid1", prefix="$", role=Role.VALUE)
        port1 = e.get_port()
        port2 = e.get_port()
        assert port1 is port2 is mock_num_port1

    async def test_cache_invalidated_on_port_removal(self, mock_num_port1):
        """get_port() should return None after the port is removed."""

        e = PortValue("nid1", prefix="$", role=Role.VALUE)
        assert e.get_port() is mock_num_port1

        await mock_num_port1.remove(persisted_data=False)
        assert mock_num_port1.is_removed()
        assert e.get_port() is None


class TestPortAttr:
    def test_parse(self, mock_num_port1):
        """Should parse `$port_id:attr_name` into a PortAttr with the correct port_id and attr_name."""

        e = parse("nid1", "$nid1:enabled", role=Role.VALUE)
        assert isinstance(e, PortAttr)
        assert e.port_id == "nid1"
        assert e.attr_name == "enabled"

    def test_deps(self):
        """Should return a dep set with `$port_id:` format."""

        e = PortAttr("nid1", prefix="$", role=Role.VALUE, attr_name="enabled")
        assert e._get_deps() == {"$nid1:"}

    async def test_eval(self, mock_num_port1, dummy_eval_context):
        """Should return the attribute value from the supplied context."""

        e = PortAttr("nid1", prefix="$", role=Role.VALUE, attr_name="enabled")
        dummy_eval_context.port_attrs["nid1"] = {"enabled": True}
        assert await e._eval(dummy_eval_context) is True

    async def test_eval_unknown(self, dummy_eval_context):
        """Should raise UnknownPortId when the referenced port doesn't exist."""

        e = PortAttr("inexistent", prefix="$", role=Role.VALUE, attr_name="enabled")
        with pytest.raises(UnknownPortId) as exc_info:
            await e._eval(dummy_eval_context)
        assert exc_info.value.port_id == "inexistent"

    async def test_eval_unavailable(self, mock_num_port1, dummy_eval_context):
        """Should raise PortAttrUnavailable when the attribute is not present in the context."""

        e = PortAttr("nid1", prefix="$", role=Role.VALUE, attr_name="nonexistent_attr")
        dummy_eval_context.port_attrs["nid1"] = {}
        with pytest.raises(PortAttrUnavailable) as exc_info:
            await e._eval(dummy_eval_context)
        assert exc_info.value.port_id == "nid1"
        assert exc_info.value.attr_name == "nonexistent_attr"
