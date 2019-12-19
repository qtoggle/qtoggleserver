
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
    'network_ip': {
        'type': 'string',
        'pattern': r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,3}\.\d{1,'
                   r'3}\.\d{1,3}\.\d{1,3})?$',
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.net.has_network_ip_support(),
        'internal': True
    },
    'network_wifi': {
        'type': 'string',
        # TODO this regex should ignore escaped colons \:
        'pattern': r'^(([^:]{0,32}:?)|([^:]{0,32}:[^:]{0,64}:?)|([^:]{0,32}:[^:]{0,64}:[0-9a-fA-F]{12}))$',
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: system.net.has_network_wifi_support(),
        'internal': True
    }
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
    'ui_theme': {
        'display_name': 'Interface Theme',
        'description': 'Sets the user interface theme.',
        'type': 'string',
        'modifiable': True,
        'choices': [
            {'value': 'light', 'display_name': 'Light'},
            {'value': 'dark', 'display_name': 'Dark'}
        ]
    }
}

ATTRDEFS = dict(STANDARD_ATTRDEFS, **ADDITIONAL_ATTRDEFS)

EMPTY_PASSWORD_HASH = hashlib.sha256(b'').hexdigest()


name = socket.gethostname()
display_name = ''
admin_password_hash = None
normal_password_hash = None
viewonly_password_hash = None

ui_theme = 'dark'

_schema = None


def get_schema():
    global _schema

    if not _schema:
        _schema = {
            'type': 'object',
            'properties': {},
            'additionalProperties': False
        }

        # noinspection PyShadowingNames
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


def get_attrs():
    attrs = {
        'name': name,
        'display_name': display_name,
        'version': version.VERSION,
        'api_version': core_api.API_VERSION,
        'vendor': version.VENDOR,
        'uptime': system.uptime(),
        'ui_theme': ui_theme
    }

    # never disclose these ones
    attrs['admin_password'] = ''
    attrs['normal_password'] = ''
    attrs['viewonly_password'] = ''

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

    if system.net.has_network_wifi_support():
        wifi_config = system.net.get_wifi_config()
        if wifi_config['bssid']:
            wifi_config['bssid'] = wifi_config['bssid'].replace(':', '')
            attrs['network_wifi'] = '{}:{}:{}'.format(wifi_config['ssid'], wifi_config['psk'], wifi_config['bssid'])

        elif wifi_config['psk']:
            wifi_config['psk'] = wifi_config['psk'].replace('\\', '\\\\')
            wifi_config['psk'] = wifi_config['psk'].replace(':', '\\:')
            attrs['network_wifi'] = '{}:{}'.format(wifi_config['ssid'], wifi_config['psk'])

        elif wifi_config['ssid']:
            wifi_config['ssid'] = wifi_config['ssid'].replace('\\', '\\\\')
            wifi_config['ssid'] = wifi_config['ssid'].replace(':', '\\:')
            attrs['network_wifi'] = wifi_config['ssid']

        else:
            attrs['network_wifi'] = ''

    if system.net.has_network_ip_support():
        ip_config = system.net.get_ip_config()
        if ip_config['ip'] and ip_config['mask'] and ip_config['gw'] and ip_config['dns']:
            attrs['network_ip'] = '{}/{}:{}:{}'.format(ip_config['ip'], ip_config['mask'],
                                                       ip_config['gw'], ip_config['dns'])

        else:
            attrs['network_ip'] = ''

    return attrs


def set_attrs(attrs):
    core_device_attrs = sys.modules[__name__]

    reboot_required = False

    # noinspection PyShadowingNames
    for name, value in attrs.items():
        # a few attributes may carry sensitive information
        # treat them separately and do not log their values
        if name.count('password'):
            logger.debug('setting device attribute %s', name)

        elif name == 'network_wifi':
            logger.debug('setting device attribute %s = [hidden]', name)

        else:
            logger.debug('setting device attribute %s = %s', name, json_utils.dumps(value))

        attrdef = ATTRDEFS[name]

        if not attrdef.get('modifiable'):
            return 'attribute not modifiable: {}'.format(name)

        # Treat passwords separately, as they are not persisted as given, but hashed first
        if name.endswith('_password') and hasattr(core_device_attrs, name + '_hash'):
            # Call password set command, if available
            if settings.password_set_cmd:
                run_set_cmd(settings.password_set_cmd, cmd_name='password', log_values=False,
                            username=name[:-9], password=value)

            value = hashlib.sha256(value.encode()).hexdigest()
            name += '_hash'

            setattr(core_device_attrs, name, value)
            continue

        persisted = attrdef.get('persisted', attrdef.get('modifiable'))
        if callable(persisted):
            persisted = persisted()
        if persisted:
            setattr(core_device_attrs, name, value)

        if name == 'name' and settings.device_name.set_cmd:
            run_set_cmd(settings.device_name.set_cmd, cmd_name='device name', name=value)

        elif name == 'date' and system.date.has_date_support():
            try:
                date = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')

            except ValueError:
                return 'invalid field: {}'.format(name)

            system.date.set_date(date)

        elif name == 'timezone' and system.date.has_timezone_support():
            system.date.set_timezone(value)

        elif name == 'network_wifi' and system.net.has_network_wifi_support():
            parts = value.split(':')
            i = 0
            while i < len(parts):
                if len(parts[i]) and parts[i][-1] == '\\':
                    parts[i] = parts[i][:-1] + ':' + parts[i + 1]
                    del parts[i + 1]
                i += 1

            parts = [p.replace('\\\\', '\\') for p in parts]
            while len(parts) < 3:
                parts.append('')

            ssid, psk, bssid = parts[:3]
            bssid = bssid.lower()
            bssid = re.sub('([a-f0-9]{2})', '\\1:', bssid).strip(':')  # Add colons

            system.net.set_wifi_config(ssid, psk, bssid)
            reboot_required = True

        elif name == 'network_ip' and system.net.has_network_ip_support():
            if value:
                parts = value.split(':')
                ip_mask, gw, dns = parts
                ip, mask = ip_mask.split('/')
                system.net.set_ip_config(ip, mask, gw, dns)

            else:
                system.net.set_ip_config(ip='', mask='', gw='', dns='')

            reboot_required = True

    return reboot_required


def to_json():
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

    result = get_attrs()
    result['definitions'] = filtered_attrdefs

    return result
