
import copy
import datetime
import hashlib
import logging
import re
import socket
import sys

from qtoggleserver import system
from qtoggleserver import version
from qtoggleserver.conf import settings
from qtoggleserver.core import api as core_api
from qtoggleserver.core.typing import Attributes, GenericJSONDict
from qtoggleserver.utils import json as json_utils
from qtoggleserver.utils.cmd import run_set_cmd


logger = logging.getLogger(__name__)

STANDARD_ATTRDEFS = {
    'name': {
        'type': 'string',
        'modifiable': True,
        'persisted': True,
        'min': 1,
        'max': 32,
        'pattern': r'^[_a-zA-Z][_a-zA-Z0-9-]{0,31}$',
        'internal': True
    },
    'display_name': {
        'type': 'string',
        'modifiable': True,
        'max': 64,
        'internal': True
    },
    'version': {
        'type': 'string',
        'internal': True
    },
    'api_version': {
        'type': 'string',
        'internal': True
    },
    'vendor': {
        'type': 'string',
        'internal': True
    },
    'admin_password': {
        'type': 'string',
        'modifiable': True,
        'max': 32,
        'internal': True
    },
    'normal_password': {
        'type': 'string',
        'modifiable': True,
        'max': 32,
        'internal': True
    },
    'viewonly_password': {
        'type': 'string',
        'modifiable': True,
        'max': 32,
        'internal': True
    },
    'flags': {
        'type': ['string'],
        'internal': True
    },
    'virtual_ports': {
        'type': 'number',
        'enabled': lambda: bool(settings.core.virtual_ports),
        'internal': True
    },
    'uptime': {
        'type': 'number',
        'internal': True
    },
    'date': {
        'type': 'string',
        'pattern': r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$',
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.date.has_date_support(),
        'internal': True
    },
    'timezone': {
        'type': 'string',
        'modifiable': True,
        'persisted': False,
        'choices': [{'value': zone} for zone in system.date.get_timezones()],
        'enabled': lambda: system.date.has_timezone_support(),
        'internal': False  # Having internal False here enables export of attribute definition (needed for choices)
    },
    'wifi_ssid': {
        'type': 'string',
        'max': 32,
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.net.has_wifi_support(),
        'internal': True
    },
    'wifi_psk': {
        'type': 'string',
        'max': 64,
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.net.has_wifi_support(),
        'internal': True
    },
    'wifi_bssid': {
        'type': 'string',
        'pattern': r'^([a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2})?$',
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.net.has_wifi_support(),
        'internal': True
    },
    'ip_address': {
        'type': 'string',
        'pattern': r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})?$',
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.net.has_ip_support(),
        'internal': True
    },
    'ip_mask': {
        'type': 'number',
        'min': 0,
        'max': 31,
        'integer': True,
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.net.has_ip_support(),
        'internal': True
    },
    'ip_gateway': {
        'type': 'string',
        'pattern': r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})?$',
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.net.has_ip_support(),
        'internal': True
    },
    'ip_dns': {
        'type': 'string',
        'pattern': r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})?$',
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.net.has_ip_support(),
        'internal': True
    },
}

# TODO generalize additional attributes using getters and setters

'''
ADDITIONAL_ATTRDEFS = {
    'attr1': {
        'display_name': 'Some Attribute Display Name',
        'description': 'Some attribute description',
        'type': 'number',
        'modifiable': True,
        'unit': 'seconds',
        'min': 1,
        'max': 100,
        'integer': True,
        'step': 5,
        'reconnect': False,
        'choices': [
            {'value': 2, 'display_name': 'Two'},
            {'value': 4, 'display_name': 'Four'}
        ]
    },
    ...
}'''
ADDITIONAL_ATTRDEFS = {
}

ATTRDEFS = dict(STANDARD_ATTRDEFS, **ADDITIONAL_ATTRDEFS)

EMPTY_PASSWORD_HASH = hashlib.sha256(b'').hexdigest()


name = socket.gethostname()
display_name = ''
admin_password_hash = None
normal_password_hash = None
viewonly_password_hash = None

_schema = None


class DeviceAttributeError(Exception):
    pass


def get_schema() -> GenericJSONDict:
    global _schema

    if not _schema:
        _schema = {
            'type': 'object',
            'properties': {},
            'additionalProperties': False
        }

        for name, attrdef in ATTRDEFS.items():
            if not attrdef.get('modifiable'):
                continue

            attr_schema = dict(attrdef)

            enabled = attr_schema.pop('enabled', True)
            if not enabled or callable(enabled) and not enabled():
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
            attr_schema.pop('internal', None)

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

    flags = []
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

    if system.date.has_date_support():
        attrs['date'] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    if system.date.has_timezone_support():
        attrs['timezone'] = system.date.get_timezone()

    if system.net.has_wifi_support():
        wifi_config = system.net.get_wifi_config()
        attrs['wifi_ssid'] = wifi_config['ssid']
        attrs['wifi_key'] = wifi_config['psk']
        attrs['wifi_bssid'] = wifi_config['bssid']

    if system.net.has_ip_support():
        ip_config = system.net.get_ip_config()
        attrs['ip_address'] = ip_config['ip']
        attrs['ip_mask'] = int(ip_config['mask'] or 0)
        attrs['ip_gateway'] = ip_config['gw']
        attrs['ip_dns'] = ip_config['dns']

    return attrs


def set_attrs(attrs: Attributes) -> bool:
    core_device_attrs = sys.modules[__name__]

    reboot_required = False

    for name, value in attrs.items():
        # A few attributes may carry sensitive information, so treat them separately and do not log their values
        if name.count('password') or name == 'wifi_key':
            logger.debug('setting device attribute %s', name)

        else:
            logger.debug('setting device attribute %s = %s', name, json_utils.dumps(value))

        attrdef = ATTRDEFS[name]

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
        if callable(persisted):
            persisted = persisted()
        if persisted:
            setattr(core_device_attrs, name, value)

        if name == 'name' and settings.core.device_name.set_cmd:
            run_set_cmd(settings.core.device_name.set_cmd, cmd_name='device name', name=value)

        elif name == 'date' and system.date.has_date_support():
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

            system.net.set_wifi_config(**wifi_config)
            reboot_required = True

        elif name in ('ip_address', 'ip_mask', 'ip_gateway', 'ip_dns') and system.net.has_ip_support():
            ip_config = system.net.get_ip_config()

            k = name[3:]
            k = {
                'address': 'ip',
                'gateway': 'gw'
            }.get(k, k)
            ip_config[k] = value

            system.net.set_ip_config(**ip_config)
            reboot_required = True

    return reboot_required


def to_json() -> GenericJSONDict:
    attrdefs = copy.deepcopy(ATTRDEFS)
    filtered_attrdefs = {}
    for n, attrdef in attrdefs.items():
        if attrdef.pop('internal', False):
            continue

        enabled = attrdef.pop('enabled', True)
        if not enabled or callable(enabled) and not enabled():
            continue

        attrdef.pop('persisted', None)
        attrdef.pop('pattern', None)

        filtered_attrdefs[n] = attrdef

    result = dict(get_attrs())
    result['definitions'] = filtered_attrdefs

    return result
