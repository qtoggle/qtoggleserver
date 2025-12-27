import hashlib

from datetime import timedelta
from unittest import mock

import pytest

from qtoggleserver.core import api as core_api
from qtoggleserver.core.device import attrs as device_attrs
from qtoggleserver.core.typing import Attribute


class MockAttrDefDriver(device_attrs.AttrDefDriver):
    async def get_value(self) -> Attribute:
        return 13


class TestAttrDefDriver:
    def test_get_display_name(self):
        """Should return the `DISPLAY_NAME` class attribute."""

        attrdef_driver = MockAttrDefDriver()
        attrdef_driver.DISPLAY_NAME = "dummy_display_name"
        assert attrdef_driver.get_display_name() == "dummy_display_name"

    def test_get_description(self):
        """Should return the `DESCRIPTION` class attribute."""

        attrdef_driver = MockAttrDefDriver()
        attrdef_driver.DESCRIPTION = "dummy_description"
        assert attrdef_driver.get_description() == "dummy_description"

    def test_get_type(self):
        """Should return the `TYPE` class attribute."""

        attrdef_driver = MockAttrDefDriver()
        attrdef_driver.TYPE = "string"
        assert attrdef_driver.get_type() == "string"

    def test_is_modifiable(self):
        """Should return the `MODIFIABLE` class attribute."""

        attrdef_driver = MockAttrDefDriver()
        attrdef_driver.MODIFIABLE = True
        assert attrdef_driver.is_modifiable()

    def test_get_unit(self):
        """Should return the `UNIT` class attribute."""

        attrdef_driver = MockAttrDefDriver()
        attrdef_driver.UNIT = "dummy_unit"
        assert attrdef_driver.get_unit() == "dummy_unit"

    def test_get_min(self):
        """Should return the `MIN` class attribute."""

        attrdef_driver = MockAttrDefDriver()
        attrdef_driver.MIN = -123
        assert attrdef_driver.get_min() == -123

    def test_get_max(self):
        """Should return the `MAX` class attribute."""

        attrdef_driver = MockAttrDefDriver()
        attrdef_driver.MAX = 123
        assert attrdef_driver.get_max() == 123

    def test_is_integer(self):
        """Should return the `INTEGER` class attribute."""

        attrdef_driver = MockAttrDefDriver()
        attrdef_driver.INTEGER = True
        assert attrdef_driver.is_integer()

    def test_get_step(self):
        """Should return the `STEP` class attribute."""

        attrdef_driver = MockAttrDefDriver()
        attrdef_driver.STEP = 100
        assert attrdef_driver.get_step() == 100

    def test_get_choices(self):
        """Should return the `CHOICES` class attribute."""

        attrdef_driver = MockAttrDefDriver()
        choices = [{"value": 1, "display_name": "One"}, {"value": 2, "display_name": "Two"}]
        attrdef_driver.CHOICES = choices
        assert attrdef_driver.get_choices() == choices

    def test_get_pattern(self):
        """Should return the `PATTERN` class attribute."""

        attrdef_driver = MockAttrDefDriver()
        attrdef_driver.PATTERN = "^a-z$"
        assert attrdef_driver.get_pattern() == "^a-z$"

    def test_needs_reconnect(self):
        """Should return the `RECONNECT` class attribute."""

        attrdef_driver = MockAttrDefDriver()
        attrdef_driver.RECONNECT = True
        assert attrdef_driver.needs_reconnect()

    def test_is_enabled(self):
        """Should return `True` by default."""

        attrdef_driver = MockAttrDefDriver()
        assert attrdef_driver.is_enabled()

    def test_is_persisted(self):
        """Should return the `PERSISTED` class attribute."""

        attrdef_driver = MockAttrDefDriver()
        attrdef_driver.PERSISTED = True
        assert attrdef_driver.is_persisted()

    async def test_getter_first_call(self, mocker):
        """Should call `get_value()` to obtain the returned value."""

        attrdef_driver = MockAttrDefDriver()
        mocker.patch.object(attrdef_driver, "get_value", return_value=16)

        value = await attrdef_driver._getter()

        attrdef_driver.get_value.assert_awaited_once()
        assert value == 16

    async def test_getter_second_call_no_cache(self, mocker):
        """Should call `get_value()` a second time as well since the caching mechanism is disabled."""

        attrdef_driver = MockAttrDefDriver()
        mocker.patch.object(attrdef_driver, "get_value", return_value=16)
        await attrdef_driver._getter()
        attrdef_driver.get_value.reset_mock()

        value = await attrdef_driver._getter()

        attrdef_driver.get_value.assert_awaited_once()
        assert value == 16

    async def test_getter_second_call_cache(self, mocker, freezer, dummy_utc_datetime):
        """Should not call `get_value()` a second time, but reuse the cached value since the caching mechanism is
        enabled."""

        freezer.move_to(dummy_utc_datetime)
        attrdef_driver = MockAttrDefDriver()
        attrdef_driver.CACHE_LIFETIME = 1000
        mocker.patch.object(attrdef_driver, "get_value", return_value=16)
        await attrdef_driver._getter()
        attrdef_driver.get_value.reset_mock()

        freezer.move_to(dummy_utc_datetime + timedelta(seconds=999))
        value = await attrdef_driver._getter()

        attrdef_driver.get_value.assert_not_called()
        assert value == 16

    async def test_getter_second_call_cache_timeout(self, mocker, freezer, dummy_utc_datetime):
        """Should call `get_value()` a second time, as the cache expired."""

        freezer.move_to(dummy_utc_datetime)
        attrdef_driver = MockAttrDefDriver()
        attrdef_driver.CACHE_LIFETIME = 1000
        mocker.patch.object(attrdef_driver, "get_value", return_value=16)
        await attrdef_driver._getter()
        attrdef_driver.get_value.reset_mock()

        freezer.move_to(dummy_utc_datetime + timedelta(seconds=1001))
        value = await attrdef_driver._getter()

        attrdef_driver.get_value.assert_awaited_once_with()
        assert value == 16

    async def test_setter(self, mocker):
        """Should call `set_value()` with supplied value and invalidate cache."""

        attrdef_driver = MockAttrDefDriver()
        attrdef_driver._cached_timestamp = 1234
        mocker.patch.object(attrdef_driver, "set_value")

        await attrdef_driver._setter(16)

        attrdef_driver.set_value.assert_awaited_once_with(16)
        assert attrdef_driver._cached_timestamp == 0

    async def test_to_attrdef_all_set(self, mocker):
        """Should call all the getter methods to obtain various attribute definition fields. Should not call those that
        are meant to be called at runtime. Should return all fields."""

        choices = [{"value": 1, "display_name": "One"}, {"value": 2, "display_name": "Two"}]

        attrdef_driver = MockAttrDefDriver()
        mocker.patch.object(attrdef_driver, "is_enabled")
        mocker.patch.object(attrdef_driver, "get_display_name", return_value="dummy_display_name")
        mocker.patch.object(attrdef_driver, "get_description", return_value="dummy_description")
        mocker.patch.object(attrdef_driver, "get_type", return_value="string")
        mocker.patch.object(attrdef_driver, "is_modifiable", return_value=True)
        mocker.patch.object(attrdef_driver, "get_unit", return_value="dummy_unit")
        mocker.patch.object(attrdef_driver, "get_min", return_value=-123)
        mocker.patch.object(attrdef_driver, "get_max", return_value=123)
        mocker.patch.object(attrdef_driver, "is_integer", return_value=True)
        mocker.patch.object(attrdef_driver, "get_step", return_value=100)
        mocker.patch.object(attrdef_driver, "get_choices", return_value=choices)
        mocker.patch.object(attrdef_driver, "get_pattern", return_value="^a-z$")
        mocker.patch.object(attrdef_driver, "needs_reconnect", return_value=True)
        mocker.patch.object(attrdef_driver, "is_persisted", return_value=True)
        mocker.patch.object(attrdef_driver, "_getter")
        mocker.patch.object(attrdef_driver, "_setter")

        assert attrdef_driver.to_attrdef() == {
            "enabled": attrdef_driver.is_enabled,
            "display_name": "dummy_display_name",
            "description": "dummy_description",
            "type": "string",
            "modifiable": True,
            "unit": "dummy_unit",
            "min": -123,
            "max": 123,
            "integer": True,
            "step": 100,
            "choices": choices,
            "pattern": "^a-z$",
            "reconnect": True,
            "persisted": True,
            "getter": attrdef_driver._getter,
            "setter": attrdef_driver._setter,
        }

        attrdef_driver.is_enabled.assert_not_called()
        attrdef_driver.get_display_name.assert_called_once_with()
        attrdef_driver.get_description.assert_called_once_with()
        attrdef_driver.get_type.assert_called_once_with()
        attrdef_driver.is_modifiable.assert_called_once_with()
        attrdef_driver.get_unit.assert_called_once_with()
        attrdef_driver.get_min.assert_called_once_with()
        attrdef_driver.get_max.assert_called_once_with()
        attrdef_driver.is_integer.assert_called_once_with()
        attrdef_driver.get_step.assert_called_once_with()
        attrdef_driver.get_choices.assert_called_once_with()
        attrdef_driver.get_pattern.assert_called_once_with()
        attrdef_driver.needs_reconnect.assert_called_once_with()
        attrdef_driver.is_persisted.assert_called_once_with()
        attrdef_driver._getter.assert_not_called()
        attrdef_driver._setter.assert_not_called()

    async def test_to_attrdef_no_return_none(self):
        """Should call all the getter methods to obtain various attribute definition fields, but should leave out fields
        that are None."""

        attrdef_driver = MockAttrDefDriver()

        assert attrdef_driver.to_attrdef() == {
            "enabled": attrdef_driver.is_enabled,
            "type": "boolean",
            "modifiable": False,
            "getter": attrdef_driver._getter,
            "setter": attrdef_driver._setter,
        }


def test_attr_get_name_internal(mocker):
    """Should simply return the internal value of `name`."""

    mocker.patch.object(device_attrs, "name", "dummy1")
    assert device_attrs.attr_get_name() == "dummy1"


def test_attr_get_name_get_cmd(mocker):
    """Should call `run_get_cmd` with appropriate arguments to obtain the name and return it."""

    mocker.patch.object(device_attrs, "name", "dummy1")
    mocker.patch("qtoggleserver.conf.settings.core.device_name.get_cmd", "dummy get cmd")
    spy_run_get_cmd = mocker.patch("qtoggleserver.core.device.attrs.run_get_cmd", return_value={"name": "dummy2"})
    assert device_attrs.attr_get_name() == "dummy2"
    spy_run_get_cmd.assert_called_once_with("dummy get cmd", cmd_name="device name", required_fields=["name"])


def test_attr_set_name_internal(mocker):
    """Should simply update internal `name` value."""

    mocker.patch.object(device_attrs, "name", "old1")
    device_attrs.attr_set_name("new1")
    assert device_attrs.name == "new1"


def test_attr_set_name_set_cmd(mocker):
    """Should call `run_set_cmd` with new name and set command, while also updating internal `name` value."""

    mocker.patch.object(device_attrs, "name", "old1")
    mocker.patch("qtoggleserver.conf.settings.core.device_name.set_cmd", "dummy set cmd")
    spy_run_set_cmd = mocker.patch("qtoggleserver.core.device.attrs.run_set_cmd")
    device_attrs.attr_set_name("new1")
    assert device_attrs.name == "new1"
    spy_run_set_cmd.assert_called_once_with("dummy set cmd", cmd_name="device name", name="new1")


def test_attr_get_display_name(mocker):
    """Should return the value of the internal `display_name`."""

    mocker.patch.object(device_attrs, "display_name", "dummy1")
    assert device_attrs.attr_get_display_name() == "dummy1"


def test_attr_set_display_name(mocker):
    """Should update the internal `display_name` value."""

    mocker.patch.object(device_attrs, "display_name", "old1")
    device_attrs.attr_set_display_name("new1")
    assert device_attrs.display_name == "new1"


def test_attr_get_api_version():
    """Should return the correct API version."""

    assert device_attrs.attr_get_api_version() == core_api.API_VERSION


def test_attr_get_flags_default():
    """Should return the list of flags enabled by default."""

    assert device_attrs.attr_get_flags() == ["expressions", "backup", "listen", "master", "sequences", "tls"]


def test_attr_get_flags_firmware(mocker):
    """Should return `firmware` flag."""

    mocker.patch("qtoggleserver.conf.settings.system.fwupdate.driver", "dummy")
    assert "firmware" in device_attrs.attr_get_flags()


def test_attr_get_flags_backup(mocker):
    """Should not return `backup` flag."""

    mocker.patch("qtoggleserver.conf.settings.core.backup_support", False)
    assert "backup" not in device_attrs.attr_get_flags()


def test_attr_get_flags_history(mocker):
    """Should return `history` flag."""

    mocker.patch("qtoggleserver.core.history.is_enabled", return_value=True)
    assert "history" in device_attrs.attr_get_flags()


def test_attr_get_flags_listen(mocker):
    """Should not return `listen` flag."""

    mocker.patch("qtoggleserver.conf.settings.core.listen_support", False)
    assert "listen" not in device_attrs.attr_get_flags()


def test_attr_get_flags_master(mocker):
    """Should not return `master` flag."""

    mocker.patch("qtoggleserver.conf.settings.slaves.enabled", False)
    assert "master" not in device_attrs.attr_get_flags()


def test_attr_get_flags_sequences(mocker):
    """Should not return `sequences` flag."""

    mocker.patch("qtoggleserver.conf.settings.core.sequences_support", False)
    assert "sequences" not in device_attrs.attr_get_flags()


def test_attr_get_flags_tls(mocker):
    """Should not return `tls` flag."""

    mocker.patch("qtoggleserver.conf.settings.core.tls_support", False)
    assert "tls" not in device_attrs.attr_get_flags()


def test_attr_get_password_empty(mocker):
    """Should return empty string due to password being unset."""

    mocker.patch("qtoggleserver.core.device.attrs.admin_password_hash", device_attrs.EMPTY_PASSWORD_HASH)
    assert device_attrs.attr_get_password("admin") == ""


def test_attr_get_password_set(mocker):
    """Should return string `set` due to password being set."""

    mocker.patch("qtoggleserver.core.device.attrs.admin_password_hash", "dummy1234")
    assert device_attrs.attr_get_password("admin") == "set"


def test_attr_get_password_unknown_user():
    """Should raise exception due to unknown user."""

    with pytest.raises(AttributeError):
        device_attrs.attr_get_password("unknown")


def test_attr_set_password_internal(mocker):
    """Should set internal value hash to corresponding password hash."""

    mocker.patch("qtoggleserver.core.device.attrs.admin_password_hash", "old1")
    device_attrs.attr_set_password("admin", "new1")
    assert device_attrs.admin_password_hash == hashlib.sha256(b"new1").hexdigest()


def test_attr_set_password_internal_empty(mocker):
    """Should set internal value hash to empty password hash."""

    mocker.patch("qtoggleserver.core.device.attrs.admin_password_hash", "old1")
    device_attrs.attr_set_password("admin", "")
    assert device_attrs.admin_password_hash == device_attrs.EMPTY_PASSWORD_HASH


def test_attr_set_password_set_cmd(mocker):
    """Should call `run_set_cmd` with password and set command, while also updating internal value hash."""

    mocker.patch("qtoggleserver.core.device.attrs.admin_password_hash", "old1")
    mocker.patch("qtoggleserver.conf.settings.core.passwords.set_cmd", "dummy set cmd")
    spy_run_set_cmd = mocker.patch("qtoggleserver.core.device.attrs.run_set_cmd")
    device_attrs.attr_set_password("admin", "new1")
    assert device_attrs.admin_password_hash == hashlib.sha256(b"new1").hexdigest()
    spy_run_set_cmd.assert_called_once_with(
        "dummy set cmd", cmd_name="password", username="admin", password="new1", log_values=False
    )


def test_get_attrdefs_first_call(mocker):
    """Should initialize attrdefs, calling callable fields, filtering out disabled attributes and returning the resulted
    dictionary."""

    mocker.patch.object(device_attrs, "_attrdefs", None)
    attrdefs = device_attrs.get_attrdefs()
    assert attrdefs is not None
    assert isinstance(attrdefs, dict)

    for attrdef in attrdefs.values():
        # 'enabled' should not be returned, but rather corresponding attrdefs should be filtered out
        assert "enabled" not in attrdef
        assert not callable(attrdef.get("modifiable"))
        assert not callable(attrdef.get("min"))
        assert not callable(attrdef.get("max"))


def test_get_attrdefs_subsequent_call(mocker):
    """Should return cached _attrdefs module member, without initializing attrdefs again."""

    attrdefs_mock = mocker.patch.object(device_attrs, "_attrdefs")
    assert device_attrs.get_attrdefs() is attrdefs_mock


def test_get_schema_first_call():
    """Should initialize a JSON schema corresponding to device attribute definitions and return it. The schema should
    not contain attribute definition metadata."""

    schema = device_attrs.get_schema()
    assert isinstance(schema, dict)
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False

    properties = schema["properties"]
    assert isinstance(properties, dict)
    assert "name" in properties

    for prop in properties.values():
        for attr in ["min", "max", "choices", "step", "modifiable", "standard", "getter", "setter", "reconnect"]:
            assert attr not in prop


def test_get_schema_subsequent_call(mocker):
    """Should return cached _schema module member, without initializing schema again."""

    schema_mock = mocker.patch.object(device_attrs, "_schema")
    assert device_attrs.get_schema() is schema_mock


def test_get_schema_loose(mocker):
    """Should return device attribute definitions JSON schema with additional properties allowed. Should not use or
    update cached schema."""

    cached_schema = device_attrs._schema
    schema_mock = mocker.patch.object(device_attrs, "_schema")
    schema = device_attrs.get_schema(loose=True)
    assert schema is not schema_mock
    assert schema is not cached_schema

    assert isinstance(schema, dict)
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is True


async def test_get_attrs(mocker):
    """Should call `get_attrdefs`, prepare and return a dictionary of corresponding device attributes by calling the
    getter of each attribute definition."""

    call_count34 = 0

    async def call5():
        return "dummy5"

    async def call34():
        nonlocal call_count34
        call_count34 += 1
        return {"key3": "dummy3", "key4": "dummy4"}

    mocker.patch.object(
        device_attrs,
        "get_attrdefs",
        return_value={
            "name1": {
                "type": "string",
                "getter": lambda: "dummy1",
            },
            "name2": {
                "type": "string",
                "getter": {
                    "call": lambda: "dummy2",
                    "transform": lambda v: v + " transformed",
                },
            },
            "name3": {
                "type": "string",
                "getter": {
                    "call": call34,
                    "key": "key3",
                },
            },
            "name4": {
                "type": "string",
                "getter": {
                    "call": call34,
                    "key": "key4",
                    "transform": lambda v: v + " transformed",
                },
            },
            "name5": {
                "type": "string",
                "getter": call5,
            },
        },
    )

    attrs = await device_attrs.get_attrs()
    assert attrs == {
        "name1": "dummy1",
        "name2": "dummy2 transformed",
        "name3": "dummy3",
        "name4": "dummy4 transformed",
        "name5": "dummy5",
    }
    assert call_count34 == 1  # call result should be cached instead of being called once for each attribute


async def test_set_attrs(mocker):
    """Should obtain the attrdef of corresponding to each supplied attribute and call the associated setter; should
    return False, indicating that no reboot is required."""

    call1 = mock.MagicMock()
    call2 = mock.MagicMock()

    call_count34 = 0

    async def call34(key3: str, key4: str):
        nonlocal call_count34
        call_count34 += 1
        assert key3 == "dummy3"
        assert key4 == "dummy4 transformed"

    async def call5(value: str):
        assert value == "dummy5"

    mocker.patch.object(
        device_attrs,
        "get_attrdefs",
        return_value={
            "name1": {
                "type": "string",
                "modifiable": True,
                "getter": mock.MagicMock(),
                "setter": call1,
            },
            "name2": {
                "type": "string",
                "modifiable": True,
                "getter": mock.MagicMock(),
                "setter": {
                    "call": call2,
                    "transform": lambda v: v + " transformed",
                },
            },
            "name3": {
                "type": "string",
                "modifiable": True,
                "getter": mock.MagicMock(),
                "setter": {
                    "call": call34,
                    "key": "key3",
                },
            },
            "name4": {
                "type": "string",
                "modifiable": True,
                "getter": mock.MagicMock(),
                "setter": {
                    "call": call34,
                    "key": "key4",
                    "transform": lambda v: v + " transformed",
                },
            },
            "name5": {
                "type": "string",
                "modifiable": True,
                "getter": mock.MagicMock(),
                "setter": call5,
            },
        },
    )

    result = await device_attrs.set_attrs(
        {
            "name1": "dummy1",
            "name2": "dummy2",
            "name3": "dummy3",
            "name4": "dummy4",
            "name5": "dummy5",
        }
    )
    assert result is False  # reboot not required
    assert call_count34 == 1

    call1.assert_called_once_with("dummy1")
    call2.assert_called_once_with("dummy2 transformed")


async def test_set_attrs_reboot(mocker):
    """Should return True, indicating that reboot is required, if at least one of the supplied attributes has the
    `reconnect` field set."""

    mocker.patch.object(
        device_attrs,
        "get_attrdefs",
        return_value={
            "name1": {
                "type": "string",
                "modifiable": True,
                "getter": mock.MagicMock(),
                "setter": mock.MagicMock(),
            },
            "name2": {
                "type": "string",
                "modifiable": True,
                "reconnect": True,
                "getter": mock.MagicMock(),
                "setter": mock.MagicMock(),
            },
        },
    )

    result = await device_attrs.set_attrs(
        {
            "name1": "dummy1",
            "name2": "dummy2",
        }
    )
    assert result is True  # reboot required


async def test_set_attrs_ignore_extra(mocker):
    """Should raise exception when supplying an undefined attribute and `ignore_extra` is set to false; Should silently
    ignore undefined attribute when `ignore_extra` is set to true."""

    mocker.patch.object(
        device_attrs,
        "get_attrdefs",
        return_value={
            "name1": {
                "type": "string",
                "modifiable": True,
                "getter": mock.MagicMock(),
                "setter": mock.MagicMock(),
            },
            "name2": {
                "type": "string",
                "modifiable": True,
                "reconnect": True,
                "getter": mock.MagicMock(),
                "setter": mock.MagicMock(),
            },
        },
    )

    with pytest.raises(device_attrs.DeviceAttributeError) as e:
        await device_attrs.set_attrs(
            {
                "name1": "dummy1",
                "inexistent": "dummy2",
            }
        )

        assert e.error == "no-such-attribute"
        assert e.attribute == "inexistent"

    await device_attrs.set_attrs(
        {
            "name1": "dummy1",
            "inexistent": "dummy2",
        },
        ignore_extra=True,
    )


async def test_set_attrs_not_modifiable(mocker):
    """Should raise exception when supplying an attribute that is not modifiable."""

    mocker.patch.object(
        device_attrs,
        "get_attrdefs",
        return_value={
            "name1": {
                "type": "string",
                "modifiable": True,
                "getter": mock.MagicMock(),
                "setter": mock.MagicMock(),
            },
            "name2": {
                "type": "string",
                "modifiable": False,
                "getter": mock.MagicMock(),
                "setter": mock.MagicMock(),
            },
        },
    )

    with pytest.raises(device_attrs.DeviceAttributeError) as e:
        await device_attrs.set_attrs(
            {
                "name1": "dummy1",
                "name2": "dummy2",
            }
        )

        assert e.error == "attribute-not-modifiable"
        assert e.attribute == "name2"


async def test_to_json(mocker):
    """Should return a dictionary with all attribute values along with their definitions, for non-standard ones."""

    mocker.patch.object(
        device_attrs,
        "get_attrdefs",
        return_value={
            "name1": {
                "type": "string",
                "modifiable": True,
                "pattern": "^.*$",
                "reconnect": False,
                "getter": lambda: "dummy1",
                "standard": False,
                "choices": [
                    {"display_name": "Choice 1", "value": "choice1"},
                    {"display_name": "Choice 2", "value": "choice2"},
                ],
            },
            "name2": {
                "type": "number",
                "pattern": "^.*$",
                "reconnect": False,
                "modifiable": False,
                "getter": lambda: 2,
                "standard": True,
            },
            "name3": {
                "type": "boolean",
                "pattern": "^.*$",
                "reconnect": False,
                "modifiable": False,
                "getter": lambda: True,
                "standard": False,
            },
        },
    )

    result = await device_attrs.to_json()
    assert result == {
        "name1": "dummy1",
        "name2": 2,
        "name3": True,
        "definitions": {
            "name1": {
                "type": "string",
                "modifiable": True,
                "pattern": "^.*$",
                "choices": [
                    {"display_name": "Choice 1", "value": "choice1"},
                    {"display_name": "Choice 2", "value": "choice2"},
                ],
            },
            "name3": {
                "type": "boolean",
                "modifiable": False,
                "pattern": "^.*$",
            },
        },
    }


class TestLoadDynamicAttrDef:
    def test_successful_load(self, mocker):
        """Should successfully load a dynamic attribute definition from a valid driver class."""

        mock_driver_instance = mocker.Mock(spec=device_attrs.AttrDefDriver)
        mock_attrdef = {
            "type": "string",
            "modifiable": True,
            "getter": mocker.Mock(),
            "setter": mocker.Mock(),
        }
        mock_driver_instance.to_attrdef.return_value = mock_attrdef

        mock_driver_class = mocker.Mock(return_value=mock_driver_instance)
        spy_load_attr = mocker.patch(
            "qtoggleserver.utils.dynload.load_attr",
            return_value=mock_driver_class,
        )

        params = {"driver": "module.path.DriverClass", "param1": "value1", "param2": "value2"}
        result = device_attrs.load_dynamic_attrdef("test_attr", params)

        spy_load_attr.assert_called_once_with("module.path.DriverClass")
        mock_driver_class.assert_called_once_with(param1="value1", param2="value2")
        mock_driver_instance.to_attrdef.assert_called_once()
        assert result == mock_attrdef

    def test_successful_load_no_params(self, mocker):
        """Should successfully load a dynamic attribute definition without additional parameters."""

        mock_driver_instance = mocker.Mock(spec=device_attrs.AttrDefDriver)
        mock_attrdef = {"type": "boolean", "getter": mocker.Mock()}
        mock_driver_instance.to_attrdef.return_value = mock_attrdef

        mock_driver_class = mocker.Mock(return_value=mock_driver_instance)
        spy_load_attr = mocker.patch(
            "qtoggleserver.utils.dynload.load_attr",
            return_value=mock_driver_class,
        )

        params = {"driver": "module.path.DriverClass"}
        result = device_attrs.load_dynamic_attrdef("test_attr", params)

        spy_load_attr.assert_called_once_with("module.path.DriverClass")
        mock_driver_class.assert_called_once_with()
        assert result == mock_attrdef

    def test_driver_not_found(self, mocker):
        """Should raise `NoSuchDriver` exception when the driver class cannot be loaded."""

        spy_load_attr = mocker.patch(
            "qtoggleserver.utils.dynload.load_attr",
            side_effect=AttributeError("Module not found"),
        )

        params = {"driver": "module.path.NonExistentDriver"}

        with pytest.raises(device_attrs.NoSuchDriver) as exc_info:
            device_attrs.load_dynamic_attrdef("test_attr", params)

        assert str(exc_info.value) == "module.path.NonExistentDriver"
        spy_load_attr.assert_called_once_with("module.path.NonExistentDriver")

    def test_import_error(self, mocker):
        """Should raise NoSuchDriver exception when the driver module fails to import."""

        spy_load_attr = mocker.patch(
            "qtoggleserver.utils.dynload.load_attr",
            side_effect=ImportError("Cannot import module"),
        )

        params = {"driver": "module.path.DriverClass"}

        with pytest.raises(device_attrs.NoSuchDriver):
            device_attrs.load_dynamic_attrdef("test_attr", params)

        spy_load_attr.assert_called_once()

    def test_params_not_mutated(self, mocker):
        """Should not mutate the original params dictionary."""

        mock_driver_instance = mocker.Mock(spec=device_attrs.AttrDefDriver)
        mock_driver_instance.to_attrdef.return_value = {}
        mock_driver_class = mocker.Mock(return_value=mock_driver_instance)
        mocker.patch("qtoggleserver.utils.dynload.load_attr", return_value=mock_driver_class)

        original_params = {"driver": "module.path.DriverClass", "param1": "value1"}
        params_copy = dict(original_params)

        device_attrs.load_dynamic_attrdef("test_attr", original_params)

        assert original_params == params_copy


class TestLoadDynamicAttrDefs:
    def test_load_multiple_attrdefs(self, mocker):
        """Should successfully load multiple dynamic attribute definitions from configuration."""

        mock_driver_instance1 = mocker.Mock(spec=device_attrs.AttrDefDriver)
        mock_attrdef1 = {"type": "string", "getter": mocker.Mock()}
        mock_driver_instance1.to_attrdef.return_value = mock_attrdef1

        mock_driver_instance2 = mocker.Mock(spec=device_attrs.AttrDefDriver)
        mock_attrdef2 = {"type": "number", "getter": mocker.Mock()}
        mock_driver_instance2.to_attrdef.return_value = mock_attrdef2

        mock_driver_class1 = mocker.Mock(return_value=mock_driver_instance1)
        mock_driver_class2 = mocker.Mock(return_value=mock_driver_instance2)

        def load_attr_side_effect(class_path):
            if class_path == "module.Driver1":
                return mock_driver_class1
            elif class_path == "module.Driver2":
                return mock_driver_class2
            else:
                return None

        spy_load_attr = mocker.patch(
            "qtoggleserver.utils.dynload.load_attr",
            side_effect=load_attr_side_effect,
        )

        mocker.patch(
            "qtoggleserver.conf.settings.core.device_attrs",
            [
                {"name": "attr1", "driver": "module.Driver1", "param": "value1"},
                {"name": "attr2", "driver": "module.Driver2", "param": "value2"},
            ],
        )

        result = device_attrs.load_dynamic_attrdefs()

        assert len(result) == 2
        assert "attr1" in result
        assert "attr2" in result
        assert result["attr1"] == mock_attrdef1
        assert result["attr2"] == mock_attrdef2

        assert spy_load_attr.call_count == 2
        mock_driver_class1.assert_called_once_with(param="value1")
        mock_driver_class2.assert_called_once_with(param="value2")

    def test_load_empty_config(self, mocker):
        """Should return an empty dictionary when no dynamic attributes are configured."""

        mocker.patch("qtoggleserver.conf.settings.core.device_attrs", [])

        result = device_attrs.load_dynamic_attrdefs()

        assert result == {}

    def test_skip_failed_attribute(self, mocker):
        """Should log error and skip attributes that fail to load, but continue loading others."""

        mock_driver_instance = mocker.Mock(spec=device_attrs.AttrDefDriver)
        mock_attrdef = {"type": "boolean", "getter": mocker.Mock()}
        mock_driver_instance.to_attrdef.return_value = mock_attrdef
        mock_driver_class = mocker.Mock(return_value=mock_driver_instance)

        def load_attr_side_effect(class_path):
            if class_path == "module.FailingDriver":
                raise ImportError("Cannot import module")
            return mock_driver_class

        mocker.patch("qtoggleserver.utils.dynload.load_attr", side_effect=load_attr_side_effect)

        mocker.patch(
            "qtoggleserver.conf.settings.core.device_attrs",
            [
                {"name": "attr1", "driver": "module.FailingDriver"},
                {"name": "attr2", "driver": "module.WorkingDriver"},
            ],
        )

        spy_logger_error = mocker.patch("qtoggleserver.core.device.attrs.logger.error")

        result = device_attrs.load_dynamic_attrdefs()

        assert len(result) == 1
        assert "attr2" in result
        assert "attr1" not in result
        assert result["attr2"] == mock_attrdef

        spy_logger_error.assert_called_once()
        assert "attr1" in str(spy_logger_error.call_args[0])

    def test_all_attributes_fail(self, mocker):
        """Should return an empty dictionary and log errors when all attributes fail to load."""

        mocker.patch(
            "qtoggleserver.utils.dynload.load_attr",
            side_effect=ImportError("Cannot import module"),
        )

        mocker.patch(
            "qtoggleserver.conf.settings.core.device_attrs",
            [
                {"name": "attr1", "driver": "module.Driver1"},
                {"name": "attr2", "driver": "module.Driver2"},
            ],
        )

        spy_logger_error = mocker.patch("qtoggleserver.core.device.attrs.logger.error")

        result = device_attrs.load_dynamic_attrdefs()

        assert result == {}
        assert spy_logger_error.call_count == 2

    def test_original_config_not_mutated(self, mocker):
        """Should not mutate the original configuration items."""

        mock_driver_instance = mocker.Mock(spec=device_attrs.AttrDefDriver)
        mock_driver_instance.to_attrdef.return_value = {}
        mock_driver_class = mocker.Mock(return_value=mock_driver_instance)
        mocker.patch("qtoggleserver.utils.dynload.load_attr", return_value=mock_driver_class)

        original_config = [
            {"name": "attr1", "driver": "module.Driver1", "param": "value1"},
        ]
        config_copy = [dict(item) for item in original_config]

        mocker.patch("qtoggleserver.conf.settings.core.device_attrs", original_config)

        device_attrs.load_dynamic_attrdefs()

        assert original_config == config_copy
