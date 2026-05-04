import pytest

from qtoggleserver.core.expressions import Role, parse
from qtoggleserver.core.expressions.devices import MainDeviceAttr, SlaveDeviceAttr
from qtoggleserver.core.expressions.exceptions import DeviceAttrUnavailable


class TestMainDeviceAttr:
    def test_parse(self):
        """Should parse `#:attr_name` into a MainDeviceAttr with device_name=None."""

        e = parse(None, "#:display_name", role=Role.VALUE)
        assert isinstance(e, MainDeviceAttr)
        assert e.device_name is None
        assert e.attr_name == "display_name"

    def test_deps(self):
        """Should return `{'#:'}` as a dependency."""

        e = MainDeviceAttr(prefix="#", role=Role.VALUE, attr_name="display_name")
        assert e._get_deps() == {"#:"}

    async def test_eval(self, dummy_eval_context):
        """Should return the attribute value from the supplied context."""

        e = MainDeviceAttr(prefix="#", role=Role.VALUE, attr_name="main_test_attr")
        dummy_eval_context.device_attrs["main_test_attr"] = "My Device"
        assert await e._eval(dummy_eval_context) == "My Device"

    async def test_eval_unavailable(self, dummy_eval_context):
        """Should raise DeviceAttrUnavailable when the attribute is not present in the context."""

        e = MainDeviceAttr(prefix="#", role=Role.VALUE, attr_name="nonexistent_main_attr")
        with pytest.raises(DeviceAttrUnavailable) as exc_info:
            await e._eval(dummy_eval_context)
        assert exc_info.value.device_name == ""
        assert exc_info.value.attr_name == "nonexistent_main_attr"

    def test_str(self):
        """Should serialise back to the original expression syntax."""

        e = MainDeviceAttr(prefix="#", role=Role.VALUE, attr_name="display_name")
        assert str(e) == "#:display_name"


class TestSlaveDeviceAttr:
    def test_parse(self):
        """Should parse `#slave_name:attr_name` into a SlaveDeviceAttr."""

        e = parse(None, "#slave1:display_name", role=Role.VALUE)
        assert isinstance(e, SlaveDeviceAttr)
        assert e.device_name == "slave1"
        assert e.attr_name == "display_name"

    def test_deps(self):
        """Should return `{'#slave_name:'}` as a dependency."""

        e = SlaveDeviceAttr("slave1", prefix="#", role=Role.VALUE, attr_name="display_name")
        assert e._get_deps() == {"#slave1:"}

    async def test_eval(self, dummy_eval_context):
        """Should return the attribute value using a `slave_name.attr_name` key in the context."""

        e = SlaveDeviceAttr("slave1", prefix="#", role=Role.VALUE, attr_name="display_name")
        dummy_eval_context.device_attrs["slave1:display_name"] = "Slave Device"
        assert await e._eval(dummy_eval_context) == "Slave Device"

    async def test_eval_unavailable(self, dummy_eval_context):
        """Should raise DeviceAttrUnavailable when the attribute is not present in the context."""

        e = SlaveDeviceAttr("slave1", prefix="#", role=Role.VALUE, attr_name="nonexistent_slave_attr")
        with pytest.raises(DeviceAttrUnavailable) as exc_info:
            await e._eval(dummy_eval_context)
        assert exc_info.value.device_name == "slave1"
        assert exc_info.value.attr_name == "nonexistent_slave_attr"

    def test_str(self):
        """Should serialise back to the original expression syntax."""

        e = SlaveDeviceAttr("slave1", prefix="#", role=Role.VALUE, attr_name="display_name")
        assert str(e) == "#slave1:display_name"
