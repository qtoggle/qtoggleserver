import hashlib

from unittest import mock

import pytest

from qtoggleserver.core import api as core_api
from qtoggleserver.core.device import attrs as device_attrs


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
        for attr in ["min", "max", "choices", "modifiable", "standard", "getter", "setter", "reboot"]:
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
    """Should return True, indicating that reboot is required, if at least one of the supplied attributes requires
    reboot."""

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
                "reboot": True,
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
                "reboot": True,
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
                "reboot": False,
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
                "reboot": False,
                "modifiable": False,
                "getter": lambda: 2,
                "standard": True,
            },
            "name3": {
                "type": "boolean",
                "pattern": "^.*$",
                "reboot": False,
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
                "choices": [
                    {"display_name": "Choice 1", "value": "choice1"},
                    {"display_name": "Choice 2", "value": "choice2"},
                ],
            },
            "name3": {
                "type": "boolean",
                "modifiable": False,
            },
        },
    }
