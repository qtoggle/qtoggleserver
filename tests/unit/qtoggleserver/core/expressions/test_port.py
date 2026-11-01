import pytest

from qtoggleserver.core.expressions import EvalContext, Role, parse
from qtoggleserver.core.expressions.exceptions import (
    DisabledPort,
    OfflinePort,
    PortAttrUnavailable,
    PortValueUnavailable,
    TransformNotSupported,
    UnexpectedCharacter,
    UnknownPortId,
)
from qtoggleserver.core.expressions.ports import (
    PortAttr,
    PortRef,
    PortValue,
    PortValueKind,
    SelfPortAttr,
    SelfPortRef,
    SelfPortValue,
)
from qtoggleserver.utils import expressions as expressions_utils


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

    def test_deps(self, mock_num_port1):
        """Should depend on the value of the port, even when it's the own port given by id."""

        e = parse("nid1", "$nid1", role=Role.VALUE)
        assert e.get_deps() == {"$nid1"}

    def test_deps_self(self, mock_num_port1):
        """Should have no deps for a self port value, as if it were wrapped in `IGNCHG`."""

        e = parse("nid1", "$", role=Role.VALUE)
        assert e.get_deps() == set()

    async def test_eval(self, mock_num_port1, dummy_eval_context):
        """Should return the port value from supplied context."""

        e = PortValue("nid1", prefix="$", role=Role.VALUE)
        dummy_eval_context.port_values["nid1"] = 16
        assert await e._eval(dummy_eval_context) == 16

    @pytest.mark.parametrize(
        "kind, value",
        [(PortValueKind.LAST, 16), (PortValueKind.LAST_READ, 17), (PortValueKind.LAST_WRITTEN, 18)],
    )
    async def test_eval_kind(self, mock_num_port1, kind, value):
        """Should return the last, last read or last written value from supplied context, as given by the kind."""

        e = PortValue("nid1", prefix="$", role=Role.VALUE, kind=kind)
        context = EvalContext(port_values={"nid1": 16}, port_read_values={"nid1": 17}, port_written_values={"nid1": 18})
        assert await e._eval(context) == value

    async def test_eval_kind_unavailable(self, mock_num_port1):
        """Should raise PortValueUnavailable when the port has no value of the given kind, even if it has others."""

        e = PortValue("nid1", prefix="$", role=Role.VALUE, kind=PortValueKind.LAST_WRITTEN)
        context = EvalContext(port_values={"nid1": 16}, port_read_values={"nid1": 16})
        with pytest.raises(PortValueUnavailable):
            await e._eval(context)

    async def test_eval_kind_disabled(self, mock_num_port1):
        """Should raise DisabledPort for every kind when the referenced port is disabled."""

        for kind in PortValueKind:
            e = PortValue("nid1", prefix="$", role=Role.VALUE, kind=kind)
            context = EvalContext(
                port_values={"nid1": 16},
                port_read_values={"nid1": 16},
                port_written_values={"nid1": 16},
                port_attrs={"nid1": {"enabled": False}},
            )
            with pytest.raises(DisabledPort):
                await e._eval(context)

    @pytest.mark.parametrize(
        "kind, suffix", [(PortValueKind.LAST, ""), (PortValueKind.LAST_READ, "?"), (PortValueKind.LAST_WRITTEN, "!")]
    )
    def test_str_deps_kind(self, mock_num_port1, kind, suffix):
        """Should add the kind's suffix to both the string form and the dep, and give a self port value no deps."""

        e = PortValue("nid1", prefix="$", role=Role.VALUE, kind=kind)
        assert str(e) == f"$nid1{suffix}"
        assert e.get_deps() == {f"$nid1{suffix}"}

        e = SelfPortValue("nid1", prefix="$", role=Role.VALUE, kind=kind)
        assert str(e) == f"${suffix}"
        assert e.get_deps() == set()

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

    async def test_eval_disabled(self, mock_num_port1):
        """Should raise DisabledPort when the referenced port is disabled."""

        e = PortValue("nid1", prefix="$", role=Role.VALUE)
        context = EvalContext(port_values={"nid1": 16}, port_attrs={"nid1": {"enabled": False}})

        with pytest.raises(DisabledPort) as exc_info:
            await e._eval(context)
        assert exc_info.value.port_id == "nid1"

    async def test_eval_offline(self, mock_num_port1):
        """Should raise OfflinePort when the referenced port is offline."""

        e = PortValue("nid1", prefix="$", role=Role.VALUE)
        context = EvalContext(port_values={"nid1": 16}, port_attrs={"nid1": {"enabled": True, "online": False}})

        with pytest.raises(OfflinePort) as exc_info:
            await e._eval(context)
        assert exc_info.value.port_id == "nid1"

    async def test_eval_offline_is_value_unavailable(self, mock_num_port1):
        """Should report an offline port as a case of unavailable port value."""

        e = PortValue("nid1", prefix="$", role=Role.VALUE)
        context = EvalContext(port_values={"nid1": 16}, port_attrs={"nid1": {"online": False}})

        with pytest.raises(PortValueUnavailable):
            await e._eval(context)

    async def test_eval_online(self, mock_num_port1):
        """Should return the port value when the referenced port is online."""

        e = PortValue("nid1", prefix="$", role=Role.VALUE)
        context = EvalContext(port_values={"nid1": 16}, port_attrs={"nid1": {"enabled": True, "online": True}})
        assert await e._eval(context) == 16

    async def test_eval_online_attr_missing(self, mock_num_port1):
        """Should return the port value when the port has no `online` attribute at all."""

        e = PortValue("nid1", prefix="$", role=Role.VALUE)
        context = EvalContext(port_values={"nid1": 16}, port_attrs={"nid1": {"enabled": True}})
        assert await e._eval(context) == 16

    async def test_eval_offline_self(self, mock_num_port1):
        """Should raise OfflinePort for a self port value reference, too."""

        e = SelfPortValue("nid1", prefix="$", role=Role.VALUE)
        context = EvalContext(port_values={"nid1": 16}, port_attrs={"nid1": {"online": False}})

        with pytest.raises(OfflinePort) as exc_info:
            await e._eval(context)
        assert exc_info.value.port_id == "nid1"

    async def test_eval_no_attrs_in_context(self, mock_num_port1):
        """Should skip the availability check when the context carries no attributes, as for transform expressions."""

        e = PortValue("nid1", prefix="$", role=Role.TRANSFORM_READ)
        context = EvalContext(port_values={"nid1": 16})
        assert await e._eval(context) == 16

    @pytest.mark.parametrize("suffix, kind", [("?", PortValueKind.LAST_READ), ("!", PortValueKind.LAST_WRITTEN)])
    def test_parse_kind(self, mock_num_port1, suffix, kind):
        """Should parse `$port_id?` and `$port_id!` into port values of their kind, with their own dep."""

        e = parse("nid1", f"ADD($nid2{suffix}, 1)", role=Role.VALUE)
        port_value = e.args[0]
        assert isinstance(port_value, PortValue)
        assert port_value.kind is kind
        assert str(e) == f"ADD($nid2{suffix}, 1)"
        assert e.get_deps() == {f"$nid2{suffix}"}

    @pytest.mark.parametrize("suffix, kind", [("?", PortValueKind.LAST_READ), ("!", PortValueKind.LAST_WRITTEN)])
    def test_parse_self_kind(self, mock_num_port1, suffix, kind):
        """Should parse `$?` and `$!` into self port values of their kind, with no deps."""

        e = parse("nid1", f"${suffix}", role=Role.VALUE)
        assert isinstance(e, SelfPortValue)
        assert e.port_id == "nid1"
        assert e.kind is kind
        assert str(e) == f"${suffix}"
        assert e.get_deps() == set()

    @pytest.mark.parametrize("sexpression", ["$nid2??", "$nid2?!", "$nid2?x", "@nid2?", "$nid2:enabled?", "$??"])
    def test_parse_kind_invalid(self, mock_num_port1, sexpression):
        """Should reject a suffix anywhere but at the end of a port value, or on references and attrs."""

        with pytest.raises(UnexpectedCharacter):
            parse("nid1", sexpression, role=Role.VALUE)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    @pytest.mark.parametrize("sexpression", ["$?", "$!", "MUL($?, 2)", "$nid1?"])
    def test_parse_kind_transform(self, mock_num_port1, role, sexpression):
        """Should reject read and written values in transforms, which allow only a plain `$`."""

        with pytest.raises(TransformNotSupported):
            parse("nid1", sexpression, role=role)

    async def test_eval_parsed_kinds(self, mock_num_port1, mock_num_port2):
        """Should give each parsed form its own value of the port."""

        context = EvalContext(
            port_values={"nid2": 9}, port_read_values={"nid2": 5}, port_written_values={"nid2": 7}, port_attrs={}
        )

        assert await parse("nid1", "$nid2", role=Role.VALUE).eval(context) == 9
        assert await parse("nid1", "$nid2?", role=Role.VALUE).eval(context) == 5
        assert await parse("nid1", "$nid2!", role=Role.VALUE).eval(context) == 7

    async def test_eval_read_value_while_write_pending(self, mock_num_port1, mock_num_port2, mocker):
        """Should give the read value for `$port_id?` and the pending value for `$port_id` while a write is pending."""

        mock_num_port2.set_read_value(5)
        mocker.patch.object(mock_num_port2, "get_pending_value", return_value=9)
        context = await expressions_utils.build_context(0)

        assert await parse("nid1", "$nid2?", role=Role.VALUE).eval(context) == 5
        assert await parse("nid1", "$nid2", role=Role.VALUE).eval(context) == 9


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

    async def test_eval_string_nonempty(self, mock_num_port1, dummy_eval_context):
        """Should return 1 when the attribute is a non-empty string."""

        e = PortAttr("nid1", prefix="$", role=Role.VALUE, attr_name="tag")
        dummy_eval_context.port_attrs["nid1"] = {"tag": "sensor"}
        assert await e._eval(dummy_eval_context) == 1

    async def test_eval_string_empty(self, mock_num_port1, dummy_eval_context):
        """Should return 0 when the attribute is an empty string."""

        e = PortAttr("nid1", prefix="$", role=Role.VALUE, attr_name="tag")
        dummy_eval_context.port_attrs["nid1"] = {"tag": ""}
        assert await e._eval(dummy_eval_context) == 0

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


class TestSelfPortAttr:
    def test_parse(self, mock_num_port1):
        """Should parse `$:attr_name` into a SelfPortAttr with port_id set to self_port_id."""

        e = parse("nid1", "$:enabled", role=Role.VALUE)
        assert isinstance(e, SelfPortAttr)
        assert e.port_id == "nid1"
        assert e.attr_name == "enabled"

    def test_str(self):
        """Should render as `$:attr_name`."""

        e = SelfPortAttr("nid1", prefix="$", role=Role.VALUE, attr_name="enabled")
        assert str(e) == "$:enabled"

    def test_deps(self):
        """Should return a dep set referencing the self port's attributes."""

        e = SelfPortAttr("nid1", prefix="$", role=Role.VALUE, attr_name="enabled")
        assert e._get_deps() == {"$nid1:"}

    async def test_eval(self, mock_num_port1, dummy_eval_context):
        """Should return the attribute value of the self port from the supplied context."""

        e = SelfPortAttr("nid1", prefix="$", role=Role.VALUE, attr_name="enabled")
        dummy_eval_context.port_attrs["nid1"] = {"enabled": True}
        assert await e._eval(dummy_eval_context) is True

    async def test_eval_string_nonempty(self, mock_num_port1, dummy_eval_context):
        """Should return 1 when the attribute is a non-empty string."""

        e = SelfPortAttr("nid1", prefix="$", role=Role.VALUE, attr_name="tag")
        dummy_eval_context.port_attrs["nid1"] = {"tag": "sensor"}
        assert await e._eval(dummy_eval_context) == 1

    async def test_eval_string_empty(self, mock_num_port1, dummy_eval_context):
        """Should return 0 when the attribute is an empty string."""

        e = SelfPortAttr("nid1", prefix="$", role=Role.VALUE, attr_name="tag")
        dummy_eval_context.port_attrs["nid1"] = {"tag": ""}
        assert await e._eval(dummy_eval_context) == 0

    async def test_eval_unknown(self, dummy_eval_context):
        """Should raise UnknownPortId when the self port doesn't exist."""

        e = SelfPortAttr("inexistent", prefix="$", role=Role.VALUE, attr_name="enabled")
        with pytest.raises(UnknownPortId) as exc_info:
            await e._eval(dummy_eval_context)
        assert exc_info.value.port_id == "inexistent"

    async def test_eval_unavailable(self, mock_num_port1, dummy_eval_context):
        """Should raise PortAttrUnavailable when the attribute is not present in the context."""

        e = SelfPortAttr("nid1", prefix="$", role=Role.VALUE, attr_name="nonexistent_attr")
        dummy_eval_context.port_attrs["nid1"] = {}
        with pytest.raises(PortAttrUnavailable) as exc_info:
            await e._eval(dummy_eval_context)
        assert exc_info.value.port_id == "nid1"
        assert exc_info.value.attr_name == "nonexistent_attr"
