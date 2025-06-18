import importlib
import logging

from qtoggleserver import persist
from qtoggleserver.utils import json as json_utils

from . import attrs as device_attrs


_PERSISTED_MODULE_ATTRS = ["admin_password_hash", "normal_password_hash", "viewonly_password_hash"]

logger = logging.getLogger(__name__)


def get_display_name() -> str:
    # Used by template notifications
    return device_attrs.display_name or device_attrs.name


async def load() -> None:
    data = await persist.get_value("device", default={})

    # Load persisted module attributes
    for name in _PERSISTED_MODULE_ATTRS:
        value = data.get(name)
        if value is None:
            continue

        # A few attributes may carry sensitive information, so treat them separately and do not log their values
        if name.count("password") or name == "wifi_key":
            logger.debug("loaded %s", name)
        else:
            logger.debug("loaded %s = %s", name, json_utils.dumps(value))

        setattr(device_attrs, name, value)

    # Load persisted device attributes
    attrdefs = device_attrs.get_attrdefs()
    attrs = {}
    for name, attrdef in attrdefs.items():
        if attrdef.get("persisted") and data.get(name) is not None:
            attrs[name] = data[name]
    if attrs:
        await device_attrs.set_attrs(attrs)

    # Hash empty passwords
    if not device_attrs.admin_password_hash:
        device_attrs.admin_password_hash = device_attrs.EMPTY_PASSWORD_HASH
    if not device_attrs.normal_password_hash:
        device_attrs.normal_password_hash = device_attrs.EMPTY_PASSWORD_HASH
    if not device_attrs.viewonly_password_hash:
        device_attrs.viewonly_password_hash = device_attrs.EMPTY_PASSWORD_HASH


async def save() -> None:
    data = {name: getattr(device_attrs, name) for name in _PERSISTED_MODULE_ATTRS}

    attrdefs = device_attrs.get_attrdefs()
    attrs = await device_attrs.get_attrs()
    for name, attrdef in attrdefs.items():
        if attrdef.get("persisted") and attrs.get(name) is not None:
            data[name] = attrs[name]

    logger.debug("saving persisted data")
    await persist.set_value("device", data)


async def reset(preserve_attrs: list[str] | None = None) -> None:
    preserve_attrs = preserve_attrs or []

    preserved_attrs = {}
    for name in preserve_attrs:
        preserved_attrs[name] = getattr(device_attrs, name, None)

    logger.debug("clearing persisted data")
    await persist.remove("device")
    importlib.reload(device_attrs)  # reloads device attributes to default values

    for name, value in preserved_attrs.items():
        setattr(device_attrs, name, value)


async def init() -> None:
    logger.debug("loading persisted data")
    await load()

    logger.debug("initializing attributes")
    await device_attrs.init()


async def cleanup() -> None:
    logger.debug("cleaning up attributes")
    await device_attrs.cleanup()
