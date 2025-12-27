import abc
import asyncio
import copy
import hashlib
import inspect
import logging
import re
import socket
import sys
import time

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from qtoggleserver import system, version
from qtoggleserver.conf import settings
from qtoggleserver.core.typing import Attribute, AttributeDefinition, AttributeDefinitions, Attributes, GenericJSONDict
from qtoggleserver.system import fwupdate
from qtoggleserver.utils import cache as cache_utils
from qtoggleserver.utils import dynload as dynload_utils
from qtoggleserver.utils import json as json_utils
from qtoggleserver.utils.cmd import run_get_cmd, run_set_cmd

from . import events as device_events
from .exceptions import DeviceAttributeError, NoSuchDriver


logger = logging.getLogger(__name__)


EMPTY_PASSWORD_HASH = hashlib.sha256(b"").hexdigest()
NETWORK_ATTRS_WATCH_INTERVAL = 5
ATTRDEF_CALLABLE_FIELDS = {"modifiable", "min", "max", "enabled"}


name: str = re.sub(r"[^a-zA-Z0-9_-]", "", socket.gethostname())
if not re.match("^[a-zA-Z_]", name):  # make sure name starts with a letter or underscore
    name = f"q{name}"
name = name[:32]

display_name: str = ""
admin_password_hash: str | None = None
normal_password_hash: str | None = None
viewonly_password_hash: str | None = None

_schema: GenericJSONDict | None = None
_attrdefs: AttributeDefinitions | None = None
_attrs_watch_task: asyncio.Task | None = None


class AttrDefDriver(metaclass=abc.ABCMeta):
    DISPLAY_NAME: str | None = None
    DESCRIPTION: str | None = None
    TYPE: str = "boolean"
    MODIFIABLE: bool = False
    UNIT: str | None = None
    MIN: float | None = None
    MAX: float | None = None
    INTEGER: bool = False
    STEP: float | None = None
    CHOICES: list[dict] | None = None
    PATTERN: str | None = None
    RECONNECT: bool = False

    PERSISTED: bool = False
    CACHE_LIFETIME: int = 0

    def __init__(self) -> None:
        self._cached_value: Attribute | None = None
        self._cached_timestamp: float = 0

    def get_display_name(self) -> str | None:
        return self.DISPLAY_NAME

    def get_description(self) -> str | None:
        return self.DESCRIPTION

    def get_type(self) -> str:
        return self.TYPE

    def is_modifiable(self) -> bool:
        return self.MODIFIABLE

    def get_unit(self) -> str | None:
        return self.UNIT

    def get_min(self) -> float | None:
        return self.MIN

    def get_max(self) -> float | None:
        return self.MAX

    def is_integer(self) -> bool:
        return self.INTEGER

    def get_step(self) -> float | None:
        return self.STEP

    def get_choices(self) -> list[dict] | None:
        return self.CHOICES

    def get_pattern(self) -> str | None:
        return self.PATTERN

    def needs_reconnect(self) -> bool:
        return self.RECONNECT

    def is_enabled(self) -> bool:
        return True

    def is_persisted(self) -> bool:
        return self.PERSISTED

    def get_cache_lifetime(self) -> int:
        return self.CACHE_LIFETIME

    @abc.abstractmethod
    async def get_value(self) -> Attribute:
        pass

    async def set_value(self, value: Attribute) -> None:
        # Not an abstract method as we don't implement this method for non-modifiable attributes
        pass

    async def _getter(self) -> Attribute:
        cache_lifetime = self.get_cache_lifetime()
        if (
            cache_lifetime > 0
            and self._cached_value is not None
            and time.time() - self._cached_timestamp < cache_lifetime
        ):
            return self._cached_value

        self._cached_value = await self.get_value()
        self._cached_timestamp = time.time()

        return self._cached_value

    async def _setter(self, value: Attribute) -> None:
        self._cached_timestamp = 0
        await self.set_value(value)

    def to_attrdef(self) -> AttributeDefinition:
        attrdef = {
            "enabled": self.is_enabled,  # intentionally supplied as callable
            "display_name": self.get_display_name(),
            "description": self.get_description(),
            "type": self.get_type(),
            "modifiable": self.is_modifiable(),
            "unit": self.get_unit(),
            "min": self.get_min(),
            "max": self.get_max(),
            "integer": self.is_integer() or None,
            "step": self.get_step(),
            "choices": self.get_choices(),
            "pattern": self.get_pattern(),
            "reconnect": self.needs_reconnect() or None,
            "persisted": self.is_persisted() or None,
            "getter": self._getter,
            "setter": self._setter,
        }

        # Keep only non-null fields
        return {k: v for k, v in attrdef.items() if v is not None}


def attr_get_name() -> str:
    global name
    if settings.core.device_name.get_cmd:
        result = run_get_cmd(settings.core.device_name.get_cmd, cmd_name="device name", required_fields=["name"])
        name = result["name"]

    return name


def attr_set_name(value: str) -> None:
    global name
    name = value

    if settings.core.device_name.set_cmd:
        run_set_cmd(settings.core.device_name.set_cmd, cmd_name="device name", name=value)


def attr_get_display_name() -> str:
    return display_name


def attr_set_display_name(value: str) -> None:
    global display_name
    display_name = value


@cache_utils.ttl_cached(ttl=60)
def attr_get_api_version() -> str:
    from qtoggleserver.core import api as core_api

    return core_api.API_VERSION


@cache_utils.ttl_cached(ttl=60)
async def attr_get_version() -> str:
    if settings.system.fwupdate.driver:
        return await fwupdate.get_current_version()
    else:
        return version.VERSION


@cache_utils.ttl_cached(ttl=60)
async def attr_is_auto_update_enabled() -> bool:
    if settings.system.fwupdate.driver:
        return await fwupdate.is_auto_update_enabled()
    else:
        return False


async def attr_set_auto_update_enabled(value: bool) -> None:
    if settings.system.fwupdate.driver:
        await fwupdate.set_auto_update_enabled(value)
        attr_is_auto_update_enabled.cache_clear()


def attr_get_flags() -> list[str]:
    from qtoggleserver.core import history as core_history

    flags = ["expressions"]
    if settings.system.fwupdate.driver:
        flags.append("firmware")

    if settings.core.backup_support:
        flags.append("backup")

    if core_history.is_enabled():
        flags.append("history")

    if settings.core.listen_support:
        flags.append("listen")

    if settings.slaves.enabled:
        flags.append("master")

    if settings.reverse.enabled:
        flags.append("reverse")

    if settings.core.sequences_support:
        flags.append("sequences")

    if settings.core.tls_support:
        flags.append("tls")

    if settings.webhooks.enabled:
        flags.append("webhooks")

    return flags


def attr_get_password(which: str) -> str:
    core_device_attrs = sys.modules[__name__]
    password_hash = getattr(core_device_attrs, f"{which}_password_hash")
    return ["set", ""][password_hash == EMPTY_PASSWORD_HASH]


def attr_set_password(which: str, value: str) -> None:
    # Call password set command, if available
    if settings.core.passwords.set_cmd:
        run_set_cmd(
            settings.core.passwords.set_cmd, cmd_name="password", log_values=False, username=which, password=value
        )

    core_device_attrs = sys.modules[__name__]
    password_hash = hashlib.sha256(value.encode()).hexdigest()
    setattr(core_device_attrs, f"{which}_password_hash", password_hash)


ATTRDEFS = {
    "name": {
        "type": "string",
        "modifiable": True,
        "min": 1,
        "max": 32,
        "pattern": r"^[_a-zA-Z][_a-zA-Z0-9-]{0,31}$",
        "standard": True,
        "persisted": True,
        "getter": attr_get_name,
        "setter": attr_set_name,
    },
    "display_name": {
        "type": "string",
        "modifiable": True,
        "max": 64,
        "standard": True,
        "persisted": True,
        "getter": attr_get_display_name,
        "setter": attr_set_display_name,
    },
    "version": {
        "type": "string",
        "standard": True,
        "getter": attr_get_version,
    },
    "firmware_auto_update": {
        "type": "boolean",
        "modifiable": True,
        "standard": True,
        "enabled": lambda: bool(settings.system.fwupdate.driver),
        "getter": attr_is_auto_update_enabled,
        "setter": attr_set_auto_update_enabled,
    },
    "api_version": {
        "type": "string",
        "standard": True,
        "getter": attr_get_api_version,
    },
    "vendor": {
        "type": "string",
        "standard": True,
        "getter": lambda: version.VENDOR,
    },
    "admin_password": {
        "type": "string",
        "modifiable": True,
        "max": 32,
        "standard": True,
        "getter": lambda: attr_get_password("admin"),
        "setter": lambda v: attr_set_password("admin", v),
    },
    "normal_password": {
        "type": "string",
        "modifiable": True,
        "max": 32,
        "standard": True,
        "getter": lambda: attr_get_password("normal"),
        "setter": lambda v: attr_set_password("normal", v),
    },
    "viewonly_password": {
        "type": "string",
        "modifiable": True,
        "max": 32,
        "standard": True,
        "getter": lambda: attr_get_password("viewonly"),
        "setter": lambda v: attr_set_password("viewonly", v),
    },
    "flags": {
        "type": ["string"],
        "standard": True,
        "getter": attr_get_flags,
    },
    "virtual_ports": {
        "type": "number",
        "standard": True,
        "enabled": lambda: bool(settings.core.virtual_ports),
        "getter": lambda: settings.core.virtual_ports,
    },
    "uptime": {
        "type": "number",
        "standard": True,
        "getter": system.uptime,
    },
    "date": {
        "type": "number",
        "modifiable": system.date.has_set_date_support,
        # mark as non-standard if no set support, to make attribute non-modifiable
        "standard": system.date.has_set_date_support,
        "enabled": system.date.has_real_date_time,
        "getter": lambda: int(time.time()),
        "setter": lambda v: system.date.set_date(datetime.fromtimestamp(v, tz=timezone.utc)),
    },
    "timezone": {
        "type": "string",
        "modifiable": True,
        "choices": [{"value": zone} for zone in system.date.get_timezones()],
        "standard": True,
        "enabled": system.date.has_timezone_support,
        "getter": system.date.get_timezone,
        "setter": system.date.set_timezone,
    },
    "wifi_ssid": {
        "type": "string",
        "max": 32,
        "modifiable": True,
        "standard": True,
        "enabled": system.net.has_wifi_support,
        "reconnect": True,
        "getter": {
            "call": system.net.get_wifi_config,
            "key": "ssid",
        },
        "setter": {
            "call": system.net.set_wifi_config,
            "key": "ssid",
        },
    },
    "wifi_key": {
        "type": "string",
        "max": 64,
        "modifiable": True,
        "standard": True,
        "enabled": system.net.has_wifi_support,
        "reconnect": True,
        "getter": {
            "call": system.net.get_wifi_config,
            "key": "psk",
        },
        "setter": {
            "call": system.net.set_wifi_config,
            "key": "psk",
        },
    },
    "wifi_bssid": {
        "type": "string",
        "pattern": r"^([a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2})?$",
        "modifiable": True,
        "standard": True,
        "enabled": system.net.has_wifi_support,
        "reconnect": True,
        "getter": {
            "call": system.net.get_wifi_config,
            "key": "bssid",
        },
        "setter": {
            "call": system.net.set_wifi_config,
            "key": "bssid",
        },
    },
    "wifi_bssid_current": {
        "type": "string",
        "modifiable": False,
        "standard": True,
        "enabled": system.net.has_wifi_support,
        "getter": {
            "call": system.net.get_wifi_config,
            "key": "bssid_current",
        },
    },
    "wifi_signal_strength": {
        "type": "number",
        "modifiable": False,
        "standard": True,
        "enabled": system.net.has_wifi_support,
        "getter": {
            "call": system.net.get_wifi_config,
            "key": "signal_strength_current",
            "transform": lambda v: int(v),
        },
    },
    "ip_address": {
        "type": "string",
        "pattern": r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})?$",
        "modifiable": True,
        "standard": True,
        "enabled": system.net.has_ip_support,
        "reconnect": True,
        "getter": {
            "call": system.net.get_ip_config,
            "key": "address",
        },
        "setter": {
            "call": system.net.set_ip_config,
            "key": "address",
        },
    },
    "ip_netmask": {
        "type": "number",
        "min": 0,
        "max": 31,
        "integer": True,
        "modifiable": True,
        "standard": True,
        "enabled": system.net.has_ip_support,
        "reconnect": True,
        "getter": {"call": system.net.get_ip_config, "key": "netmask", "transform": lambda v: v or 0},
        "setter": {"call": system.net.set_ip_config, "key": "netmask", "transform": lambda v: str(v)},
    },
    "ip_gateway": {
        "type": "string",
        "pattern": r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})?$",
        "modifiable": True,
        "standard": True,
        "enabled": system.net.has_ip_support,
        "reconnect": True,
        "getter": {
            "call": system.net.get_ip_config,
            "key": "gateway",
        },
        "setter": {
            "call": system.net.set_ip_config,
            "key": "gateway",
        },
    },
    "ip_dns": {
        "type": "string",
        "pattern": r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})?$",
        "modifiable": True,
        "standard": True,
        "enabled": system.net.has_ip_support,
        "reconnect": True,
        "getter": {
            "call": system.net.get_ip_config,
            "key": "dns",
        },
        "setter": {
            "call": system.net.set_ip_config,
            "key": "dns",
        },
    },
    "ip_address_current": {
        "type": "string",
        "modifiable": False,
        "standard": True,
        "enabled": system.net.has_ip_support,
        "getter": {
            "call": system.net.get_ip_config,
            "key": "address_current",
        },
    },
    "ip_netmask_current": {
        "type": "number",
        "modifiable": False,
        "standard": True,
        "enabled": system.net.has_ip_support,
        "getter": {"call": system.net.get_ip_config, "key": "netmask_current", "transform": lambda v: v or 0},
    },
    "ip_gateway_current": {
        "type": "string",
        "modifiable": False,
        "standard": True,
        "enabled": system.net.has_ip_support,
        "getter": {
            "call": system.net.get_ip_config,
            "key": "gateway_current",
        },
    },
    "ip_dns_current": {
        "type": "string",
        "modifiable": False,
        "standard": True,
        "enabled": system.net.has_ip_support,
        "getter": {
            "call": system.net.get_ip_config,
            "key": "dns_current",
        },
    },
    "cpu_usage": {
        "type": "number",
        "min": 0,
        "max": 100,
        "modifiable": False,
        "standard": True,
        "getter": system.get_cpu_usage,
    },
    "mem_usage": {
        "type": "number",
        "min": 0,
        "max": 100,
        "modifiable": False,
        "standard": True,
        "getter": system.get_mem_usage,
    },
    "storage_usage": {
        "type": "number",
        "min": 0,
        "max": 100,
        "modifiable": False,
        "standard": True,
        "enabled": system.storage.has_storage_support,
        "getter": system.storage.get_storage_usage,
    },
    "temperature": {
        "type": "number",
        "modifiable": False,
        "min": lambda: settings.system.temperature.min,
        "max": lambda: settings.system.temperature.max,
        # mark as non-standard to expose min/max fields
        "standard": False,
        "enabled": system.temperature.has_temperature_support,
        "getter": system.temperature.get_temperature,
    },
    "battery_level": {
        "type": "number",
        "min": 0,
        "max": 100,
        "modifiable": False,
        "standard": True,
        "enabled": system.battery.has_battery_support,
        "getter": system.battery.get_battery_level,
    },
}


def load_dynamic_attrdef(name: str, params: dict[str, Any]) -> AttributeDefinition:
    params = dict(params)
    class_path = params.pop("driver")

    logger.debug('creating device attribute "%s" with driver "%s"', name, class_path)
    try:
        peripheral_class = dynload_utils.load_attr(class_path)
    except Exception:
        raise NoSuchDriver(class_path)

    return peripheral_class(**params).to_attrdef()


def load_dynamic_attrdefs() -> AttributeDefinitions:
    attrdefs = {}

    for params in settings.core.device_attrs:
        params = dict(params)
        name = params.pop("name")

        try:
            attrdef = load_dynamic_attrdef(name, params)
        except Exception as e:
            logger.error('failed to load dynamic attribute "%s": %s', name, e, exc_info=True)
            continue

        attrdefs[name] = attrdef

    return attrdefs


def get_attrdefs() -> AttributeDefinitions:
    global _attrdefs

    if _attrdefs is None:
        logger.debug("initializing attribute definitions")
        _attrdefs = copy.deepcopy(ATTRDEFS) | load_dynamic_attrdefs()

        # Transform some callable values into corresponding results
        for n, attrdef in list(_attrdefs.items()):
            for k, v in attrdef.items():
                if callable(v) and k in ATTRDEF_CALLABLE_FIELDS:
                    attrdef[k] = v()

            if attrdef.pop("enabled", True) is False:
                _attrdefs.pop(n)

    return _attrdefs


def get_schema(loose: bool = False) -> GenericJSONDict:
    global _schema

    # Use cached value, but only when `loose` is false, as `loose` schema is never cached
    if _schema is not None and not loose:
        return _schema

    schema = {"type": "object", "properties": {}, "additionalProperties": loose}

    for n, attrdef in get_attrdefs().items():
        if not attrdef.get("modifiable"):
            continue

        attr_schema = dict(attrdef)
        if attr_schema["type"] == "string":
            if "min" in attr_schema:
                attr_schema["minLength"] = attr_schema.pop("min")

            if "max" in attr_schema:
                attr_schema["maxLength"] = attr_schema.pop("max")
        elif attr_schema["type"] == "number":
            if attr_schema.get("integer"):
                attr_schema["type"] = "integer"

            if "min" in attr_schema:
                attr_schema["minimum"] = attr_schema.pop("min")

            if "max" in attr_schema:
                attr_schema["maximum"] = attr_schema.pop("max")

        if "choices" in attrdef:
            attr_schema["enum"] = [c["value"] for c in attr_schema.pop("choices")]

        for field in ("modifiable", "standard", "persisted", "getter", "setter", "reconnect"):
            attr_schema.pop(field, None)

        schema["properties"][n] = attr_schema

    if not loose:
        _schema = schema

    return schema


async def get_attrs() -> Attributes:
    attrdefs = get_attrdefs()

    # Do a first round to gather all required calls and ensure we only call each function once, caching its result
    call_results = {}
    for n, attrdef in attrdefs.items():
        getter = attrdef["getter"]
        if isinstance(getter, dict):
            call = getter["call"]
            call_results[call] = None

    for call in call_results.keys():
        result = call()
        if inspect.isawaitable(result):
            result = await result
        call_results[call] = result

    # Do a second round to prepare attribute values
    attrs = {}
    for n, attrdef in attrdefs.items():
        getter = attrdef["getter"]
        if not getter:
            continue

        if isinstance(getter, dict):
            call = getter["call"]
            key = getter.get("key")
            transform = getter.get("transform")
            value = call_results[call]
            if key:
                value = value[key]
            if transform:
                value = transform(value)
        elif callable(getter):
            value = getter()
            if inspect.isawaitable(value):
                value = await value
        else:
            continue

        attrs[n] = value

    return attrs


async def set_attrs(attrs: Attributes, ignore_extra: bool = False) -> bool:
    core_device_attrs = sys.modules[__name__]

    reboot_required = False
    attrdefs = get_attrdefs()

    # Call getters first so that we have all current attribute values, needed for a complete setter argument list
    getter_call_results = {}
    for n, attrdef in attrdefs.items():
        getter = attrdef["getter"]
        if isinstance(getter, dict):
            call = getter["call"]
            getter_call_results[call] = None

    for call in getter_call_results.keys():
        result = call()
        if inspect.isawaitable(result):
            result = await result
        getter_call_results[call] = result

    call_values: dict[Callable, dict] = {}

    for n, value in attrs.items():
        # A few attributes may carry sensitive information, so treat them separately and do not log their values
        if n.count("password") or n == "wifi_key":
            logger.debug("setting device attribute %s", n)
        else:
            logger.debug("setting device attribute %s = %s", n, json_utils.dumps(value))

        try:
            attrdef = attrdefs[n]
        except KeyError:
            if ignore_extra:
                continue
            else:
                raise DeviceAttributeError("no-such-attribute", n) from None

        if not attrdef.get("modifiable"):
            if ignore_extra:
                continue
            else:
                raise DeviceAttributeError("attribute-not-modifiable", n)

        reboot_required = reboot_required or attrdef.get("reconnect", False)

        # Used by `PUT /device` API call to restore passwords stored as hashes
        if n.endswith("_password_hash") and hasattr(core_device_attrs, n):
            # FIXME: Password set command cannot be called with hash, and we don't have clear-text password here.
            #        A solution would be to use sha256 crypt algorithm w/o salt for Unix password (watch for the special
            #        alphabet and for number of rounds defaulting to 5000)
            setattr(core_device_attrs, n, value)
            continue

        setter = attrdef["setter"]
        if isinstance(setter, dict):
            call = setter["call"]
            key = setter.get("key")
            transform = setter.get("transform")
            if transform:
                value = transform(value)
            if key:
                call_values.setdefault(call, {})[key] = value
            else:
                result = call(value)
                if inspect.isawaitable(result):
                    await result
        else:
            result = setter(value)
            if inspect.isawaitable(result):
                await result

    # Actually do the calls with corresponding values
    for call, values in call_values.items():
        # Fill in any missing setter parameters using corresponding getter values
        for n, attrdef in attrdefs.items():
            getter = attrdef["getter"]
            setter = attrdef.get("setter")
            if not isinstance(getter, dict) or not isinstance(setter, dict) or setter["call"] is not call:
                continue
            call_result = getter_call_results.get(getter["call"])
            if not call_result:
                continue
            values.setdefault(setter["key"], call_result[setter["key"]])

        result = call(**values)
        if inspect.isawaitable(result):
            await result

    return reboot_required


async def to_json() -> GenericJSONDict:
    attrdefs: AttributeDefinitions = copy.deepcopy(get_attrdefs())
    filtered_attrdefs: AttributeDefinitions = {}
    for attr_name, attrdef in attrdefs.items():
        if attrdef.pop("standard", False):
            continue

        # Remove unwanted fields from attribute definition
        for field in ("persisted", "setter", "getter"):
            attrdef.pop(field, None)

        # Remove optional boolean fields that are false
        for field in ("integer", "reconnect"):
            if not attrdef.get(field):
                attrdef.pop(field, None)

        for key in list(attrdef):
            if key.startswith("_"):
                attrdef.pop(key)

        filtered_attrdefs[attr_name] = attrdef

    result: dict[str, Any] = dict(await get_attrs())
    result["definitions"] = filtered_attrdefs

    return result


def _check_net_data_changed(data: dict) -> bool:
    changed = False

    if system.net.has_wifi_support():
        wifi_config = system.net.get_wifi_config()
        old_wifi_config = data.get("wifi_config")
        if old_wifi_config != wifi_config:
            data["wifi_config"] = wifi_config
            changed = True

    if system.net.has_ip_support():
        ip_config = system.net.get_ip_config()
        old_ip_config = data.get("ip_config")
        if old_ip_config != ip_config:
            data["ip_config"] = ip_config
            changed = True

    return changed


async def _attrs_watch_loop() -> None:
    # TODO: also watch dynamic attributes

    last_net_data = {}

    try:
        while True:
            changed = False
            try:
                if _check_net_data_changed(last_net_data):
                    logger.debug("network attributes data changed")
                    changed = True
            except Exception as e:
                logger.error("network attributes data check failed: %s", e, exc_info=True)

            if changed:
                await device_events.trigger_update()

            await asyncio.sleep(NETWORK_ATTRS_WATCH_INTERVAL)
    except asyncio.CancelledError:
        logger.debug("attributes watch task cancelled")


async def init() -> None:
    global _attrs_watch_task

    logger.debug("starting attributes watch task")
    _attrs_watch_task = asyncio.create_task(_attrs_watch_loop())


async def cleanup() -> None:
    logger.debug("stopping attributes watch task")
    if _attrs_watch_task:
        _attrs_watch_task.cancel()
        await _attrs_watch_task
