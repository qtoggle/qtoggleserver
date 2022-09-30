import asyncio
import copy
import re
import time

from collections import deque
from typing import Any, Optional

from qtoggleserver.conf import settings
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core import responses as core_responses
from qtoggleserver.core.typing import (
    Attribute,
    AttributeDefinitions,
    Attributes,
    GenericJSONDict,
    NullablePortValue,
    PortValue,
)

from . import exceptions


_DEVICE_EXPRESSION_RE = re.compile(r'^(device_)+expression$')
_DEVICE_HISTORY_RE = re.compile(r'^(device_)+history_[a-z0-9_]+$')

MASTER_ATTRS = {
    'id',                        # always use the special slave.id notation
    'tag',                       # always kept on master, ignored on slave
    'expression',                # kept and managed on master, separate attribute for slave
    'history_interval',          # kept and managed on master, separate attribute for slave
    'history_retention',         # kept and managed on master, separate attribute for slave
    'online',                    # use slave value unless slave itself offline or port disabled
    'last_sync',                 # always kept on master, ignored on slave
    'expires',                   # always kept on master, ignored on slave
}


# We can't use proper type annotations for slaves in this module because that would create unsolvable circular imports.
# Therefore, we use "Any" type annotation for Slave instances.


class SlavePort(core_ports.BasePort):
    PERSIST_COLLECTION = 'slave_ports'

    _DEVICE_EXPRESSION_ATTRDEF = {
        'type': 'string',
        'modifiable': True,
        'max': 1024
    }

    _DEVICE_HISTORY_INTERVAL_ATTRDEF = {
        'type': 'number',
        'integer': True,
        'modifiable': True,
        'min': -1,
        'max': 2147483647
    }

    _DEVICE_HISTORY_RETENTION_ATTRDEF = {
        'type': 'number',
        'integer': True,
        'modifiable': True,
        'min': 0,
        'max': 2147483647
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

    def __init__(self, slave: Any, attrs: Attributes) -> None:
        from .devices import Slave  # we need this import here just for Slave type annotation

        self._slave: Slave = slave

        self._remote_id: str = attrs['id']

        # Value
        self._cached_value: NullablePortValue = None
        self._remote_value_queue: deque = deque()

        # Attributes cache
        self._cached_attrs: Attributes = {}

        # Names of attributes that will be updated remotely asap
        self._remote_update_pending_attrs: set[tuple[str, Attribute]] = set()

        # Tag is kept locally
        self._tag: str = ''

        # Timestamp of the last time we've heard from this port
        self._last_sync: float = 0

        # Number of seconds before port value expires
        self._expires: int = 0

        # Cached expired status
        self._expired: bool = False

        # Names of attributes (including value) that have been changed while device was offline and have to be
        # provisioned later
        self._provisioning: set[str] = set()

        # Helps managing the triggering of port-update event from non-async methods
        self._trigger_update_task: Optional[asyncio.Task] = None

        port_id = f'{slave.get_name()}.{self._remote_id}'

        super().__init__(port_id)

        self.update_cached_attrs(attrs)

        if self.get_last_remote_value() is not None:
            # Remote value is supplied in attrs when a new port is added on the slave device
            self.update_last_sync()

    def _get_standard_attrdefs(self) -> AttributeDefinitions:
        attrdefs = copy.copy(core_ports.STANDARD_ATTRDEFS)

        # device_*expression
        for i in range(1, 10):
            slave_name = (i - 1) * 'device_' + 'expression'
            master_name = i * 'device_' + 'expression'
            if slave_name not in self._cached_attrs:
                break

            attrdefs[master_name] = dict(self._DEVICE_EXPRESSION_ATTRDEF)

        # device_*history_interval
        for i in range(1, 10):
            slave_name = (i - 1) * 'device_' + 'history_interval'
            master_name = i * 'device_' + 'history_interval'
            if slave_name not in self._cached_attrs:
                break

            attrdefs[master_name] = dict(self._DEVICE_HISTORY_INTERVAL_ATTRDEF)

        # device_*history_retention
        for i in range(1, 10):
            slave_name = (i - 1) * 'device_' + 'history_retention'
            master_name = i * 'device_' + 'history_retention'
            if slave_name not in self._cached_attrs:
                break

            attrdefs[master_name] = dict(self._DEVICE_HISTORY_RETENTION_ATTRDEF)

        # Various master-specific standard attributes
        attrdefs['last_sync'] = dict(self._LAST_SYNC_ATTRDEF)
        attrdefs['expires'] = dict(self._EXPIRES_ATTRDEF)
        attrdefs['provisioning'] = dict(self._PROVISIONING_ATTRDEF)

        return attrdefs

    STANDARD_ATTRDEFS = property(_get_standard_attrdefs)

    def _get_additional_attrdefs(self) -> AttributeDefinitions:
        return copy.copy(self._cached_attrs.get('definitions', {}))

    ADDITIONAL_ATTRDEFS = property(_get_additional_attrdefs)

    def map_id(self, new_id: str) -> None:
        raise core_ports.PortError('Slave ports cannot be mapped')

    def get_remote_id(self) -> str:
        return self._remote_id

    async def get_attr(self, name: str) -> Optional[Attribute]:
        # device_expression        - mapped to expression on slave
        # device_history_interval  - mapped to history_interval on slave
        # device_history_retention - mapped to history_retention on slave

        if name in MASTER_ATTRS:
            return await super().get_attr(name)
        elif _DEVICE_EXPRESSION_RE.match(name) or _DEVICE_HISTORY_RE.match(name):  # strip leading "device_"
            return self.get_cached_attr(name[7:])

        value = self._cached_attrs.get(name)
        if value is not None:
            return value

        return await super().get_attr(name)

    async def set_attr(self, name: str, value: Attribute) -> None:
        if name in MASTER_ATTRS:
            # Attributes that always stay locally, on master
            await super().set_attr(name, value)
        else:
            if _DEVICE_EXPRESSION_RE.match(name) or _DEVICE_HISTORY_RE.match(name):  # strip leading "device_"
                name = name[7:]

            if self._slave.is_online():
                self._remote_update_pending_attrs.add((name, value))

                # Skip an IO loop iteration, allowing setting multiple attributes in one request
                await asyncio.sleep(0)

                try:
                    await self._update_attrs_remotely()
                except Exception as e:
                    # Map exceptions to specific slave API errors
                    raise exceptions.adapt_api_error(e) from e
            else:  # offline
                # Allow provisioning for offline devices
                self.debug('marking attribute %s for provisioning', name)
                self._provisioning.add(name)
                self._cached_attrs[name] = value

                await self.trigger_update()

    def get_cached_attr(self, name: str) -> Optional[Attribute]:
        return self._cached_attrs.get(name)

    def get_cached_attrs(self) -> Attributes:
        return dict(self._cached_attrs)

    def update_cached_attrs(self, attrs: Attributes) -> None:
        self._cached_attrs = dict(attrs)

        # Value can be found among attrs but we don't want it as attribute
        if 'value' in attrs:
            self.push_remote_value(self._cached_attrs.pop('value'))

        self.invalidate_attrdefs()

    async def update_enabled(self) -> None:
        if self._cached_attrs.get('enabled') and not self.is_enabled():
            await self.enable()
        elif not self._cached_attrs.get('enabled') and self.is_enabled():
            await self.disable()

    async def _update_attrs_remotely(self) -> None:
        if not self._remote_update_pending_attrs:
            return

        body = {}
        for name, value in self._remote_update_pending_attrs:
            # Transform expressions reference themselves locally via the slave.id identifier; we need to remove the
            # slave name prefix before sending it to the slave
            if name in ('transform_read', 'transform_write'):
                value = value.replace(self._id, self._remote_id)

            body[name] = value

        self._remote_update_pending_attrs = set()

        try:
            await self._slave.api_call('PATCH', f'/ports/{self._remote_id}', body, timeout=settings.slaves.long_timeout)
            self.debug('successfully updated attributes remotely')
        except Exception as e:
            self.debug('failed to update attributes remotely: %s', e)

            raise

    async def is_persisted(self) -> bool:
        # Ports belonging to permanently offline devices should always behave as persisted on master

        if self._slave.is_permanently_offline():
            return True

        return await core_ports.BasePort.is_persisted(self)

    async def attr_is_online(self) -> bool:
        if not self._enabled:
            return False

        if self._expired:
            return False

        if not self._expires and not self._slave.is_online():
            return False

        return self._cached_attrs.get('online', True)

    async def attr_get_provisioning(self) -> list[str]:
        return list(self._provisioning)

    def get_provisioning_attrs(self) -> Attributes:
        provisioning = {}
        for name in self._provisioning:
            value = self._cached_attrs.get(name)
            if value is not None:
                provisioning[name] = value

        return provisioning

    def get_provisioning_value(self) -> Optional[PortValue]:
        if 'value' in self._provisioning:
            return self._cached_value

        return None

    def clear_provisioning(self) -> None:
        self._provisioning = set()

    def push_remote_value(self, value: PortValue) -> None:
        self._remote_value_queue.appendleft(value)

    def get_last_remote_value(self) -> NullablePortValue:
        try:
            return self._remote_value_queue[0]
        except IndexError:
            return self._cached_value

    async def read_value(self) -> NullablePortValue:
        try:
            self._cached_value = self._remote_value_queue.pop()
            return self._cached_value
        except IndexError:
            return

    async def write_value(self, value: PortValue) -> None:
        if self._slave.is_online():
            try:
                await self._slave.api_call(
                    'PATCH',
                    f'/ports/{self._remote_id}/value',
                    value,
                    timeout=settings.slaves.long_timeout
                )
                self.push_remote_value(value)
            except core_responses.Accepted:
                # The value has been successfully sent to the slave but it hasn't been applied right away. We should
                # update the cached value later, as soon as we receive a corresponding value-change event.
                pass
            except core_responses.HTTPError as e:
                if e.code == 502 and e.code == 'port-error':
                    message = e.params.get('message')
                    if message:
                        raise core_ports.PortError(message)
                    else:
                        raise core_ports.PortError()

                if e.code == 504 and e.code == 'port-timeout':
                    raise core_ports.PortTimeout()

                raise exceptions.adapt_api_error(e) from e
        else:  # offline
            # Allow provisioning for offline devices
            self.debug('marking value for provisioning')
            self._cached_value = value
            self._provisioning.add('value')
            await self.save()  # save provisioning value

            # We need to trigger a port-update because our provisioning attribute has changed
            await self.trigger_update()

    async def set_sequence(self, values: list[PortValue], delays: list[int], repeat: int) -> None:
        if not self._slave.is_online():
            raise exceptions.DeviceOffline(self._slave)

        try:
            await self._slave.api_call(
                'PATCH',
                f'/ports/{self._remote_id}/sequence',
                {'values': values, 'delays': delays, 'repeat': repeat}
            )
            self.debug('sequence sent remotely')
        except Exception as e:
            self.error('failed to send sequence remotely: %s', e)

            # Map exceptions to specific slave API errors
            raise exceptions.adapt_api_error(e) from e

    def heart_beat_second(self) -> None:
        was_expired = self._expired
        now_expired = (self._expires > 0) and (time.time() - self._last_sync > self._expires)
        self._expired = now_expired

        if was_expired != now_expired:
            if now_expired:
                self.debug('value expired')

            if not self._trigger_update_task:
                self._trigger_update_task = asyncio.create_task(self.trigger_update())

    async def load_from_data(self, data: GenericJSONDict) -> None:
        # Only consider locally persisted attributes for permanently offline devices. For online devices, we always use
        # fresh attributes received from device.
        attrs = data.get('attrs')
        if attrs and self._slave.is_permanently_offline():
            if 'value' in data:
                attrs['value'] = data['value']

            self.update_cached_attrs(attrs)

        # Attributes that are kept on master
        for attr in MASTER_ATTRS:
            if attr in data:
                await self.set_attr(attr, data[attr])

        self._history_last_timestamp = data.get('history_last_timestamp', 0)
        self._provisioning = set(data.get('provisioning', []))

        # Enable if enabled remotely
        await self.update_enabled()

    async def prepare_for_save(self) -> GenericJSONDict:
        return {
            'id': self.get_id(),
            'tag': self._tag,
            'expression': str(self._expression or ''),
            'history_interval': self._history_interval,
            'history_retention': self._history_retention,
            'history_last_timestamp': self._history_last_timestamp,
            'last_sync': self._last_sync,
            'expires': self._expires,
            'provisioning': list(self._provisioning),
            'attrs': self._cached_attrs,
            'value': self._cached_value
        }

    def update_last_sync(self) -> None:
        self._last_sync = int(time.time())

    async def handle_enable(self) -> None:
        # Fetch current port value, but not before slaves are ready. Slaves aren't ready during initial loading at
        # startup, at which point we've got recent values for all slave ports
        if self._slave.is_ready():
            self.debug('fetching port value')

            try:
                value = await self._slave.api_call('GET', f'/ports/{self._remote_id}/value', retry_counter=None)
            except Exception as e:
                self.error('failed to fetch port value: %s', e)
            else:
                if value is not None:
                    self.push_remote_value(value)

    async def trigger_update(self) -> None:
        await super().trigger_update()

        self._trigger_update_task = None

    async def cleanup(self) -> None:
        await super().cleanup()

        if self._trigger_update_task:
            await self._trigger_update_task
