
import asyncio
import copy
import re
import time

from qtoggleserver.core import ports as core_ports
from qtoggleserver.core import responses as core_responses

from . import exceptions


_DEVICE_EXPRESSION_RE = re.compile(r'^(device_)+expression$')

_FWUPDATE_POLL_INTERVAL = 30
_FWUPDATE_POLL_TIMEOUT = 300


class SlavePort(core_ports.BasePort):
    PERSIST_COLLECTION = 'slave_ports'

    _DEVICE_EXPRESSION_ATTRDEF = {
        'type': 'string',
        'modifiable': True,
        'max': 1024
    }

    _LAST_SYNC_ATTRDEF = {
        'type': 'number',
        'modifiable': False
    }

    _EXPIRES_ATTRDEF = {
        'type': 'number',
        'modifiable': True,
        'min': 0,
        'max': 2147483647
    }

    _PROVISIONING_ATTRDEF = {
        'type': ['string'],
        'modifiable': False
    }

    def __init__(self, slave, attrs):
        self._slave = slave

        self._remote_id = attrs['id']

        # value cache
        self._cached_value = None

        # attributes cache
        self._cached_attrs = {}

        # names of attributes that will be updated remotely asap
        self._remote_update_pending_attrs = set()

        # tag is kept locally
        self._tag = ''

        # timestamp of the last time we've heard from this port
        self._last_sync = 0

        # number of seconds before port value expires
        self._expires = 0

        # cached expired status
        self._expired = False

        # names of attributes (including value) that have been changed
        # while device was offline and have to be provisioned later
        self._provisioning = set()

        port_id = '{}.{}'.format(slave.get_name(), self._remote_id)

        super().__init__(port_id)

        self.update_cached_attrs(attrs)

        if self._cached_value is not None:
            # remote value is supplied in attrs when a new port is added on the slave device

            self._value = self._cached_value
            self.update_last_sync()

    def _get_standard_attrdefs(self):
        attrdefs = copy.copy(core_ports.STANDARD_ATTRDEFS)

        # device_*_expression
        for i in range(1, 10):
            slave_name = (i - 1) * 'device_' + 'expression'
            master_name = i * 'device_' + 'expression'
            if slave_name not in self._cached_attrs:
                break

            attrdefs[master_name] = dict(self._DEVICE_EXPRESSION_ATTRDEF)

        # various master-specific standard attributes
        attrdefs['last_sync'] = dict(self._LAST_SYNC_ATTRDEF)
        attrdefs['expires'] = dict(self._EXPIRES_ATTRDEF)
        attrdefs['provisioning'] = dict(self._PROVISIONING_ATTRDEF)

        return attrdefs

    STANDARD_ATTRDEFS = property(_get_standard_attrdefs)

    def _get_additional_attrdefs(self):
        return copy.copy(self._cached_attrs.get('definitions', {}))

    ADDITIONAL_ATTRDEFS = property(_get_additional_attrdefs)

    def map_id(self, new_id):
        raise core_ports.PortError('slave ports cannot be mapped')

    def get_remote_id(self):
        return self._remote_id

    async def get_attr(self, name):
        # id - always use the special slave.id notation
        # tag - always kept on master, ignored on slave
        # expression - kept and managed on master, separate attribute for slave
        # device_expression - mapped to expression on slave
        # online - use slave value unless slave itself offline or port disabled
        # expires - always kept on master, ignored on slave

        if name in ('id', 'tag', 'expression', 'online', 'last_sync', 'expires'):
            return await super().get_attr(name)

        elif _DEVICE_EXPRESSION_RE.match(name):
            return self.get_cached_attr(name[7:])

        value = self._cached_attrs.get(name)
        if value is not None:
            return value

        return await super().get_attr(name)

    async def set_attr(self, name, value):
        if name in ('tag', 'expression', 'last_sync', 'expires'):
            # attributes that always stay locally, on master
            await super().set_attr(name, value)

        else:
            if _DEVICE_EXPRESSION_RE.match(name):
                name = name[7:]

            if self._slave.is_online():
                self._remote_update_pending_attrs.add((name, value))

                # skip an IO loop iteration, allowing setting multiple attributes in one request
                await asyncio.sleep(0)

                try:
                    await self._update_attrs_remotely()

                except Exception as e:
                    # map exceptions to specific slave API errors
                    raise exceptions.adapt_api_error(e) from e

            else:  # offline
                # allow provisioning for offline devices
                self.debug('marking attribute %s for provisioning', name)
                self._provisioning.add(name)
                self._cached_attrs[name] = value

                # skip an IO loop iteration, allowing setting multiple attributes before triggering a port-update
                await asyncio.sleep(0)
                self.trigger_update()

    def get_cached_attr(self, name):
        return self._cached_attrs.get(name)

    def get_cached_attrs(self):
        return dict(self._cached_attrs)

    def update_cached_attrs(self, attrs):
        # use fire-and-forget here to enable/disable ports, as this method cannot be async
        if attrs.get('enabled') and not self.is_enabled():
            asyncio.create_task(self.enable())

        elif not attrs.get('enabled') and self.is_enabled():
            asyncio.create_task(self.disable())

        self._cached_attrs = dict(attrs)

        # value can be found among attrs but we don't want it as attribute
        if 'value' in attrs:
            self._cached_value = self._cached_attrs.pop('value')

        self.invalidate_attrs()
        self.invalidate_attrdefs()

    async def _update_attrs_remotely(self):
        if not self._remote_update_pending_attrs:
            return

        body = {}
        for name, value in self._remote_update_pending_attrs:
            # transform expressions reference themselves locally via the slave.id identifier;
            # we need to remove the slave name prefix before sending it to the slave
            if name in ('transform_read', 'transform_write'):
                value = value.replace(self._id, self._remote_id)

            body[name] = value

        self._remote_update_pending_attrs = set()

        try:
            await self._slave.api_call('PATCH', '/ports/{}'.format(self._remote_id), body)
            self.debug('successfully updated attributes remotely')

        except Exception as e:
            self.debug('failed to update attributes remotely: %s', e)

            raise

    async def is_persisted(self):
        # ports belonging to permanently offline devices
        # should always behave as persisted on master

        if self._slave.is_permanently_offline():
            return True

        return await core_ports.BasePort.is_persisted(self)

    async def attr_is_online(self):
        if not self._enabled:
            return False

        if self._expired:
            return False

        if not self._expires and not self._slave.is_online():
            return False

        return self._cached_attrs.get('online', True)

    async def attr_get_provisioning(self):
        return list(self._provisioning)

    def get_provisioning_attrs(self):
        provisioning = {}
        for name in self._provisioning:
            value = self._cached_attrs.get(name)
            if value is not None:
                provisioning[name] = value

        return provisioning

    def get_provisioning_value(self):
        if 'value' in self._provisioning:
            return self._cached_value

        return None

    def clear_provisioning(self):
        self._provisioning = set()

    def get_cached_value(self):
        return self._cached_value

    def set_cached_value(self, value):
        self._cached_value = value

    async def read_value(self):
        return self._cached_value

    async def write_value(self, value):
        if self._slave.is_online():
            try:
                await self._slave.api_call('PATCH', '/ports/{}/value'.format(self._remote_id), value)

            except core_responses.HTTPError as e:
                if e.code == 502 and e.msg.startswith('port error:'):
                    raise core_ports.PortError(e.msg.split(':', 1)[1].strip())

                if e.code == 504 and e.msg == 'port timeout':
                    raise core_ports.PortTimeout()

                raise exceptions.adapt_api_error(e) from e

        else:  # offline
            # allow provisioning for offline devices
            self.debug('marking value for provisioning')
            self._cached_value = value
            self._provisioning.add('value')
            await self.save()  # save provisioning value

            # we need to trigger a port-update because
            # our provisioning attribute has changed
            self.trigger_update()

    async def set_sequence(self, values, delays, repeat):
        if not self._slave.is_online():
            raise exceptions.DeviceOffline(self._slave)

        try:
            await self._slave.api_call('POST', '/ports/{}/sequence'.format(self._remote_id),
                                       {'values': values, 'delays': delays, 'repeat': repeat})
            self.debug('sequence sent remotely')

        except Exception as e:
            self.error('failed to send sequence remotely: %s', e)

            # map exceptions to specific slave API errors
            raise exceptions.adapt_api_error(e) from e

    def heart_beat_second(self):
        was_expired = self._expired
        now_expired = (self._expires > 0) and (time.time() - self._last_sync > self._expires)
        self._expired = now_expired

        if was_expired != now_expired:
            if now_expired:
                self.debug('value expired')

            self.trigger_update()

    async def load_from_data(self, data):
        attrs = data.get('attrs')
        if attrs:
            if 'value' in data:
                attrs['value'] = data['value']

            self.update_cached_attrs(attrs)

        # attributes that are kept on master
        for attr in ('tag', 'expression', 'last_sync', 'expires'):
            if attr in data:
                await self.set_attr(attr, data[attr])

        self._provisioning = set(data.get('provisioning', []))

    async def prepare_for_save(self):
        return {
            'id': self.get_id(),
            'tag': self._tag,
            'expression': str(self._expression or ''),
            'last_sync': self._last_sync,
            'expires': self._expires,
            'provisioning': list(self._provisioning),
            'attrs': self._cached_attrs,
            'value': self._cached_value
        }

    def update_last_sync(self):
        self._last_sync = int(time.time())
