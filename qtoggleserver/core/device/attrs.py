
import asyncio
import copy
import datetime
import hashlib
import logging
import socket
import sys
import time

from qtoggleserver import system
from qtoggleserver import version
from qtoggleserver.conf import settings
from qtoggleserver.core import api as core_api
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
        'type': 'string',
        'pattern': r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$',
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
    }
}

EMPTY_PASSWORD_HASH = hashlib.sha256(b'').hexdigest()

WIFI_RSSI_EXCELLENT = -50
WIFI_RSSI_GOOD = -60
WIFI_RSSI_FAIR = -70

NETWORK_ATTRS_WATCH_INTERVAL = 10


name = socket.gethostname()
display_name = ''
admin_password_hash = None
normal_password_hash = None
viewonly_password_hash = None

_schema = None
_attrdefs = None
_attrs_watch_task = None


class DeviceAttributeError(Exception):
    pass


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


def get_schema() -> GenericJSONDict:
    global _schema

    if not _schema:
        _schema = {
            'type': 'object',
            'properties': {},
            'additionalProperties': False
        }

        for name, attrdef in get_attrdefs().items():
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

            _schema['properties'][name] = attr_schema

    return _schema


def get_attrs() -> Attributes:
    attrs = {
        'name': name,
        'display_name': display_name,
        'version': version.VERSION,
        'api_version': core_api.API_VERSION,
        'vendor': version.VENDOR,
        'uptime': system.uptime(),

        # Never disclose passwords
        'admin_password': '',
        'normal_password': '',
        'viewonly_password': ''
    }

    flags = ['expressions']
    if settings.system.fwupdate_driver:
        flags.append('firmware')

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
        attrs['date'] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    if system.date.has_timezone_support():
        attrs['timezone'] = system.date.get_timezone()

    if system.net.has_wifi_support():
        wifi_config = system.net.get_wifi_config()
        attrs['wifi_ssid'] = wifi_config['ssid']
        attrs['wifi_key'] = wifi_config['psk']
        attrs['wifi_bssid'] = wifi_config['bssid']
        attrs['wifi_bssid_current'] = wifi_config['bssid_current']

        strength = -1
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

    return attrs


def set_attrs(attrs: Attributes) -> bool:
    core_device_attrs = sys.modules[__name__]

    reboot_required = False
    attrdefs = get_attrdefs()

    for name, value in attrs.items():
        # A few attributes may carry sensitive information, so treat them separately and do not log their values
        if name.count('password') or name == 'wifi_key':
            logger.debug('setting device attribute %s', name)

        else:
            logger.debug('setting device attribute %s = %s', name, json_utils.dumps(value))

        attrdef = attrdefs[name]

        if not attrdef.get('modifiable'):
            raise DeviceAttributeError(f'attribute not modifiable: {name}')

        # Treat passwords separately, as they are not persisted as given, but hashed first
        if name.endswith('_password') and hasattr(core_device_attrs, name + '_hash'):
            # Call password set command, if available
            if settings.core.passwords.set_cmd:
                run_set_cmd(
                    settings.core.passwords.set_cmd,
                    cmd_name='password',
                    log_values=False,
                    username=name[:-9],
                    password=value
                )

            value = hashlib.sha256(value.encode()).hexdigest()
            name += '_hash'

            setattr(core_device_attrs, name, value)
            continue

        persisted = attrdef.get('persisted', attrdef.get('modifiable'))
        if persisted:
            setattr(core_device_attrs, name, value)

        if name == 'name' and settings.core.device_name.set_cmd:
            run_set_cmd(settings.core.device_name.set_cmd, cmd_name='device name', name=value)

        elif name == 'date' and system.date.has_set_date_support():
            try:
                date = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')

            except ValueError:
                raise DeviceAttributeError(f'invalid field: {name}')

            system.date.set_date(date)

        elif name == 'timezone' and system.date.has_timezone_support():
            system.date.set_timezone(value)

        elif name in ('wifi_ssid', 'wifi_key', 'wifi_bssid') and system.net.has_wifi_support():
            wifi_config = system.net.get_wifi_config()
            k = name[5:]
            k = {
                'key': 'psk'
            }.get(k, k)
            wifi_config[k] = value
            wifi_config = {k: v for k, v in wifi_config.items() if not k.endswith('_current')}

            system.net.set_wifi_config(**wifi_config)
            reboot_required = True

        elif name in ('ip_address', 'ip_netmask', 'ip_gateway', 'ip_dns') and system.net.has_ip_support():
            ip_config = system.net.get_ip_config()

            k = name[3:]
            ip_config[k] = value
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
                device_events.trigger_update()

            await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.debug('attributes watch task cancelled')


async def init() -> None:
    global _attrs_watch_task

    logger.debug('starting attributes watch task')
    _attrs_watch_task = asyncio.create_task(_attrs_watch_loop())


async def cleanup() -> None:
    logger.debug('stopping attributes watch task')
    _attrs_watch_task.cancel()
    await _attrs_watch_task
