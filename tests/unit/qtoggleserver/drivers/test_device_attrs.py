import pytest

from qtoggleserver.core.device.exceptions import DeviceAttributeException
from qtoggleserver.drivers.device_attrs.cmdline import CmdLineAttrDef


class TestCmdLineAttrDef:
    def test_init_valid_types(self):
        """Should initialize with valid attribute types."""

        for type_ in ["boolean", "number", "string"]:
            attrdef = CmdLineAttrDef(
                display_name="Test Attr",
                description="Test description",
                type=type_,
                get_cmd="echo 'QS_VALUE=test'",
                set_cmd="echo 'set'",
            )
            assert attrdef.get_type() == type_

    def test_init_invalid_type(self):
        """Should raise `ValueError` when initialized with invalid type."""

        with pytest.raises(ValueError, match="Invalid attribute type"):
            CmdLineAttrDef(
                display_name="Test Attr",
                description="Test description",
                type="invalid_type",
                get_cmd="echo 'QS_VALUE=test'",
                set_cmd="echo 'set'",
            )

    def test_get_display_name(self):
        """Should return the display name provided during initialization."""

        attrdef = CmdLineAttrDef(
            display_name="Test Display Name",
            description="Test description",
            type="string",
            get_cmd="echo 'QS_VALUE=test'",
        )
        assert attrdef.get_display_name() == "Test Display Name"

    def test_get_description(self):
        """Should return the description provided during initialization."""

        attrdef = CmdLineAttrDef(
            display_name="Test Attr",
            description="Test Description Text",
            type="string",
            get_cmd="echo 'QS_VALUE=test'",
        )
        assert attrdef.get_description() == "Test Description Text"

    def test_get_type(self):
        """Should return the type provided during initialization."""

        attrdef = CmdLineAttrDef(
            display_name="Test Attr", description="Test description", type="number", get_cmd="echo 'QS_VALUE=123'"
        )
        assert attrdef.get_type() == "number"

    def test_is_modifiable_with_set_cmd(self):
        """Should return `True` when set_cmd is provided."""

        attrdef = CmdLineAttrDef(
            display_name="Test Attr",
            description="Test description",
            type="string",
            get_cmd="echo 'QS_VALUE=test'",
            set_cmd="echo 'set'",
        )
        assert attrdef.is_modifiable() is True

    def test_is_modifiable_without_set_cmd(self):
        """Should return `False` when `set_cmd` is not provided."""

        attrdef = CmdLineAttrDef(
            display_name="Test Attr", description="Test description", type="string", get_cmd="echo 'QS_VALUE=test'"
        )
        assert attrdef.is_modifiable() is False

    def test_get_cache_lifetime(self):
        """Should return the supplied `cache_lifetime` value."""

        attrdef = CmdLineAttrDef(
            display_name="Test Attr",
            description="Test description",
            type="string",
            get_cmd="echo 'QS_VALUE=test'",
            set_cmd="echo 'set'",
            cache_lifetime=12345,
        )
        assert attrdef.get_cache_lifetime() == 12345

    async def test_get_value_string(self, mocker):
        """Should execute `get_cmd` and return string value."""

        mocker.patch(
            "qtoggleserver.drivers.device_attrs.cmdline.run_get_cmd", return_value={"value": "test_string_value"}
        )

        attrdef = CmdLineAttrDef(
            display_name="Test Attr", description="Test description", type="string", get_cmd="echo 'QS_VALUE=test'"
        )
        value = await attrdef.get_value()

        assert value == "test_string_value"

    @pytest.mark.parametrize("str_value", ("true", "TRUE"))
    async def test_get_value_boolean_true(self, str_value, mocker):
        """Should execute `get_cmd` and return `True` for boolean type when value is "true" or "TRUE"."""

        mocker.patch("qtoggleserver.drivers.device_attrs.cmdline.run_get_cmd", return_value={"value": str_value})

        attrdef = CmdLineAttrDef(
            display_name="Test Attr", description="Test description", type="boolean", get_cmd="echo 'QS_VALUE=true'"
        )
        assert await attrdef.get_value() is True

    @pytest.mark.parametrize("str_value", ("false", "FALSE", "something else"))
    async def test_get_value_boolean_false(self, str_value, mocker):
        """Should execute get_cmd and return False for boolean type when value is not `true` or "TRUE"."""

        mocker.patch("qtoggleserver.drivers.device_attrs.cmdline.run_get_cmd", return_value={"value": str_value})

        attrdef = CmdLineAttrDef(
            display_name="Test Attr", description="Test description", type="boolean", get_cmd="echo 'QS_VALUE=false'"
        )
        assert await attrdef.get_value() is False

    async def test_get_value_number_int(self, mocker):
        """Should execute `get_cmd` and return integer value for number type."""

        mocker.patch("qtoggleserver.drivers.device_attrs.cmdline.run_get_cmd", return_value={"value": "42"})

        attrdef = CmdLineAttrDef(
            display_name="Test Attr", description="Test description", type="number", get_cmd="echo 'QS_VALUE=42'"
        )
        value = await attrdef.get_value()

        assert isinstance(value, int)
        assert value == 42

    async def test_get_value_number_float(self, mocker):
        """Should execute `get_cmd` and return float value for number type."""

        mocker.patch("qtoggleserver.drivers.device_attrs.cmdline.run_get_cmd", return_value={"value": "3.14"})

        attrdef = CmdLineAttrDef(
            display_name="Test Attr", description="Test description", type="number", get_cmd="echo 'QS_VALUE=3.14'"
        )
        assert await attrdef.get_value() == 3.14

    async def test_get_value_number_invalid(self, mocker):
        """Should return `None` for number type when value cannot be parsed."""

        mocker.patch("qtoggleserver.drivers.device_attrs.cmdline.run_get_cmd", return_value={"value": "not_a_number"})

        attrdef = CmdLineAttrDef(
            display_name="Test Attr",
            description="Test description",
            type="number",
            get_cmd="echo 'QS_VALUE=not_a_number'",
        )
        assert await attrdef.get_value() is None

    async def test_get_value_calls_run_get_cmd(self, mocker):
        """Should call `run_get_cmd` with correct parameters."""

        mock_run_get_cmd = mocker.patch(
            "qtoggleserver.drivers.device_attrs.cmdline.run_get_cmd", return_value={"value": "test"}
        )

        attrdef = CmdLineAttrDef(
            display_name="Test Attr",
            description="Test description",
            type="string",
            get_cmd="echo 'QS_VALUE=test'",
        )
        await attrdef.get_value()

        mock_run_get_cmd.assert_called_once_with(
            "echo 'QS_VALUE=test'",
            cmd_name="attrdef getter",
            required_fields=["value"],
            exc_class=DeviceAttributeException,
        )

    async def test_set_value_calls_run_set_cmd(self, mocker):
        """Should call `run_set_cmd` with correct parameters."""

        mock_run_set_cmd = mocker.patch("qtoggleserver.drivers.device_attrs.cmdline.run_set_cmd")

        attrdef = CmdLineAttrDef(
            display_name="Test Attr",
            description="Test description",
            type="string",
            get_cmd="echo 'QS_VALUE=test'",
            set_cmd="echo 'set'",
        )
        await attrdef.set_value("new_value")

        mock_run_set_cmd.assert_called_once_with(
            "echo 'set'",
            cmd_name="attrdef setter",
            exc_class=DeviceAttributeException,
            value="new_value",
        )

    async def test_set_value_with_number(self, mocker):
        """Should pass number value to `run_set_cmd`."""

        mock_run_set_cmd = mocker.patch("qtoggleserver.drivers.device_attrs.cmdline.run_set_cmd")

        attrdef = CmdLineAttrDef(
            display_name="Test Attr",
            description="Test description",
            type="number",
            get_cmd="echo 'QS_VALUE=42'",
            set_cmd="echo 'set'",
        )
        await attrdef.set_value(3.14)

        mock_run_set_cmd.assert_called_once_with(
            "echo 'set'",
            cmd_name="attrdef setter",
            exc_class=DeviceAttributeException,
            value="3.14",
        )

    async def test_set_value_with_boolean(self, mocker):
        """Should pass boolean value to `run_set_cmd`."""

        mock_run_set_cmd = mocker.patch("qtoggleserver.drivers.device_attrs.cmdline.run_set_cmd")

        attrdef = CmdLineAttrDef(
            display_name="Test Attr",
            description="Test description",
            type="boolean",
            get_cmd="echo 'QS_VALUE=true'",
            set_cmd="echo 'set'",
        )
        await attrdef.set_value(True)

        mock_run_set_cmd.assert_called_once()
        mock_run_set_cmd.assert_called_once_with(
            "echo 'set'",
            cmd_name="attrdef setter",
            exc_class=DeviceAttributeException,
            value="true",
        )
