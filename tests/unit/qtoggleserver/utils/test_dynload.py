import pytest

from qtoggleserver.utils import dynload


class TestLoadAttr:
    def test_loads_existing_attr(self):
        cls = dynload.load_attr("tests.unit.qtoggleserver.mock.peripherals.MockPeripheral")

        from tests.unit.qtoggleserver.mock.peripherals import MockPeripheral

        assert cls is MockPeripheral

    def test_no_such_module_raises_no_such_module(self):
        with pytest.raises(dynload.NoSuchModule) as exc_info:
            dynload.load_attr("tests.unit.qtoggleserver.mock.no_such_module.SomeClass")

        assert isinstance(exc_info.value, dynload.DynloadError)

    def test_no_such_attr_raises_no_such_attribute(self):
        with pytest.raises(dynload.NoSuchAttribute) as exc_info:
            dynload.load_attr("tests.unit.qtoggleserver.mock.peripherals.NoSuchClass")

        assert isinstance(exc_info.value, dynload.DynloadError)
