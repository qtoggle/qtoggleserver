
from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import re
import time
import types

from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from qtoggleserver import persist
from qtoggleserver.core import api as core_api
from qtoggleserver.core import events as core_events
from qtoggleserver.core import main as core_main
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core import responses as core_responses
from qtoggleserver.conf import settings
from qtoggleserver.core.api import auth as core_api_auth
from qtoggleserver.core.api import schema as core_api_schema
from qtoggleserver.core.device import attrs as core_device_attrs
from qtoggleserver.core.typing import Attribute, Attributes, GenericJSONDict, NullablePortValue
from qtoggleserver.utils import asyncio as asyncio_utils
from qtoggleserver.utils import json as json_utils
from qtoggleserver.utils import logging as logging_utils

from . import events
from . import exceptions
from .ports import SlavePort


_MAX_PARALLEL_API_CALLS = 2
_MAX_QUEUED_API_CALLS = 256
_INVALID_EXPRESSION_FIELD_RE = re.compile(r'^((device_)*expression)$')
_FWUPDATE_POLL_INTERVAL = 30
_FWUPDATE_POLL_TIMEOUT = 300
_NO_EVENT_DEVICE_ATTRS = ['uptime', 'date']
_DEFAULT_POLL_INTERVAL = 10


_slaves_by_name: Dict[str, Slave] = {}
_load_time: float = 0

logger = logging.getLogger(__name__)


class Slave(logging_utils.LoggableMixin):
    def __init__(
        self,
        name: Optional[str],
        scheme: str,
        host: str,
        port: int,
        path: str,
        poll_interval: int = 0,
        listen_enabled: bool = False,
        admin_password: Optional[str] = None,
        admin_password_hash: Optional[str] = None,
        last_sync: int = -1,
        attrs: Optional[Attributes] = None,
        webhooks: Optional[GenericJSONDict] = None,
        reverse: Optional[GenericJSONDict] = None,
        provisioning_attrs: Optional[Set[str]] = None,
        provisioning_webhooks: Optional[Set[str]] = None,
        provisioning_reverse: Optional[Set[str]] = None,
        **kwargs
    ) -> None:

        # The enabled value comes with kwargs but is ignored, as the slave will be explicitly enabled afterwards

        logging_utils.LoggableMixin.__init__(self, name, logger)
        if not name:
            self.set_logger_name(f'{host}:{port}')

        self._name: Optional[str] = name
        self._scheme: str = scheme
        self._host: str = host
        self._port: int = port
        self._path: str = path
        self._poll_interval: int = poll_interval
        self._listen_enabled: bool = listen_enabled

        if admin_password is not None:
            self._admin_password_hash: str = hashlib.sha256(admin_password.encode()).hexdigest()

        else:
            self._admin_password_hash: str = admin_password_hash

        # Indicates the online status
        self._enabled: bool = False

        # Indicates the online status
        self._online: bool = False

        # Used to tell initial offline -> online transition from subsequent transitions
        self._initial_online: bool = True

        # Timestamp when we last heard from this device
        self._last_sync: float = last_sync

        # Indicates whether all data required for this slave is present locally
        self._ready: bool = False

        # API call throttling
        self._parallel_api_caller = asyncio_utils.ParallelCaller(_MAX_PARALLEL_API_CALLS, _MAX_QUEUED_API_CALLS)

        # Indicates the listening session id, or None if no listen client is active
        self._listen_session_id: Optional[str] = None
        self._listen_task: Optional[asyncio.Task] = None

        # Tells the polling mechanism status
        self._poll_started: bool = False
        self._poll_task: Optional[asyncio.Task] = None

        # Attributes cache
        self._cached_attrs: Attributes = attrs or {}

        # Webhooks parameters cache
        self._cached_webhooks: GenericJSONDict = webhooks or {}

        # Reverse API calls cache
        self._cached_reverse: GenericJSONDict = reverse or {}

        # Names of attributes that have been changed while device was offline and have to be provisioned later
        self._provisioning_attrs: Set[str] = set(provisioning_attrs or [])

        # Webhooks params that have been changed while device was offline and have to be provisioned later
        self._provisioning_webhooks: Set[str] = set(provisioning_webhooks or [])

        # Reverse params that have been changed while device was offline and have to be provisioned later
        self._provisioning_reverse: Set[str] = set(provisioning_reverse or [])

        # Used to schedule provisioning + local update for permanently offline slaves
        self._provisioning_timeout_task: Optional[asyncio.Task] = None

        # An internal reference to the last made API call
        self._last_api_call_ref: Any = None

        # Cached url
        self._url: Optional[str] = None

        # Handles firmware update progress
        self._fwupdate_poll_task: Optional[asyncio.Task] = None

    def __str__(self) -> str:
        if self._name:
            return f'slave {self._name} at {self.get_url()}'

        else:
            return f'slave at {self.get_url()}'

    def __eq__(self, s: Slave) -> bool:
        return (self._scheme == s.get_scheme() and self._host == s.get_host() and
                self._port == s.get_port() and self._path == s.get_path())

    def get_url(self, path: Optional[str] = None) -> str:
        if path:
            url = self.get_url()
            while url.endswith('/'):
                url = url[:-1]

            return url + path

        if not self._url:
            if self._scheme == 'http' and self._port == 80 or self._scheme == 'https' and self._port == 443:
                self._url = f'{self._scheme}://{self._host}{self._path}'

            else:
                self._url = f'{self._scheme}://{self._host}:{self._port}{self._path}'

        return self._url

    def get_cached_attr(self, name: str) -> Optional[Attribute]:
        return self._cached_attrs.get(name)

    def get_cached_attrs(self) -> Attributes:
        return self._cached_attrs

    async def update_cached_attrs(self, attrs: Attributes, partial: bool = False) -> None:
        # If the name has changed remove the device and re-add the device from scratch

        if attrs.get('name'):
            name = attrs['name']
            if name != self._name:
                if self._name is not None:
                    self.debug('detected name change to %s', name)

                    # Disable device before removing it
                    if self.is_enabled():
                        await self.disable()

                        # We have to trigger an update event here, to inform consumers about disabling
                        await self.trigger_update()

                    # Check for duplicate name
                    if name in _slaves_by_name or core_device_attrs.name == name:
                        logger.error('a slave with name %s already exists', name)
                        raise exceptions.DeviceAlreadyExists(name)

                    # Rename associated ports persisted data
                    try:
                        self._rename_ports_persisted_data(name)

                    except Exception as e:
                        logger.error('renaming ports persisted data failed: %s', e, exc_info=True)

                    # Actually remove the slave
                    await remove(self)

                    # Add the slave back
                    future = add(
                        self._scheme,
                        self._host,
                        self._port,
                        self._path,
                        self._poll_interval,
                        self._listen_enabled,
                        admin_password_hash=self._admin_password_hash
                    )

                    asyncio.create_task(future)

                    raise exceptions.DeviceRenamed(self)

                else:
                    self.debug('got real name: %s', name)
                    self._name = name
                    self.set_logger_name(name)

        if partial:
            self._cached_attrs.update(attrs)

        else:
            self._cached_attrs = attrs

    def get_name(self) -> str:
        return self._name

    def get_display_name(self) -> str:
        return self._cached_attrs.get('display_name') or self._name

    def get_scheme(self) -> str:
        return self._scheme

    def get_host(self) -> str:
        return self._host

    def get_port(self) -> int:
        return self._port

    def get_path(self) -> str:
        return self._path

    def get_admin_password_hash(self) -> str:
        return self._admin_password_hash

    def set_admin_password(self, admin_password: str) -> None:
        self._admin_password_hash = hashlib.sha256(admin_password.encode()).hexdigest()

    def is_ready(self) -> bool:
        return self._ready

    def is_online(self) -> bool:
        return self._online

    def update_last_sync(self) -> None:
        self._last_sync = int(time.time())

    def is_enabled(self) -> bool:
        return self._enabled

    async def enable(self) -> None:
        if self._enabled:
            return

        self.debug('enabling device')
        self._enabled = True
        self._ready = False
        self._online = False

        # Start polling/listening mechanism
        if self._poll_interval:
            self._start_polling()

        elif self._listen_enabled:
            self._start_listening()

        # For permanently offline devices, we can't do an initial port discovery. We will need to load ports from
        # persisted data.
        #
        # We can't await for the _load_ports() result, because we expect callers of enable() to generate
        # slave-device-update events, and we want any port-related events generated by _load_ports() to come after.
        if self.is_permanently_offline() and self._name:
            asyncio.create_task(self._load_ports())

    async def disable(self) -> None:
        if not self._enabled:
            return

        self.debug('disabling device')
        self._enabled = False
        self._ready = False

        # Stop listening
        if self._listen_session_id:
            self._stop_listening()

        # Stop polling
        if self._poll_started:
            self._stop_polling()

        # Remove ports
        self.debug('removing ports')
        for port in self._get_local_ports():
            await port.remove(persisted_data=False)

        # Mark offline
        self._online = False

    def set_poll_interval(self, poll_interval: Optional[int]) -> None:
        if self._poll_interval == poll_interval:
            return

        self._poll_interval = poll_interval

        if poll_interval:
            self.debug('polling interval set to %ss', poll_interval)

            if not self._poll_started and self._enabled:
                self._start_polling()

        else:
            self.debug('polling disabled')
            if self._poll_started:
                self._stop_polling()

            if self._online:
                # Take offline
                self._online = False
                asyncio.create_task(self._handle_offline())

    def get_poll_interval(self) -> Optional[int]:
        return self._poll_interval

    def enable_listen(self) -> None:
        if self._listen_enabled:
            return  # Already enabled

        self.debug('listening enabled')

        self._listen_enabled = True
        if not self._listen_session_id and self._enabled:
            self._start_listening()

    def disable_listen(self) -> None:
        if not self._listen_enabled:
            return  # Not enabled

        self.debug('listening disabled')

        self._listen_enabled = False
        if self._listen_session_id:
            self._stop_listening()

        if self._online:
            # Take offline
            self._online = False
            asyncio.create_task(self._handle_offline())

    def is_listen_enabled(self) -> bool:
        return self._listen_enabled

    def is_permanently_offline(self) -> bool:
        return self._poll_interval == 0 and not self._listen_enabled

    def to_json(self) -> GenericJSONDict:
        provisioning = list(self._provisioning_attrs)
        if self._provisioning_webhooks:
            provisioning.append('webhooks')
        if self._provisioning_reverse:
            provisioning.append('reverse')

        return {
            'enabled': self._enabled,
            'name': self._name,
            'scheme': self._scheme,
            'host': self._host,
            'port': self._port,
            'path': self._path,
            'poll_interval': self._poll_interval,
            'listen_enabled': self._listen_enabled,
            'last_sync': self._last_sync,
            'online': self._online,
            'provisioning': provisioning,
            'attrs': self._cached_attrs
        }

    def prepare_for_save(self) -> GenericJSONDict:
        return {
            'enabled': self._enabled,
            'name': self._name,
            'scheme': self._scheme,
            'host': self._host,
            'port': self._port,
            'path': self._path,
            'poll_interval': self._poll_interval,
            'listen_enabled': self._listen_enabled,
            'last_sync': self._last_sync,
            'admin_password_hash': self._admin_password_hash,
            'attrs': self._cached_attrs,
            'webhooks': self._cached_webhooks,
            'reverse': self._cached_reverse,
            'provisioning_attrs': list(self._provisioning_attrs),
            'provisioning_webhooks': list(self._provisioning_webhooks),
            'provisioning_reverse': list(self._provisioning_reverse),
        }

    def save(self) -> None:
        self.debug('saving device')
        persist.replace('slaves', self._name, self.prepare_for_save())

    async def cleanup(self) -> None:
        self.debug('cleaning up')

        # Stop listening
        if self._listen_session_id:
            self._stop_listening()
            await self._listen_task
            self.debug('listening stopped')

        # Stop polling
        if self._poll_started:
            self._stop_polling()
            await self._poll_task
            self.debug('polling mechanism stopped')

        # Stop fwupdate pool loop
        if self._fwupdate_poll_task and not self._fwupdate_poll_task.done():
            self._fwupdate_poll_task.cancel()
            await self._fwupdate_poll_task

        # Stop parallel API caller
        self._parallel_api_caller.stop()

    async def _load_ports(self) -> None:
        self.debug('loading persisted ports')
        port_data_list = persist.query(SlavePort.PERSIST_COLLECTION, fields=['id'])
        my_port_ids = [
            d['id'][len(self._name) + 1:] for d in port_data_list
            if d['id'].startswith(f'{self._name}.')
        ]

        for _id in my_port_ids:
            await self._add_port(attrs={'id': _id})

    async def _save_ports(self) -> None:

        self.debug('persisting ports')
        ports = self._get_local_ports()
        for port in ports:
            await port.save()

    def _rename_ports_persisted_data(self, new_name: str) -> None:
        port_data_list = persist.query(SlavePort.PERSIST_COLLECTION, fields=['id'])
        my_port_data_list = [
            d for d in port_data_list
            if d['id'].startswith(f'{self._name}.')
        ]

        # Remove old records
        for d in my_port_data_list:
            persist.remove(SlavePort.PERSIST_COLLECTION, {'id': d['id']})

        # Add new records
        for d in my_port_data_list:
            d['id'] = new_name + d['id'][len(self._name):]
            persist.insert(SlavePort.PERSIST_COLLECTION, d)

    async def remove(self) -> None:
        self._enabled = False
        self._ready = False

        await self.cleanup()

        self.debug('removing ports')
        for port in self._get_local_ports():
            await port.remove()

        # Also remove persisted port data belonging to this device for ports that are no longer present on this slave
        port_data_list = persist.query(SlavePort.PERSIST_COLLECTION, fields=['id'])
        for d in port_data_list:
            if d['id'].startswith(f'{self._name}.'):
                persist.remove(SlavePort.PERSIST_COLLECTION, {'id': d['id']})

        self.debug('removing device')
        persist.remove('slaves', filt={'id': self._name})

        await self.trigger_remove()

    async def trigger_add(self) -> None:
        await core_events.handle_event(events.SlaveDeviceAdd(self))

    async def trigger_remove(self) -> None:
        await core_events.handle_event(events.SlaveDeviceRemove(self))

    async def trigger_update(self) -> None:
        await core_events.handle_event(events.SlaveDeviceUpdate(self))

    async def api_call(
        self,
        method: str,
        path: str,
        body: Any = None,
        timeout: int = None,
        retry_counter: Optional[int] = 0
    ) -> Any:

        return await self._parallel_api_caller.call(self._api_call, method, path, body, timeout, retry_counter)

    async def _api_call(
        self,
        method: str,
        path: str,
        body: Any = None,
        timeout: int = None,
        retry_counter: Optional[int] = 0
    ) -> Any:

        if method == 'GET':
            body = None

        url = self.get_url(path)
        body_str = json_utils.dumps(body) if body is not None else None

        # Used to signal a new API call, which should prevent any pending retry
        ref = self._last_api_call_ref = {}

        http_client = AsyncHTTPClient()
        headers = {
            'Content-Type': json_utils.JSON_CONTENT_TYPE,
            'Authorization': core_api_auth.make_auth_header(
                core_api_auth.ORIGIN_CONSUMER,
                username='admin', password_hash=self._admin_password_hash
            )
        }

        if timeout is None:
            timeout = settings.slaves.timeout

        request = HTTPRequest(
            url,
            method,
            headers=headers,
            body=body_str,
            connect_timeout=timeout,
            request_timeout=timeout
        )

        self.debug('calling API function %s %s', method, path)

        try:
            response = await http_client.fetch(request, raise_error=False)

        except Exception as e:
            # We need to catch exceptions here even though raise_error is False, because it only affects HTTP errors
            response = types.SimpleNamespace(error=e, code=599)

        try:
            response_body = core_responses.parse(response)

        except core_responses.Error as e:
            e = self.intercept_error(e)

            msg = f'api call {method} {path} on {self} failed: {e} (body={body_str or ""})'

            if ((retry_counter is not None) and (retry_counter < settings.slaves.retry_count) and
                (ref is not self._last_api_call_ref) and self._enabled):

                msg += f', retrying in {settings.slaves.retry_interval} seconds'
                self.error(msg)

                await asyncio.sleep(settings.slaves.retry_interval)

                return await self.api_call(method, path, body, timeout, retry_counter + 1)

            else:
                self.error(msg)
                raise e

        else:
            self.debug('api call %s %s succeeded', method, path)

            self.update_last_sync()
            await self.intercept_response(method, path, body, response_body)

            return response_body

    def _start_listening(self) -> None:
        if self._listen_session_id:
            self.warning('listening client already active')

            return

        h = hashlib.sha1(str(int(time.time() * 1000) + random.randint(0, 10000)).encode()).hexdigest()[:8]
        self._listen_session_id = f'{core_device_attrs.name.lower()}-{h}'

        self.debug('starting listening mechanism (%s)', self._listen_session_id)

        self._listen_task = asyncio.create_task(self._listen_loop())

    def _stop_listening(self) -> None:
        if not self._listen_session_id:
            self.warning('listening client not active')

            return

        self.debug('stopping listening mechanism (%s)', self._listen_session_id)

        self._listen_session_id = None
        self._listen_task.cancel()

    def _start_polling(self) -> None:
        if self._poll_started:
            self.warning('polling already active')

            return

        self._poll_started = True

        self.debug('starting polling mechanism')

        self._poll_task = asyncio.create_task(self._poll_loop())

    def _stop_polling(self) -> None:
        if not self._poll_started:
            self.warning('polling not active')

            return

        self.debug('stopping polling mechanism')

        self._poll_started = False
        self._poll_task.cancel()

    def _start_fwupdate_polling(self) -> None:
        if self._fwupdate_poll_task:
            self.warning('fwupdate polling already active')

            return

        self.debug('starting fwupdate polling')

        self._fwupdate_poll_task = asyncio.create_task(self._fwupdate_poll_loop())

    def _stop_fwupdate_polling(self) -> None:
        if not self._fwupdate_poll_task:
            self.warning('fwupdate polling not active')

            return

        self.debug('stopping fwupdate polling')

        self._fwupdate_poll_task.cancel()

    async def _add_port(self, attrs: Attributes) -> core_ports.BasePort:
        self.debug('adding port %s', attrs['id'])

        port = await core_ports.load_one(SlavePort, {
            'slave': self,
            'attrs': attrs
        })

        return port

    async def fetch_and_update_device(self) -> None:
        self.debug('fetching device attributes')

        just_added = self._name is None

        # Fetch remote attributes
        try:
            attrs = await self.api_call('GET', '/device', retry_counter=settings.slaves.retry_count)

        except Exception as e:
            self.error('failed to fetch device attributes: %s', e)
            raise

        name = attrs.get('name')
        if not name:
            self.error('invalid device')
            raise exceptions.InvalidDevice()

        await self.update_cached_attrs(attrs)

        if just_added and (name in _slaves_by_name or core_device_attrs.name == name):
            self.error('device already exists')
            raise exceptions.DeviceAlreadyExists(name)

    async def fetch_and_update_ports(self) -> None:
        self.debug('fetching ports')
        try:
            port_attrs = await self.api_call('GET', '/ports')

        except Exception as e:
            self.error('failed to fetch ports: %s', e)

            raise

        # At this point we have all remote information we need about ports

        local_ports = self._get_local_ports()
        local_ports_by_id = dict((p.get_remote_id(), p) for p in local_ports)

        attrs_by_id = dict((p.get('id'), p) for p in port_attrs)

        # Update existing ports
        for port_id, attrs in attrs_by_id.items():
            port = local_ports_by_id.get(port_id)
            if not port:
                continue

            await self._handle_port_update(**attrs)

        # Added ports
        for port_id, attrs in attrs_by_id.items():
            if port_id in local_ports_by_id:
                continue

            self.debug('port %s present remotely but not locally', port_id)
            await self._add_port(attrs)

        # Removed ports
        for port_id, port in local_ports_by_id.items():
            if port_id in attrs_by_id:
                continue

            self.debug('port %s present locally but not remotely', port_id)
            await port.remove(persisted_data=False)

        await self._save_ports()

    def _get_local_ports(self) -> List[SlavePort]:
        return [
            port for port in core_ports.all_ports()
            if port.get_id().startswith(f'{self._name}.') and isinstance(port, SlavePort)
        ]

    async def _listen_loop(self) -> None:
        # The initial listen API call is used to determine the reachability (the online status) of a slave
        keep_alive = 1

        # Used to drop orphaned listen responses (belonging to requests made before a session id update)
        requested_session_id = self._listen_session_id

        while True:
            try:
                if not self._listen_session_id:
                    break

                if self not in _slaves_by_name.values():
                    self.error('exiting listen loop for dangling slave device')
                    break

                url = self.get_url(f'/listen?timeout={keep_alive}&session_id={self._listen_session_id}')
                headers = {
                    'Content-Type': json_utils.JSON_CONTENT_TYPE,
                    'Authorization': core_api_auth.make_auth_header(
                        core_api_auth.ORIGIN_CONSUMER,
                        username='admin',
                        password_hash=self._admin_password_hash
                    )
                }

                http_client = AsyncHTTPClient()
                request = HTTPRequest(
                    url,
                    'GET',
                    headers=headers,
                    connect_timeout=settings.slaves.timeout,
                    request_timeout=settings.slaves.timeout + settings.slaves.keepalive
                )

                self.debug('calling API function GET /listen')

                try:
                    response = await http_client.fetch(request, raise_error=False)

                except Exception as e:
                    # We need to catch exceptions here even though raise_error is False, because it only affects HTTP
                    # errors
                    response = types.SimpleNamespace(error=e, code=599)

                # Ignore response to older or mismatching listen requests
                if self._listen_session_id != requested_session_id:
                    self.debug('ignoring listen response to older session (%s)', requested_session_id)

                    break

                if not self._listen_session_id:
                    break

                try:
                    events = core_responses.parse(response)

                except core_responses.Error as e:
                    self.error(
                        'api call GET /listen failed: %s, retrying in %s seconds',
                        e,
                        settings.slaves.retry_interval
                    )

                    if self._online:
                        self._online = False
                        await self._handle_offline()

                    await asyncio.sleep(settings.slaves.retry_interval)

                    # Fast keep-alive
                    keep_alive = 1

                else:
                    self.debug('api call GET /listen succeeded')

                    self.update_last_sync()

                    # Switch to normal keep-alive
                    keep_alive = settings.slaves.keepalive
                    needs_save_ports = False

                    for event in events:
                        try:
                            await self.handle_event(event)
                            if event['type'] in ('port-add', 'port-remove', 'port-update'):
                                needs_save_ports = True

                        except exceptions.DeviceRenamed:
                            self.debug('ignoring device renamed exception')
                            break

                        except Exception:
                            # Ignoring any error from handling an event is the best thing that we can do here, to ensure
                            # that we keep handling remaining events
                            pass

                    # _handle_event() indirectly stopped listening or removed this slave; this happens when the slave
                    # device is renamed
                    if self not in _slaves_by_name.values() or not self._listen_session_id:
                        break

                    if not self._online:
                        self._online = True
                        await self._handle_online()

                        if not self._online and self._listen_session_id:
                            self.warning(
                                'device did not successfully go online, retrying in %s seconds',
                                settings.slaves.retry_interval
                            )

                            await asyncio.sleep(settings.slaves.retry_interval)

                            # Fast keep-alive
                            keep_alive = 1

                    else:  # Still online
                        if needs_save_ports:
                            await self._save_ports()

            except asyncio.CancelledError:
                self.debug('listen task cancelled')
                break

    async def _poll_loop(self) -> None:
        interval = 0  # Never wait when start polling

        while True:
            try:
                await asyncio.sleep(interval)
                interval = await self._poll_once()

                if not interval:
                    break

            except asyncio.CancelledError:
                self.debug('poll task cancelled')
                break

    async def _poll_once(self) -> int:
        # We have to use try ... except blocks quite aggressively here, because we do not want any error that may occur
        # to stop our poll loop

        if not self._poll_started:
            return 0

        if self not in _slaves_by_name.values():
            self.error('exiting polling loop for dangling slave device')
            return 0

        self.debug('polling device')

        try:
            attrs = await self.api_call('GET', '/device')

        except Exception as e:
            self.error('failed to poll device: %s', e)

            if self._online:
                self._online = False
                await self._handle_offline()

            return settings.slaves.retry_interval

        added_names = [n for n in attrs if n not in self._cached_attrs]
        removed_names = [n for n in self._cached_attrs if n not in attrs]
        changed_names = [
            n for n in self._cached_attrs
            if (n in attrs) and (attrs[n] != self._cached_attrs[n])
        ]

        for name in added_names:
            self.debug('detected new attribute: %s = %s', name, json_utils.dumps(attrs[name]))

        for name in removed_names:
            self.debug('detected removed attribute: %s', name)

        for name in changed_names:
            if name == 'definitions':
                self.debug('detected attribute definitions change')

            else:
                self.debug(
                    'detected attribute change: %s = %s -> %s',
                    name,
                    json_utils.dumps(self._cached_attrs[name]),
                    json_utils.dumps(attrs[name])
                )

        if removed_names or added_names or changed_names:
            try:
                await self._handle_device_update(**attrs)

            except exceptions.DeviceAlreadyExists:
                # When DeviceAlreadyExists is raised, we expect the slave to be disabled; therefore we exit the polling
                # loop right away
                return 0

            except exceptions.DeviceRenamed:
                # When DeviceRenamed is raised, we have to break the polling loop right away, because another slave
                # device has been added in place of this one
                return 0

            except Exception as e:
                self.error('failed to update device: %s', e)

        # If we reach this point, we can consider the slave device online

        if not self._online:
            self._online = True
            await self._handle_online()

            if not self._online:
                self.warning(
                    'device did not successfully go online, retrying in %s seconds',
                    settings.slaves.retry_interval
                )

                return settings.slaves.retry_interval

        # Don't poll ports unless device is ready
        if not self._ready:
            return self._poll_interval

        # Polling could have been stopped in the meantime
        if not self._poll_started:
            return 0

        self.debug('polling ports')

        try:
            ports = await self.api_call('GET', '/ports')

        except Exception as e:
            self.error('failed to poll ports: %s', e)

            if self._online:
                self._online = False
                await self._handle_offline()

            return settings.slaves.retry_interval

        needs_save_ports = False

        local_ports = self._get_local_ports()
        local_ports_by_id = {p.get_remote_id(): p for p in local_ports}

        # Port values are also present among attrs when requesting GET /ports; we need to separate them
        attrs_by_id = {p['id']: p for p in ports}
        values_by_id = {_id: attrs.pop('value', None) for _id, attrs in attrs_by_id.items()}

        added_ids = [i for i in attrs_by_id if i not in local_ports_by_id]
        removed_ids = [i for i in local_ports_by_id if i not in attrs_by_id]

        for _id in added_ids:
            self.debug('detected new port: %s', _id)
            try:
                await self._handle_port_add(**attrs_by_id[_id])
                needs_save_ports = True

            except Exception as e:
                self.error('failed to add polled port %s: %s', _id, e)

        for _id in removed_ids:
            self.debug('detected port removal: %s', _id)

            try:
                await self._handle_port_remove(_id)
                needs_save_ports = True

            except Exception as e:
                self.error('failed to remove polled port %s: %s', _id, e)

        for _id, local_port in local_ports_by_id.items():
            attrs = attrs_by_id.get(_id)
            if not attrs:
                continue

            local_attrs = local_port.get_cached_attrs()

            added_names = [n for n in attrs if n not in local_attrs]
            removed_names = [n for n in local_attrs if n not in attrs]
            changed_names = [n for n in local_attrs if n in attrs and attrs[n] != local_attrs[n]]

            for name in added_names:
                local_port.debug('detected new attribute: %s = %s', name, json_utils.dumps(attrs[name]))

            for name in removed_names:
                local_port.debug('detected removed attribute: %s', name)

            for name in changed_names:
                if name == 'definitions':
                    local_port.debug('detected attribute definitions change')

                else:
                    local_port.debug(
                        'detected attribute change: %s = %s -> %s',
                        name,
                        json_utils.dumps(local_attrs[name]),
                        json_utils.dumps(attrs[name])
                    )

            if removed_names or added_names or changed_names:
                try:
                    await self._handle_port_update(**attrs)
                    needs_save_ports = True

                except Exception as e:
                    self.error('failed to update polled port %s: %s', _id, e)

            old_value = local_port.get_cached_value()
            new_value = values_by_id.get(_id)
            if old_value != new_value:
                try:
                    await self._handle_value_change(_id, new_value)

                except Exception as e:
                    self.error('failed to update polled port %s value: %s', _id, e)

        if needs_save_ports:
            try:
                await self._save_ports()

            except Exception as e:
                self.error('failed to save polled ports: %s', e)

        return self._poll_interval

    async def _fwupdate_poll_loop(self) -> None:
        counter = _FWUPDATE_POLL_TIMEOUT / _FWUPDATE_POLL_INTERVAL

        while True:
            try:
                await asyncio.sleep(_FWUPDATE_POLL_INTERVAL)
                if not counter:
                    self.error('timeout waiting for device to come up after firmware update')
                    break  # We give up waiting for device to come up

                # Requesting GET /firmware will call the intercept_request() method and will cancel the loop when done
                try:
                    await self.api_call('GET', '/firmware')

                except Exception:
                    pass

                counter -= 1

            except asyncio.CancelledError:
                self.debug('fwupdate poll loop cancelled')
                break

        # Clear task reference when exiting the task loop
        self._fwupdate_poll_task = None

    async def handle_event(self, event: GenericJSONDict) -> None:
        event_name = re.sub(r'[^\w]', '_', event['type'])
        method_name = f'_handle_{event_name}'
        method = getattr(self, method_name, None)
        if not method:
            self.warning('ignoring event of type %s', event['type'])
            return

        self.debug('handling event of type %s', event['type'])
        try:
            await method(**event.get('params', {}))

        except exceptions.DeviceRenamed:
            # Treat DeviceRenamed as an expected exception, do not log anything but forward it
            raise

        except Exception as e:
            self.error('handling event of type %s failed: %s', event['type'], e)
            raise

    async def _handle_value_change(self, id: str, value: NullablePortValue) -> None:
        local_id = f'{self._name}.{id}'
        port = core_ports.get(local_id)
        if not port or not isinstance(port, SlavePort):
            raise exceptions.PortNotFound(self, local_id)

        if port.get_provisioning_value() is not None:
            self.debug('ignoring value-change event due to pending provisioning value')
            return

        self.debug(
            'value of %s changed remotely from %s to %s',
            port,
            json_utils.dumps(port.get_value()),
            json_utils.dumps(value)
        )

        port.set_cached_value(value)
        port.update_last_sync()
        await port.save()

        await core_main.update()

    async def _handle_port_update(self, **attrs: Attribute) -> None:
        local_id = f'{self._name}.{attrs.get("id")}'
        port = core_ports.get(local_id)
        if not port or not isinstance(port, SlavePort):
            raise exceptions.PortNotFound(self, local_id)

        provisioning_attrs = port.get_provisioning_attrs()

        for name, value in attrs.items():
            if name in ('tag', 'expression'):
                continue

            if name in provisioning_attrs:
                self.debug('ignoring port-update attribute %s due to pending provisioning attribute', name)
                continue

            old_value = port.get_cached_attr(name)
            if old_value is not None and value != old_value:
                self.debug(
                    '%s.%s changed remotely: %s -> %s',
                    port,
                    name,
                    json_utils.dumps(old_value),
                    json_utils.dumps(value)
                )

                await port.handle_attr_change(name, value)

        port.update_cached_attrs(attrs)
        await port.update_enabled()

        if 'value' in attrs:  # Value has also been updated
            port.update_last_sync()

        await port.save()
        await port.trigger_update()

    async def _handle_port_add(self, **attrs: Attribute) -> None:
        local_id = f'{self._name}.{attrs.get("id")}'
        self.debug('port %s added remotely', local_id)

        await self._add_port(attrs)

    async def _handle_port_remove(self, id: str) -> None:
        local_id = f'{self._name}.{id}'
        port = core_ports.get(local_id)
        if not port or not isinstance(port, SlavePort):
            raise exceptions.PortNotFound(self, local_id)

        await port.remove()

    async def _handle_device_update(self, **attrs: Attribute) -> None:
        provisioning_attrs = self.get_provisioning_attrs()

        # We're working on a copy, just to be sure we can safely pop stuff from it
        attrs = dict(attrs)

        for name in attrs:
            if name in provisioning_attrs:
                self.debug('ignoring device-update attribute %s due to pending provisioning attribute', name)
                attrs.pop(name)

        await self.update_cached_attrs(attrs)
        await self.trigger_update()
        self.save()

    async def _handle_full_update(self) -> None:
        await self.fetch_and_update_device()
        await self.fetch_and_update_ports()
        await self.trigger_update()
        self.save()

    async def _handle_offline(self) -> None:
        self.debug('device is offline')

        await self.trigger_update()

        # Trigger a port-update so that online attribute is pushed to consumers
        for port in self._get_local_ports():
            if port.is_enabled():
                await port.trigger_update()

    async def _handle_online(self) -> None:
        self.debug('device is online')

        # Now that the device is back online, we can apply any pending provisioning data
        await self.apply_provisioning()

        if not self._poll_interval:
            # Synchronize device attributes as well as ports, but only if polling is disabled (since it does the same
            # thing itself)

            try:
                await self.fetch_and_update_device()
                await self.fetch_and_update_ports()

            except Exception as e:
                self.error('failed to fetch device attributes and ports: %s', e, exc_info=True)

                self._online = False
                await self._handle_offline()

                return

        await self.trigger_update()

        # Trigger a port-update so that online attribute is pushed to consumers
        for port in self._get_local_ports():
            if port.is_enabled():
                await port.trigger_update()

        if not self._ready:
            self.debug('device is ready')
            self._ready = True

        self.save()

    def get_provisioning_attrs(self) -> Attributes:
        provisioning = {}
        for name in self._provisioning_attrs:
            value = self._cached_attrs.get(name)
            if value is not None:
                provisioning[name] = value

        return provisioning

    def get_provisioning_webhooks(self) -> GenericJSONDict:
        provisioning = {}
        for name in self._provisioning_webhooks:
            value = self._cached_webhooks.get(name)
            if value is not None:
                provisioning[name] = value

        return provisioning

    def get_provisioning_reverse(self) -> GenericJSONDict:
        provisioning = {}
        for name in self._provisioning_reverse:
            value = self._cached_reverse.get(name)
            if value is not None:
                provisioning[name] = value

        return provisioning

    def clear_provisioning_attrs(self) -> None:
        self._provisioning_attrs = set()

    def clear_provisioning_webhooks(self) -> None:
        self._provisioning_webhooks = set()

    def clear_provisioning_reverse(self) -> None:
        self._provisioning_reverse = set()

    async def apply_provisioning(self) -> None:
        provisioned = False

        has_webhooks = 'webhooks' in self._cached_attrs.get('flags', [])
        has_reverse = 'reverse' in self._cached_attrs.get('flags', [])

        # Device attributes provisioning
        attrs = self.get_provisioning_attrs()
        if attrs:
            self.debug('provisioning device attributes: %s', ', '.join(attrs.keys()))

            try:
                await self.api_call('PATCH', '/device', attrs, timeout=settings.slaves.long_timeout)

            except Exception as e:
                self.error('failed to provision device attributes: %s', e)

            self.clear_provisioning_attrs()

            provisioned = True

        # Webhooks params provisioning
        params = self.get_provisioning_webhooks()
        webhooks_provisioned = False
        if params and has_webhooks:
            self.debug('provisioning webhooks params: %s', ', '.join(params.keys()))

            try:
                await self.api_call('PATCH', '/webhooks', params)

            except Exception as e:
                self.error('failed to provision webhooks params: %s', e)

            self.clear_provisioning_webhooks()

            provisioned = True
            webhooks_provisioned = True

        # Reverse params provisioning
        params = self.get_provisioning_reverse()
        reverse_provisioned = False
        if params and has_reverse:
            self.debug('provisioning reverse params: %s', ', '.join(params.keys()))

            try:
                await self.api_call('PATCH', '/reverse', params)

            except Exception as e:
                self.error('failed to provision reverse params: %s', e)

            self.clear_provisioning_reverse()

            provisioned = True
            reverse_provisioned = True

        # If we had some provisioning to do, we need to save the new device state (with cleared provisioning)
        if provisioned:
            self.save()

        # Ports provisioning
        for port in self._get_local_ports():
            assert isinstance(port, SlavePort)

            provisioned = False

            # Port attributes provisioning
            attrs = port.get_provisioning_attrs()
            if attrs:
                self.debug('provisioning %s attributes: %s', port, ', '.join(attrs.keys()))

                try:
                    await self.api_call(
                        'PATCH', f'/ports/{port.get_remote_id()}',
                        attrs,
                        timeout=settings.slaves.long_timeout
                    )

                except Exception as e:
                    self.error('failed to provision %s attributes: %s', port, e)

                provisioned = True

            # Port values provisioning
            value = port.get_provisioning_value()
            if value is not None:
                self.debug('provisioning %s value', port)

                try:
                    await self.api_call(
                        'PATCH',
                        f'/ports/{port.get_remote_id()}/value',
                        timeout=settings.slaves.long_timeout
                    )

                except Exception as e:
                    self.error('failed to provision %s value: %s', port, e)

                provisioned = True

            port.clear_provisioning()

            # If we had some provisioning to do, we need to save the new port state (with cleared provisioning)
            if provisioned:
                await port.save()

        # If no webhooks params marked for provisioning, query the current params from device
        webhooks_queried = False
        if not webhooks_provisioned and has_webhooks:
            self.debug('querying current webhooks params')

            try:
                self._cached_webhooks = await self.api_call('GET', '/webhooks')
                webhooks_queried = True

            except Exception as e:
                self.error('failed to query current webhooks params: %s', e)

        # If no reverse params marked for provisioning, query the current params from device
        reverse_queried = False
        if not reverse_provisioned and has_reverse:
            self.debug('querying current reverse params')

            try:
                self._cached_reverse = await self.api_call('GET', '/reverse')
                reverse_queried = True

            except Exception as e:
                self.error('failed to query current reverse params: %s', e)

        if webhooks_queried or reverse_queried:
            self.save()

    def schedule_provisioning_and_update(self, delay: float) -> None:
        if self._provisioning_timeout_task:
            self._provisioning_timeout_task.cancel()

        future = asyncio_utils.await_later(delay, self._provision_and_update)
        self._provisioning_timeout_task = asyncio.create_task(future)

    async def _provision_and_update(self) -> None:
        self.debug('starting provisioning & update procedure')
        self._provisioning_timeout_task = None

        await self.apply_provisioning()
        await self.fetch_and_update_device()
        await self.fetch_and_update_ports()

    async def intercept_request(
        self,
        method: str,
        path: str,
        params: Any,
        request: core_api.APIRequest
    ) -> Tuple[bool, Any]:

        # Intercept API calls to device attributes, webhooks and reverse parameters, for devices that are offline
        if self._online:
            return False, None

        if method == 'GET':
            if path == '/device':
                # In theory, cached attributes should always be available, while device is online
                if self._cached_attrs:
                    return True, self._cached_attrs

            elif path == '/webhooks':
                # This is how we test that we have all required webhooks parameters in cache
                if len(set(core_api_schema.PATCH_WEBHOOKS['properties'].keys()) - set(self._cached_webhooks)) == 0:
                    return True, self._cached_webhooks

            elif path == '/reverse':
                # This is how we test that we have all required reverse parameters in cache
                if len(set(core_api_schema.PATCH_REVERSE['properties'].keys()) - set(self._cached_reverse)) == 0:
                    return True, self._cached_reverse

        elif method == 'PATCH':
            if path == '/device':
                for name, value in params.items():
                    self.debug('marking attribute %s for provisioning', name)
                    self._provisioning_attrs.add(name)
                    self._cached_attrs[name] = value

                # Inform clients about the provisioning field change
                await self.trigger_update()

                self.save()

                return True, None

            elif path == '/webhooks':
                for name, value in params.items():
                    self.debug('marking webhooks param %s for provisioning', name)
                    self._provisioning_webhooks.add(name)
                    self._cached_webhooks[name] = value

                self.save()

                return True, None

            elif path == '/reverse':
                for name, value in params.items():
                    self.debug('marking reverse param %s for provisioning', name)
                    self._provisioning_reverse.add(name)
                    self._cached_reverse[name] = value

                self.save()

                return True, None

        # By default, requests are not intercepted
        return False, None

    async def intercept_response(self, method: str, path: str, request_body: Any, response_body: Any) -> None:
        if path.endswith('/'):
            path = path[:-1]

        if path == '/device':
            if method == 'PATCH':
                # Intercept this API call to detect admin password changes
                new_admin_password = (request_body or {}).get('admin_password')
                if new_admin_password is not None:
                    self.debug('updating admin password')
                    self.set_admin_password(new_admin_password)
                    self.save()

                # Detect local name changes
                new_name = request_body and request_body.get('name')
                if new_name and new_name != self._name:
                    try:
                        await self.update_cached_attrs({'name': new_name}, partial=True)

                    except exceptions.DeviceRenamed:
                        pass

            elif method == 'GET':
                # Intercept this API call so that we can update locally cached attributes whose values change often and
                # therefore do not trigger a device-update event
                attrs = {n: response_body[n] for n in _NO_EVENT_DEVICE_ATTRS if n in response_body}
                await self.update_cached_attrs(attrs, partial=True)

        elif path == '/firmware':
            if method == 'PATCH' and not self._fwupdate_poll_task:
                # When performing firmware update, take device offline and stop listening/polling mechanisms

                self.debug('firmware update process active')
                await self.disable()
                await self.trigger_update()
                self._start_fwupdate_polling()

            elif method == 'GET' and self._fwupdate_poll_task:
                if response_body.get('status') == 'idle':  # Firmware update process not running
                    self.debug('firmware update process ended')
                    await self.enable()
                    self._stop_fwupdate_polling()

        elif path == '/reset':
            if method == 'POST' and request_body.get('factory'):
                # When performing factory reset, disable device

                self.debug('device has been reset to factory defaults')
                await self.disable()
                await self.trigger_update()

    def intercept_error(self, error: Exception) -> Exception:
        if isinstance(error, core_responses.HTTPError):
            # Slave expression attribute is known as "device_expression" on Master; we must adapt the corresponding
            # error here by prepending a(nother) "device_"
            if error.code == 'invalid-field':
                field = error.params.get('field', '')
                m = _INVALID_EXPRESSION_FIELD_RE.match(field)
                if m:
                    params = dict(error.params)
                    params['field'] = 'device_' + m.group(1)
                    return core_responses.HTTPError(error.status, error.code, **params)

        return error


def get(name: str) -> Optional[Slave]:
    return _slaves_by_name.get(name)


async def add(
    scheme: str,
    host: str,
    port: int,
    path: str,
    poll_interval: int = 0,
    listen_enabled: Optional[bool] = None,
    admin_password: Optional[str] = None,
    admin_password_hash: Optional[str] = None
) -> Slave:

    slave = Slave(
        name=None,
        scheme=scheme,
        host=host,
        port=port,
        path=path,
        poll_interval=0,  # Will be set later
        listen_enabled=False,  # Will be set later
        admin_password=admin_password,
        admin_password_hash=admin_password_hash
    )

    slave.debug('starting add procedure')

    await slave.fetch_and_update_device()
    name = slave.get_name()

    # Check that we have required listen support
    if (listen_enabled is True) and 'listen' not in slave.get_cached_attr('flags'):
        slave.error('no listen support')
        raise exceptions.NoListenSupport(name)

    # If no listen and no polling specified, attempt to automatically detect and enable supported method
    if (listen_enabled is None) and (poll_interval == 0):
        if 'listen' in slave.get_cached_attr('flags'):
            slave.debug('listen support detected, auto-enabling listening')
            listen_enabled = True

        else:
            slave.debug('listen support not detected, auto-enabling polling')
            poll_interval = _DEFAULT_POLL_INTERVAL

    if listen_enabled:
        slave.enable_listen()

    elif poll_interval:
        slave.set_poll_interval(poll_interval)

    await slave.enable()
    await slave.trigger_add()
    slave.save()

    if not listen_enabled and not poll_interval:
        # Device is permanently offline, but we must know its ports; this would otherwise be called by
        # Slave._handle_online()
        await slave.fetch_and_update_ports()

    _slaves_by_name[name] = slave

    return slave


async def remove(slave: Slave) -> None:
    _slaves_by_name.pop(slave.get_name(), None)
    await slave.remove()


def get_all() -> Iterable[Slave]:
    return _slaves_by_name.values()


def _slave_ready(slave: Slave) -> bool:
    return slave.is_enabled() and not slave.is_permanently_offline()


def ready() -> bool:
    # Allow 110% of slaves.timeout setting for all slaves to get ready; after that time has passed, slaves are as ready
    # as they can be
    if time.time() - _load_time > int(settings.slaves.timeout * 1.1):
        return True

    slaves = (s for s in _slaves_by_name.values() if s.is_enabled() and not s.is_permanently_offline())

    return all(s.is_ready() for s in slaves)


async def load() -> None:
    global _load_time

    _load_time = time.time()

    for entry in persist.query('slaves'):
        try:
            entry['name'] = entry.pop('id')

        except KeyError:
            logger.error('skipping entry with missing "id" key in persisted data')
            continue

        try:
            slave = Slave(**entry)

        except Exception as e:
            logger.error('failed to load slave %s: %s', entry['name'], e, exc_info=True)
            continue

        _slaves_by_name[slave.get_name()] = slave

        if entry['enabled']:
            logger.debug('loaded %s', slave)
            await slave.enable()

        else:
            logger.debug('loaded %s (disabled)', slave)

        await slave.trigger_add()


async def cleanup() -> None:
    tasks = [slave.cleanup() for slave in _slaves_by_name.values()]
    if tasks:
        await asyncio.wait(tasks)
