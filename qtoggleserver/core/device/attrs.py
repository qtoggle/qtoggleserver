
import asyncio
import copy
import datetime
import hashlib
import logging
import re
import socket
import sys
import time

from typing import Optional

from qtoggleserver import system
from qtoggleserver import version
from qtoggleserver.conf import settings
from qtoggleserver.core.typing import Attributes, AttributeDefinitions, GenericJSONDict
from qtoggleserver.utils import json as json_utils
from qtoggleserver.utils.cmd import run_set_cmd

from . import events as device_events


logger = logging.getLogger(__name__)

ATTRDEFS = {
    'name': {
        'type': 'string',
        'modifiable': True,
        'persisted': True,
        'min': 1,
        'max': 32,
        'pattern': r'^[_a-zA-Z][_a-zA-Z0-9-]{0,31}$',
        'standard': True
    },
    'display_name': {
        'type': 'string',
        'modifiable': True,
        'max': 64,
        'standard': True
    },
    'version': {
        'type': 'string',
        'standard': True
    },
    'api_version': {
        'type': 'string',
        'standard': True
    },
    'vendor': {
        'type': 'string',
        'standard': True
    },
    'admin_password': {
        'type': 'string',
        'modifiable': True,
        'max': 32,
        'standard': True
    },
    'normal_password': {
        'type': 'string',
        'modifiable': True,
        'max': 32,
        'standard': True
    },
    'viewonly_password': {
        'type': 'string',
        'modifiable': True,
        'max': 32,
        'standard': True
    },
    'flags': {
        'type': ['string'],
        'standard': True
    },
    'virtual_ports': {
        'type': 'number',
        'enabled': lambda: bool(settings.core.virtual_ports),
        'standard': True
    },
    'uptime': {
        'type': 'number',
        'standard': True
    },
    'date': {
        'type': 'number',
        'modifiable': lambda: system.date.has_set_date_support(),
        'persisted': False,
        'standard': False  # Having standard False here enables exposing of definition (needed for non-modifiable)
    },
    'timezone': {
        'type': 'string',
        'modifiable': True,
        'persisted': False,
        'choices': [{'value': zone} for zone in system.date.get_timezones()],
        'enabled': lambda: system.date.has_timezone_support(),
        'standard': False  # Having standard False here enables exposing of definition (needed for choices)
    },
    'wifi_ssid': {
        'type': 'string',
        'max': 32,
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.net.has_wifi_support(),
        'standard': True
    },
    'wifi_key': {
        'type': 'string',
        'max': 64,
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.net.has_wifi_support(),
        'standard': True
    },
    'wifi_bssid': {
        'type': 'string',
        'pattern': r'^([a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2})?$',
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.net.has_wifi_support(),
        'standard': True
    },
    'wifi_bssid_current': {
        'type': 'string',
        'modifiable': False,
        'persisted': False,
        'enabled': lambda: system.net.has_wifi_support(),
        'standard': True
    },
    'wifi_signal_strength': {
        'type': 'number',
        'modifiable': False,
        'persisted': False,
        'enabled': lambda: system.net.has_wifi_support(),
        'standard': True
    },
    'ip_address': {
        'type': 'string',
        'pattern': r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})?$',
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.net.has_ip_support(),
        'standard': True
    },
    'ip_netmask': {
        'type': 'number',
        'min': 0,
        'max': 31,
        'integer': True,
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.net.has_ip_support(),
        'standard': True
    },
    'ip_gateway': {
        'type': 'string',
        'pattern': r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})?$',
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.net.has_ip_support(),
        'standard': True
    },
    'ip_dns': {
        'type': 'string',
        'pattern': r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})?$',
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.net.has_ip_support(),
        'standard': True
    },
    'ip_address_current': {
        'type': 'string',
        'modifiable': False,
        'persisted': False,
        'enabled': lambda: system.net.has_ip_support(),
        'standard': True
    },
    'ip_netmask_current': {
        'type': 'number',
        'modifiable': False,
        'persisted': False,
        'enabled': lambda: system.net.has_ip_support(),
        'standard': True
    },
    'ip_gateway_current': {
        'type': 'string',
        'modifiable': False,
        'persisted': False,
        'enabled': lambda: system.net.has_ip_support(),
        'standard': True
    },
    'ip_dns_current': {
        'type': 'string',
        'modifiable': False,
        'persisted': False,
        'enabled': lambda: system.net.has_ip_support(),
        'standard': True
    },
    'cpu_usage': {
        'type': 'number',
        'min': 0,
        'max': 100,
        'modifiable': False,
        'persisted': False,
        'standard': True
    },
    'mem_usage': {
        'type': 'number',
        'min': 0,
        'max': 100,
        'modifiable': False,
        'persisted': False,
        'standard': True
    },
    'storage_usage': {
        'type': 'number',
        'min': 0,
        'max': 100,
        'modifiable': False,
        'persisted': False,
        'enabled': lambda: system.storage.has_storage_support(),
        'standard': True
    },
    'temperature': {
        'type': 'number',
        'modifiable': False,
        'persisted': False,
        'enabled': lambda: system.temperature.has_temperature_support(),
        'min': lambda: settings.system.temperature.min,
        'max': lambda: settings.system.temperature.max,
        'standard': False  # Having standard False here enables exposing of definition (needed for min/max)
    },
    'battery_level': {
        'type': 'number',
        'min': 0,
        'max': 100,
        'modifiable': False,
        'persisted': False,
        'enabled': lambda: system.battery.has_battery_support(),
        'standard': True
    }
}

EMPTY_PASSWORD_HASH = hashlib.sha256(b'').hexdigest()

WIFI_RSSI_EXCELLENT = -50
WIFI_RSSI_GOOD = -60
WIFI_RSSI_FAIR = -70

NETWORK_ATTRS_WATCH_INTERVAL = 10


name: str = re.sub(r'[^a-zA-Z0-9_-]', '', socket.gethostname())
if not re.match('^[a-zA-Z_]', name):  # Make sure name starts with a letter or underscore
    name = f'q{name}'
name = name[:32]

display_name: str = ''
admin_password_hash: Optional[str] = None
normal_password_hash: Optional[str] = None
viewonly_password_hash: Optional[str] = None

_schema: Optional[GenericJSONDict] = None
_attrdefs: Optional[AttributeDefinitions] = None
_attrs_watch_task: Optional[asyncio.Task] = None


class DeviceAttributeError(Exception):
    def __init__(self, error: str, attribute: str) -> None:
        self.error: str = error
        self.attribute: str = attribute


def get_attrdefs() -> AttributeDefinitions:
    global _attrdefs

    if _attrdefs is None:
        logger.debug('initializing attribute definitions')
        _attrdefs = copy.deepcopy(ATTRDEFS)

        # Transform all callable values into corresponding results
        for n, attrdef in _attrdefs.items():
            for k, v in attrdef.items():
                if callable(v):
                    attrdef[k] = v()

    return _attrdefs


def get_schema(loose: bool = False) -> GenericJSONDict:
    global _schema

    # Use cached value, but only when loose is false, as loose schema is never cached
    if _schema is not None and not loose:
        return _schema

    schema = {
        'type': 'object',
        'properties': {},
        'additionalProperties': loose
    }

    for n, attrdef in get_attrdefs().items():
        if not attrdef.get('modifiable'):
            continue

        attr_schema = dict(attrdef)

        enabled = attr_schema.pop('enabled', True)
        if not enabled:
            continue

        if attr_schema['type'] == 'string':
            if 'min' in attr_schema:
                attr_schema['minLength'] = attr_schema.pop('min')

            if 'max' in attr_schema:
                attr_schema['maxLength'] = attr_schema.pop('max')

        elif attr_schema['type'] == 'number':
            if attr_schema.get('integer'):
                attr_schema['type'] = 'integer'

            if 'min' in attr_schema:
                attr_schema['minimum'] = attr_schema.pop('min')

            if 'max' in attr_schema:
                attr_schema['maximum'] = attr_schema.pop('max')

        if 'choices' in attrdef:
            attr_schema['enum'] = [c['value'] for c in attr_schema.pop('choices')]

        attr_schema.pop('persisted', None)
        attr_schema.pop('modifiable', None)
        attr_schema.pop('standard', None)

        schema['properties'][n] = attr_schema

    if not loose:
        _schema = schema

    return schema


def get_attrs() -> Attributes:
    from qtoggleserver.core import api as core_api
    from qtoggleserver.core import history as core_history

    attrs = {
        'name': name,
        'display_name': display_name,
        'version': version.VERSION,
        'api_version': core_api.API_VERSION,
        'vendor': version.VENDOR,
        'uptime': system.uptime(),

        # Never disclose passwords
        'admin_password': '' if admin_password_hash == EMPTY_PASSWORD_HASH else 'set',
        'normal_password': '' if normal_password_hash == EMPTY_PASSWORD_HASH else 'set',
        'viewonly_password': '' if viewonly_password_hash == EMPTY_PASSWORD_HASH else 'set'
    }

    flags = ['expressions']
    if settings.system.fwupdate.driver:
        flags.append('firmware')

    if settings.core.backup_support:
        flags.append('backup')

    if core_history.is_enabled():
        flags.append('history')

    if settings.core.listen_support:
        flags.append('listen')

    if settings.slaves.enabled:
        flags.append('master')

    if settings.reverse.enabled:
        flags.append('reverse')

    if settings.core.sequences_support:
        flags.append('sequences')

    if settings.core.ssl_support:
        flags.append('ssl')

    if settings.webhooks.enabled:
        flags.append('webhooks')

    attrs['flags'] = flags

    if settings.core.virtual_ports:
        attrs['virtual_ports'] = settings.core.virtual_ports

    if system.date.has_real_date_time():
        attrs['date'] = int(time.time())

    if system.date.has_timezone_support():
        attrs['timezone'] = system.date.get_timezone()

    if system.net.has_wifi_support():
        wifi_config = system.net.get_wifi_config()
        attrs['wifi_ssid'] = wifi_config['ssid']
        attrs['wifi_key'] = wifi_config['psk']
        attrs['wifi_bssid'] = wifi_config['bssid']

        if wifi_config['bssid_current']:
            attrs['wifi_bssid_current'] = wifi_config['bssid_current']

        rssi = wifi_config['rssi_current']
        if rssi:
            rssi = int(rssi)
            if rssi >= WIFI_RSSI_EXCELLENT:
                strength = 3

            elif rssi >= WIFI_RSSI_GOOD:
                strength = 2

            elif rssi >= WIFI_RSSI_FAIR:
                strength = 1

            else:
                strength = 0

            attrs['wifi_signal_strength'] = strength

    if system.net.has_ip_support():
        ip_config = system.net.get_ip_config()
        attrs['ip_address'] = ip_config['address']
        attrs['ip_netmask'] = int(ip_config['netmask'] or 0)
        attrs['ip_gateway'] = ip_config['gateway']
        attrs['ip_dns'] = ip_config['dns']

        if 'address_current' in ip_config:
            attrs['ip_address_current'] = ip_config['address_current']
        if 'netmask_current' in ip_config:
            attrs['ip_netmask_current'] = int(ip_config['netmask_current'] or 0)
        if 'gateway_current' in ip_config:
            attrs['ip_gateway_current'] = ip_config['gateway_current']
        if 'dns_current' in ip_config:
            attrs['ip_dns_current'] = ip_config['dns_current']

    attrs['cpu_usage'] = system.get_cpu_usage()
    attrs['mem_usage'] = system.get_mem_usage()

    if system.storage.has_storage_support():
        attrs['storage_usage'] = system.storage.get_storage_usage()

    if system.temperature.has_temperature_support():
        attrs['temperature'] = system.temperature.get_temperature()

    if system.battery.has_battery_support():
        attrs['battery_level'] = system.battery.get_battery_level()

    return attrs


def set_attrs(attrs: Attributes, ignore_extra: bool = False) -> bool:
    core_device_attrs = sys.modules[__name__]

    reboot_required = False
    attrdefs = get_attrdefs()

    wifi_attrs = {}
    ip_attrs = {}

    for n, value in attrs.items():
        # A few attributes may carry sensitive information, so treat them separately and do not log their values
        if n.count('password') or n == 'wifi_key':
            logger.debug('setting device attribute %s', n)

        else:
            logger.debug('setting device attribute %s = %s', n, json_utils.dumps(value))

        try:
            attrdef = attrdefs[n]

        except KeyError:
            if ignore_extra:
                continue

            else:
                raise

        if not attrdef.get('modifiable'):
            if not ignore_extra:
                raise DeviceAttributeError('attribute-not-modifiable', n)

        # Treat passwords separately, as they are not persisted as given, but hashed first
        if n.endswith('_password') and hasattr(core_device_attrs, f'{n}_hash'):
            # Call password set command, if available
            if settings.core.passwords.set_cmd:
                run_set_cmd(
                    settings.core.passwords.set_cmd,
                    cmd_name='password',
                    log_values=False,
                    username=n[:-9],
                    password=value
                )

            value = hashlib.sha256(value.encode()).hexdigest()
            n += '_hash'

            setattr(core_device_attrs, n, value)
            continue

        elif n.endswith('_password_hash') and hasattr(core_device_attrs, n):
            # FIXME: Password set command cannot be called with hash and we don't have clear-text password here.
            #        A solution would be to use sha256 crypt algorithm w/o salt for Unix password (watch for the special
            #        alphabet and for number of rounds defaulting to 5000)
            setattr(core_device_attrs, n, value)
            continue

        persisted = attrdef.get('persisted', attrdef.get('modifiable'))
        if persisted:
            setattr(core_device_attrs, n, value)

        if n == 'name' and settings.core.device_name.set_cmd:
            run_set_cmd(settings.core.device_name.set_cmd, cmd_name='device name', name=value)

        elif n == 'date' and system.date.has_set_date_support():
            date = datetime.datetime.utcfromtimestamp(value)
            system.date.set_date(date)

        elif n == 'timezone' and system.date.has_timezone_support():
            system.date.set_timezone(value)

        elif n in ('wifi_ssid', 'wifi_key', 'wifi_bssid') and system.net.has_wifi_support():
            k = n[5:]
            k = {
                'key': 'psk'
            }.get(k, k)
            wifi_attrs[k] = value

        elif n in ('ip_address', 'ip_netmask', 'ip_gateway', 'ip_dns') and system.net.has_ip_support():
            k = n[3:]
            ip_attrs[k] = value

    if wifi_attrs:
        wifi_config = system.net.get_wifi_config()

        for k, v in wifi_attrs.items():
            wifi_config[k] = v
            wifi_config = {k: v for k, v in wifi_config.items() if not k.endswith('_current')}

        system.net.set_wifi_config(**wifi_config)
        reboot_required = True

    if ip_attrs:
        ip_config = system.net.get_ip_config()

        for k, v in ip_attrs.items():
            ip_config[k] = v
            ip_config = {k: v for k, v in ip_config.items() if not k.endswith('_current')}
            ip_config['netmask'] = str(ip_config['netmask'])

        system.net.set_ip_config(**ip_config)
        reboot_required = True

    return reboot_required


def to_json() -> GenericJSONDict:
    attrdefs = copy.deepcopy(get_attrdefs())
    filtered_attrdefs = {}
    for n, attrdef in attrdefs.items():
        if attrdef.pop('standard', False):
            continue

        enabled = attrdef.pop('enabled', True)
        if not enabled:
            continue

        attrdef.pop('persisted', None)
        attrdef.pop('pattern', None)

        filtered_attrdefs[n] = attrdef

    result = dict(get_attrs())
    result['definitions'] = filtered_attrdefs

    return result


def _check_net_data_changed(data: dict) -> bool:
    changed = False

    if system.net.has_wifi_support():
        wifi_config = system.net.get_wifi_config()
        old_wifi_config = data.get('wifi_config')
        if old_wifi_config != wifi_config:
            data['wifi_config'] = wifi_config
            changed = True

    if system.net.has_ip_support():
        ip_config = system.net.get_ip_config()
        old_ip_config = data.get('ip_config')
        if old_ip_config != ip_config:
            data['ip_config'] = ip_config
            changed = True

    return changed


async def _attrs_watch_loop() -> None:
    last_net_time = time.time()
    last_net_data = {}

    try:
        while True:
            now = time.time()
            changed = False
            if now - last_net_time >= NETWORK_ATTRS_WATCH_INTERVAL:
                try:
                    if _check_net_data_changed(last_net_data):
                        logger.debug('network attributes data changed')
                        changed = True

                except Exception as e:
                    logger.error('network attributes data check failed: %s', e, exc_info=True)

                last_net_time = now

            if changed:
                await device_events.trigger_update()

            await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.debug('attributes watch task cancelled')


async def init() -> None:
    global _attrs_watch_task

    logger.debug('starting attributes watch task')
    _attrs_watch_task = asyncio.create_task(_attrs_watch_loop())


async def cleanup() -> None:
    logger.debug('stopping attributes watch task')
    if _attrs_watch_task:
        _attrs_watch_task.cancel()
        await _attrs_watch_task
