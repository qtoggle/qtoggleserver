
import calendar
import copy
import datetime
import hashlib
import json
import logging
import os
import re
import socket
import subprocess
import sys

from qtoggleserver import system
from qtoggleserver import version
from qtoggleserver.conf import settings
from qtoggleserver.core import api as core_api


logger = logging.getLogger(__name__)

STANDARD_ATTRDEFS = {
    'name': {
        'type': 'string',
        'modifiable': True,
        'persisted': lambda: not bool(settings.device_name_hooks.set),
        'min': 1,
        'max': 32,
        'pattern': r'^[_a-zA-Z]?[_a-z-A-Z0-9]*$',
    },
    'display_name': {
        'type': 'string',
        'modifiable': True,
        'max': 64
    },
    'version': {
        'type': 'string'
    },
    'api_version': {
        'type': 'string'
    },
    'admin_password': {
        'type': 'string',
        'modifiable': True,
        'max': 32
    },
    'normal_password': {
        'type': 'string',
        'modifiable': True,
        'max': 32
    },
    'viewonly_password': {
        'type': 'string',
        'modifiable': True,
        'max': 32
    },
    'flags': {
        'type': ['string']
    },
    'virtual_ports': {
        'type': 'number',
        'enabled': lambda: bool(settings.core.virtual_ports)
    },
    'uptime': {
        'type': 'number'
    },
    'date': {
        'type': 'string',
        'pattern': r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$',
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: settings.system.date_support
    },
    'timezone': {
        'type': 'string',
        'modifiable': True,
        'persisted': False,
        'choices': [{'value': zone} for zone in system.date.get_timezones()],
        'enabled': lambda: system.date.has_timezone_support()
    },
    'network_ip': {
        'type': 'string',
        'pattern': r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,3}\.\d{1,'
                   r'3}\.\d{1,3}\.\d{1,3})|$',
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: bool(settings.system.network_interface)
    },
    'network_wifi': {
        'type': 'string',
        # TODO this regex should ignore escaped colons \:
        'pattern': r'^(([^:]{0,32}:?)|([^:]{0,32}:[^:]{0,64}:?)|([^:]{0,32}:[^:]{0,64}:[0-9a-fA-F]{12}))$',
        'modifiable': True,
        'persisted': False,
        'enabled': lambda: bool(settings.system.wpa_supplicant_conf)
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
            if not enabled:
                continue

            if callable(enabled) and not enabled():
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
                attr_schema['enum'] = [i['value'] for i in attr_schema.pop('choices')]

            attr_schema.pop('persisted', None)
            attr_schema.pop('modifiable', None)

            _schema['properties'][name] = attr_schema

    return _schema


def get_attrs():
    attrs = {
        'name': name,
        'display_name': display_name,
        'version': version.VERSION,
        'api_version': core_api.API_VERSION,
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

    if settings.system.date_support:
        attrs['date'] = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    if system.date.has_timezone_support():
        attrs['timezone'] = system.date.get_timezone()

    if settings.system.wpa_supplicant_conf:
        wifi = system.net.get_wifi(settings.system.wpa_supplicant_conf)
        if wifi['bssid']:
            attrs['network_wifi'] = '{}:{}:{}'.format(wifi['ssid'], wifi['psk'], wifi['bssid'])

        elif wifi['psk']:
            attrs['network_wifi'] = '{}:{}'.format(wifi['ssid'], wifi['psk'])

        else:
            attrs['network_wifi'] = wifi['ssid']

    if settings.system.network_interface:
        ip_config = system.net.get_ip_config(settings.system.network_interface)
        attrs['network_ip'] = '{}/{}:{}:{}'.format(ip_config['ip'], ip_config['mask'],
                                                   ip_config['gw'], ip_config['dns'])

    return attrs


def set_attrs(attrs):
    core_device_attrs = sys.modules[__name__]

    ip_config = None
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
            logger.debug('setting device attribute %s = %s', name, json.dumps(value))

        attrdef = ATTRDEFS[name]

        if not attrdef.get('modifiable'):
            return 'attribute not modifiable: {}'.format(name)

        if name.endswith('_password') and hasattr(core_device_attrs, name + '_hash'):
            # call password hook, if set
            if settings.password_hook:
                env = {
                    'QS_USERNAME': name[:-9],
                    'QS_PASSWORD': value
                }

                try:
                    subprocess.check_output(settings.password_hook, env=env, stderr=subprocess.STDOUT)
                    logger.debug('password hook exec succeeded')

                except Exception as e:
                    logger.error('password hook call failed: %s', e)

            value = hashlib.sha256(value.encode()).hexdigest()

            name += '_hash'

            setattr(core_device_attrs, name, value)
            continue

        persisted = attrdef.get('persisted', attrdef.get('modifiable'))
        if callable(persisted):
            persisted = persisted()
        if persisted:
            setattr(core_device_attrs, name, value)
            continue

        if name == 'name' and settings.device_name_hooks.set:
            env = {'QS_HOSTNAME': value}

            try:
                subprocess.check_output(settings.device_name_hooks.set, env=env, stderr=subprocess.STDOUT)
                core_device_attrs.name = value
                logger.debug('device name set hook exec succeeded')

            except Exception as e:
                logger.error('device name set hook call failed: %s', e)

            continue

        if name == 'date' and settings.system.date_support:
            try:
                date = datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')

            except ValueError:
                return 'invalid field: {}'.format(name)

            time = int(calendar.timegm(date.timetuple()))
            if os.system('date +%s -s{}'.format(date)):
                logger.error('date call failed')

                raise Exception(500, 'date call failed')  # TODO a more specific exception?

            else:
                logger.debug('system date set to %s', time)

                continue

        if name == 'timezone' and system.date.has_timezone_support():
            system.date.set_timezone(value)
            continue

        if settings.system.wpa_supplicant_conf:
            if name == 'network_wifi':
                parts = re.split(r'[^\\]:', value)
                parts = [p.replace('\\:', ':') for p in parts]

                while len(parts) < 3:
                    parts.append('')

                ssid, psk, bssid = parts[:3]

                system.net.set_wifi(settings.system.wpa_supplicant_conf, ssid, psk, bssid)
                reboot_required = True
                continue

        if settings.system.network_interface:
            if name == 'network_ip':
                ip_config = value
                continue

        return 'no such attribute: {}'.format(name)

    if ip_config is not None:
        system.net.set_ip_config(settings.system.network_interface, **ip_config)
        reboot_required = True

    return reboot_required


def to_json():
    attrdefs = copy.deepcopy(ADDITIONAL_ATTRDEFS)
    for attrdef in attrdefs.values():
        attrdef.pop('persisted', None)
        attrdef.pop('pattern', None)
        attrdef.pop('enabled', None)

    result = get_attrs()
    result['definitions'] = attrdefs

    return result
