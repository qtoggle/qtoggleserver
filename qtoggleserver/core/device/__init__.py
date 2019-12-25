
import logging

from qtoggleserver import persist
from qtoggleserver.conf import settings
from qtoggleserver.utils import json as json_utils
from qtoggleserver.utils.cmd import run_get_cmd

from . import attrs as device_attrs


logger = logging.getLogger(__name__)


def get_display_name():
    return device_attrs.display_name or device_attrs.name


def load():
    data = persist.get_value('device', {})

    # attributes
    persisted_attrs = []
    for name, value in device_attrs.ATTRDEFS.items():
        persisted = value.get('persisted', value.get('modifiable'))
        if callable(persisted):
            persisted = persisted()

        if persisted:
            persisted_attrs.append(name)

    for name in persisted_attrs:
        if name.endswith('password') and hasattr(device_attrs, name + '_hash'):
            name += '_hash'

        if name not in data:
            continue

        value = data[name]

        # a few attributes may carry sensitive information
        # treat them separately and do not log their values
        if name.count('password'):
            logger.debug('loaded %s', name)

        elif name == 'network_wifi':
            logger.debug('loaded %s = [hidden]', name)

        else:
            logger.debug('loaded %s = %s', name, json_utils.dumps(value))

        setattr(device_attrs, name, value)

    # device name
    if settings.device_name.get_cmd:
        result = run_get_cmd(settings.device_name.get_cmd, cmd_name='device name', required_fields=['name'])
        device_attrs.name = result['name']

    # hash empty passwords
    if not device_attrs.admin_password_hash:
        device_attrs.admin_password_hash = device_attrs.EMPTY_PASSWORD_HASH
    if not device_attrs.normal_password_hash:
        device_attrs.normal_password_hash = device_attrs.EMPTY_PASSWORD_HASH
    if not device_attrs.viewonly_password_hash:
        device_attrs.viewonly_password_hash = device_attrs.EMPTY_PASSWORD_HASH


def save():
    data = {}

    # attributes
    persisted_attrs = []
    for name, value in device_attrs.ATTRDEFS.items():
        persisted = value.get('persisted', value.get('modifiable'))
        if callable(persisted):
            persisted = persisted()

        if persisted:
            persisted_attrs.append(name)

    for name in persisted_attrs:
        if name.endswith('password') and hasattr(device_attrs, name + '_hash'):
            name += '_hash'

        data[name] = getattr(device_attrs, name)

    logger.debug('saving device data')
    persist.set_value('device', data)


def reset():
    logger.debug('clearing device persisted data')
    persist.remove('device')
