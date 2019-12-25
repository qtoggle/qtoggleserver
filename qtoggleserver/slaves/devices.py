
import asyncio
import hashlib
import logging
import random
import re
import time
import types

from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from qtoggleserver import persist
from qtoggleserver import utils
from qtoggleserver.conf import settings
from qtoggleserver.core import events as core_events
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core import responses as core_responses
from qtoggleserver.core import sessions as core_sessions
from qtoggleserver.core.api import auth as core_api_auth
from qtoggleserver.core.api import schema as core_api_schema
from qtoggleserver.core.device import attrs as core_device_attrs
from qtoggleserver.utils import http as http_utils
from qtoggleserver.utils import json as json_utils

from . import exceptions
from .ports import SlavePort


_INVALID_EXPRESSION_RE = re.compile(r'^invalid field: ((device_)*expression)$')
_FWUPDATE_POLL_INTERVAL = 30
_FWUPDATE_POLL_TIMEOUT = 300
_NO_EVENT_DEVICE_ATTRS = ['uptime', 'date']


_slaves = {}  # indexed by name
_load_time = 0

logger = logging.getLogger(__name__)


class Slave(utils.LoggableMixin):
    def __init__(self, name, scheme, host, port, path, poll_interval=None, listen_enabled=True,
                 admin_password=None, admin_password_hash=None, last_sync=-1,
                 attrs=None, webhooks=None, reverse=None,
                 provisioning_attrs=None, provisioning_webhooks=None, provisioning_reverse=None,
                 **kwargs):

        # the enabled value comes with kwargs but is ignored,
        # as the slave will be explicitly enabled afterwards

        utils.LoggableMixin.__init__(self, name, logger)
        if not name:
            self.set_logger_name('{}:{}'.format(host, port))

        self._name = name
        self._scheme = scheme
        self._host = host
        self._port = port
        self._path = path
        self._poll_interval = poll_interval
        self._listen_enabled = listen_enabled

        if admin_password is not None:
            self._admin_password_hash = hashlib.sha256(admin_password.encode()).hexdigest()

        else:
            self._admin_password_hash = admin_password_hash

        # indicates the online status
        self._enabled = False

        # indicates the online status
        self._online = False

        # used to tell initial offline -> online transition from subsequent transitions
        self._initial_online = True

        # timestamp when we last heard from this device
        self._last_sync = last_sync

        # indicates whether all data required for this slave is present locally
        self._ready = False

        # indicates the listening session id, or None if no listen client is active
        self._listen_session_id = None
        self._listen_task = None

        # tells the polling mechanism status
        self._poll_started = False
        self._pool_task = None

        # attributes cache
        self._cached_attrs = attrs or {}

        # webhooks parameters cache
        self._cached_webhooks = webhooks or {}

        # reverse API calls cache
        self._cached_reverse = reverse or {}

        # names of attributes that have been changed
        # while device was offline and have to be provisioned later
        self._provisioning_attrs = set(provisioning_attrs or [])

        # webhooks params that have been changed
        # while device was offline and have to be provisioned later
        self._provisioning_webhooks = set(provisioning_webhooks or [])

        # reverse params that have been changed
        # while device was offline and have to be provisioned later
        self._provisioning_reverse = set(provisioning_reverse or [])

        # used to schedule provisioning + local update for permanently offline slaves
        self._provisioning_timeout_handle = None

        # an internal reference to the last made API call
        self._last_api_call_ref = None

        # cached url
        self._url = None

        # flag indicating that firmware update is in progress
        self._fwupdate_poll_started = False

    def __str__(self):
        if self._name:
            return 'slave {} at {}'.format(self._name, self.get_url())

        else:
            return 'slave at {}'.format(self.get_url())

    def __eq__(self, s):
        return (self._scheme == s.get_scheme() and self._host == s.get_host() and
                self._port == s.get_port() and self._path == s.get_path())

    def get_url(self, path=None):
        if path:
            url = self.get_url()
            while url.endswith('/'):
                url = url[:-1]

            return url + path

        if not self._url:
            if self._scheme == 'http' and self._port == 80 or self._scheme == 'https' and self._port == 443:
                self._url = '{}://{}{}'.format(self._scheme, self._host, self._path)

            else:
                self._url = '{}://{}:{}{}'.format(self._scheme, self._host, self._port, self._path)

        return self._url

    def get_cached_attr(self, name):
        return self._cached_attrs.get(name)

    def get_cached_attrs(self):
        return self._cached_attrs

    def update_cached_attrs(self, attrs, partial=False):
        # if the name has changed remove the device and re-add the device from scratch

        if attrs.get('name'):
            name = attrs['name']
            if name != self._name:
                if self._name is not None:
                    self.debug('detected name change to %s', name)

                    # disable device before removing it
                    if self.is_enabled():
                        self.disable()

                        # we have to trigger an update event here,
                        # to inform consumers about disabling
                        self.trigger_update()

                    # check for duplicate name
                    if name in _slaves or core_device_attrs.name == name:
                        logger.error('a slave with name %s already exists', name)
                        raise exceptions.DeviceAlreadyExists(name)

                    # rename associated ports persisted data
                    try:
                        self._rename_ports_persisted_data(name)

                    except Exception as e:
                        logger.error('renaming ports persisted data failed: %s', e, exc_info=True)

                    # actually remove the slave
                    remove(self)

                    # add the slave back
                    future = add(self._scheme, self._host, self._port, self._path, self._poll_interval,
                                 self._listen_enabled, admin_password_hash=self._admin_password_hash)

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

    def get_name(self):
        return self._name

    def get_display_name(self):
        return self._cached_attrs.get('display_name') or self._name

    def get_scheme(self):
        return self._scheme

    def get_host(self):
        return self._host

    def get_port(self):
        return self._port

    def get_path(self):
        return self._path

    def get_admin_password_hash(self):
        return self._admin_password_hash

    def set_admin_password(self, admin_password):
        self._admin_password_hash = hashlib.sha256(admin_password.encode()).hexdigest()

    def is_ready(self):
        return self._ready

    def is_online(self):
        return self._online

    def update_last_sync(self):
        self._last_sync = int(time.time())

    def is_enabled(self):
        return self._enabled

    def enable(self):
        if self._enabled:
            return

        self.debug('enabling device')
        self._enabled = True
        self._ready = False
        self._online = False

        # start polling/listening mechanism
        if self._poll_interval:
            self._start_polling()

        elif self._listen_enabled:
            self._start_listening()

        # we need to load ports asynchronously, because we expect callers of enable()
        # to generate slave-device-update events, and we want any port-related events
        # generated by _load_ports() to come after
        if self._name:
            asyncio.create_task(self._load_ports())

    def disable(self):
        if not self._enabled:
            return

        self.debug('disabling device')
        self._enabled = False
        self._ready = False

        # stop listening
        if self._listen_session_id:
            self._stop_listening()

        # stop polling
        if self._poll_started:
            self._stop_polling()

        # removing ports
        self.debug('removing ports')
        for port in self._get_local_ports():
            port.remove(persisted_data=False)

        # marking offline
        self._online = False

    def set_poll_interval(self, poll_interval):
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
                # take offline
                self._online = False
                asyncio.create_task(self._handle_offline())

    def get_poll_interval(self):
        return self._poll_interval

    def enable_listen(self):
        if self._listen_enabled:
            return  # already enabled

        self.debug('listening enabled')

        self._listen_enabled = True
        if not self._listen_session_id and self._enabled:
            self._start_listening()

    def disable_listen(self):
        if not self._listen_enabled:
            return  # not enabled

        self.debug('listening disabled')

        self._listen_enabled = False
        if self._listen_session_id:
            self._stop_listening()

        if self._online:
            # take offline
            self._online = False
            asyncio.create_task(self._handle_offline())

    def is_listen_enabled(self):
        return self._listen_enabled

    def is_permanently_offline(self):
        return self._poll_interval == 0 and not self._listen_enabled

    def to_json(self):
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

    def prepare_for_save(self):
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

    def save(self):
        self.debug('saving device')
        persist.replace('slaves', self._name, self.prepare_for_save())

    async def cleanup(self):
        self.debug('cleaning up')

        # stop listening
        if self._listen_session_id:
            self._stop_listening()
            self._listen_task.cancel()
            await self._listen_task
            self.debug('listening stopped')

        # stop polling
        if self._poll_started:
            self._stop_polling()
            await self._pool_task
            self.debug('polling mechanism stopped')

    async def _load_ports(self):
        self.debug('loading persisted ports')
        port_data_list = persist.query(SlavePort.PERSIST_COLLECTION, fields=['id'])
        my_port_ids = [d['id'][len(self._name) + 1:] for d in port_data_list
                       if d['id'].startswith(self._name + '.')]

        for _id in my_port_ids:
            await self._add_port(attrs={'id': _id})

    async def _save_ports(self):

        self.debug('persisting ports')
        ports = self._get_local_ports()
        for port in ports:
            await port.save()

    def _rename_ports_persisted_data(self, new_name):
        port_data_list = persist.query(SlavePort.PERSIST_COLLECTION, fields=['id'])
        my_port_data_list = [d for d in port_data_list
                             if d['id'].startswith(self._name + '.')]

        # remove old records
        for d in my_port_data_list:
            persist.remove(SlavePort.PERSIST_COLLECTION, {'id': d['id']})

        # add new records
        for d in my_port_data_list:
            d['id'] = new_name + d['id'][len(self._name):]
            persist.insert(SlavePort.PERSIST_COLLECTION, d)

    def remove(self):
        self._enabled = False
        self._ready = False

        if self._listen_session_id:
            self._stop_listening()

        if self._poll_started:
            self._stop_polling()

        self.debug('removing ports')
        for port in self._get_local_ports():
            port.remove()

        self.debug('removing device')
        persist.remove('slaves', filt={'id': self._name})

        self.trigger_remove()

        return True

    def trigger_add(self):
        event = core_events.SlaveDeviceAdd(self)
        core_sessions.push(event)
        core_events.handle_event(event)

    def trigger_remove(self):
        event = core_events.SlaveDeviceRemove(self)
        core_sessions.push(event)
        core_events.handle_event(event)

    def trigger_update(self):
        event = core_events.SlaveDeviceUpdate(self)
        core_sessions.push(event)
        core_events.handle_event(event)

    async def api_call(self, method, path, body=None, retry_counter=0):
        if method == 'GET':
            body = None

        url = self.get_url(path)
        body_str = json_utils.dumps(body) if body is not None else None

        # a new API call cancels any pending retry
        ref = self._last_api_call_ref = {}

        http_client = AsyncHTTPClient()
        headers = {
            'Content-Type': http_utils.JSON_CONTENT_TYPE,
            'Authorization': core_api_auth.make_auth_header(core_api_auth.ORIGIN_CONSUMER,
                                                            username='admin', password_hash=self._admin_password_hash)
        }
        request = HTTPRequest(url, method, headers=headers, body=body_str,
                              connect_timeout=settings.slaves.timeout, request_timeout=settings.slaves.timeout)

        self.debug('calling api function %s %s', method, path)

        try:
            response = await http_client.fetch(request, raise_error=False)

        except Exception as e:
            # We need to catch exceptions here even though raise_error is False,
            # because it only affects HTTP errors
            response = types.SimpleNamespace(error=e, code=599)

        try:
            result = core_responses.parse(response)

        except core_responses.Error as e:
            e = self.intercept_error(e)

            msg = 'api call {} {} on {} failed: {} (body={})'.format(method, path, self, e, body_str or '')

            if (retry_counter is not None and retry_counter < settings.slaves.retry_count and
                self._enabled and ref is not self._last_api_call_ref):

                msg += ', retrying in {} seconds'.format(settings.slaves.retry_interval)
                self.error(msg)

                await asyncio.sleep(settings.slaves.retry_interval)

                return await self.api_call(method, path, body, retry_counter + 1)

            else:
                self.error(msg)
                raise e

        else:
            self.debug('api call %s %s succeeded', method, path)

            self.update_last_sync()
            self.intercept_response(method, path, body, result)

            return result

    def _start_listening(self):
        if self._listen_session_id:
            self.warning('listening client already active')

            return

        h = hashlib.sha1(str(int(time.time() * 1000) + random.randint(0, 10000)).encode()).hexdigest()[:8]
        self._listen_session_id = '{}-{}'.format(core_device_attrs.name.lower(), h)

        self.debug('starting listening mechanism (%s)', self._listen_session_id)

        self._listen_task = asyncio.create_task(self._listen_loop())

    def _stop_listening(self):
        if not self._listen_session_id:
            self.warning('listening client not active')

            return

        self.debug('stopping listening mechanism (%s)', self._listen_session_id)

        self._listen_session_id = None

    def _start_polling(self):
        if self._poll_started:
            self.warning('polling already active')

            return

        self._poll_started = True

        self.debug('starting polling mechanism')

        self._pool_task = asyncio.create_task(self._poll_loop())

    def _stop_polling(self):
        if not self._poll_started:
            self.warning('polling not active')

            return

        self.debug('stopping polling mechanism')

        self._poll_started = False

    def _start_fwupdate_polling(self):
        if self._fwupdate_poll_started:
            self.warning('fwupdate polling already active')

            return

        self._fwupdate_poll_started = True

        self.debug('starting fwupdate polling')

        asyncio.create_task(self._fwupdate_poll_loop())

    def _stop_fwupdate_polling(self):
        if not self._fwupdate_poll_started:
            self.warning('fwupdate polling not active')

            return

        self.debug('stopping fwupdate polling')

        self._fwupdate_poll_started = False

    async def _add_port(self, attrs):
        self.debug('adding port %s', attrs['id'])

        port = await core_ports.load_one(SlavePort, {
            'slave': self,
            'attrs': attrs
        })

        port.trigger_add()

    async def fetch_and_update_device(self):
        self.debug('fetching device attributes')

        just_added = self._name is None

        # fetch remote attributes
        try:
            attrs = await self.api_call('GET', '/device', retry_counter=settings.slaves.retry_count)

        except Exception as e:
            self.error('failed to fetch device attributes: %s', e)
            raise

        name = attrs.get('name')
        if not name:
            self.error('invalid device')
            raise exceptions.InvalidDevice()

        self.update_cached_attrs(attrs)

        if just_added and (name in _slaves or core_device_attrs.name == name):
            self.error('device already exists')
            raise exceptions.DeviceAlreadyExists(name)

    async def fetch_and_update_ports(self):
        self.debug('fetching ports')
        try:
            port_attrs = await self.api_call('GET', '/ports')

        except Exception as e:
            self.error('failed to fetch ports: %s', e)

            raise

        # at this point we have all remote information we need about ports

        local_ports = self._get_local_ports()
        local_ports_by_id = dict((p.get_remote_id(), p) for p in local_ports)

        attrs_by_id = dict((p.get('id'), p) for p in port_attrs)

        # update existing ports
        for port_id, attrs in attrs_by_id.items():
            port = local_ports_by_id.get(port_id)
            if not port:
                continue

            await self._handle_port_update(**attrs)

        # added ports
        for port_id, attrs in attrs_by_id.items():
            if port_id in local_ports_by_id:
                continue

            self.debug('port %s present remotely but not locally', port_id)
            await self._add_port(attrs)

        # removed ports
        for port_id, port in local_ports_by_id.items():
            if port_id in attrs_by_id:
                continue

            self.debug('port %s present locally but not remotely', port_id)
            port.remove()

        await self._save_ports()

    def _get_local_ports(self):
        return [port for port in core_ports.all_ports() if port.get_id().startswith(self._name + '.')]

    async def _listen_loop(self):
        # the initial listen API call is used to determine
        # the reachability (the online status) of a slave
        keep_alive = 1

        # used to drop orphaned listen responses
        # (belonging to requests made before a session id update)
        requested_session_id = self._listen_session_id

        while True:
            try:
                if not self._listen_session_id:
                    break

                if self not in _slaves.values():
                    self.error('exiting listen loop for dangling slave device')
                    break

                url = self.get_url('/listen?timeout={}&session_id={}'.format(keep_alive, self._listen_session_id))
                headers = {
                    'Content-Type': http_utils.JSON_CONTENT_TYPE,
                    'Authorization': core_api_auth.make_auth_header(core_api_auth.ORIGIN_CONSUMER,
                                                                    username='admin',
                                                                    password_hash=self._admin_password_hash)
                }

                http_client = AsyncHTTPClient()
                request = HTTPRequest(url, 'GET', headers=headers,
                                      connect_timeout=settings.slaves.timeout,
                                      request_timeout=settings.slaves.timeout + settings.slaves.keepalive)

                self.debug('calling api function GET /listen')

                try:
                    response = await http_client.fetch(request, raise_error=False)

                except Exception as e:
                    # We need to catch exceptions here even though raise_error is False,
                    # because it only affects HTTP errors
                    response = types.SimpleNamespace(error=e, code=599)

                # ignore response to older or mismatching listen requests
                if self._listen_session_id != requested_session_id:
                    self.debug('ignoring listen response to older session (%s)', requested_session_id)

                    break

                if not self._listen_session_id:
                    break

                try:
                    events = core_responses.parse(response)

                except core_responses.Error as e:
                    self.error('api call GET /listen failed: %s, retrying in %s seconds', e, settings.slaves.retry_interval)

                    if self._online:
                        self._online = False
                        await self._handle_offline()

                    await asyncio.sleep(settings.slaves.retry_interval)

                    # fast keep-alive
                    keep_alive = 1

                else:
                    self.debug('api call GET /listen succeeded')

                    self.update_last_sync()

                    # switching to normal keep-alive
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
                            # ignoring any error from handling an event is the best thing
                            # that we can do here, to ensure that we keep handling remaining events
                            pass

                    # _handle_event() indirectly stopped listening or removed this slave;
                    # this happens when the slave device is renamed
                    if self not in _slaves.values() or not self._listen_session_id:
                        break

                    if not self._online:
                        self._online = True
                        await self._handle_online()

                        if not self._online and self._listen_session_id:
                            self.warning('device did not successfully go online, retrying in %s seconds',
                                         settings.slaves.retry_interval)

                            await asyncio.sleep(settings.slaves.retry_interval)

                            # fast keep-alive
                            keep_alive = 1

                    else:  # still online
                        if needs_save_ports:
                            await self._save_ports()

            except asyncio.CancelledError:
                self.debug('listen task cancelled')
                break

    async def _poll_loop(self):
        interval = 0  # never wait when start polling

        while True:
            try:
                await asyncio.sleep(interval)
                interval = await self._poll_once()

                if not interval:
                    break

            except asyncio.CancelledError:
                self.debug('poll task cancelled')
                break

    async def _poll_once(self):
        # we have to use try ... except blocks quite aggressively here,
        # because we do not want any error that may occur to stop our poll loop

        if not self._poll_started:
            return 0

        if self not in _slaves.values():
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
        changed_names = [n for n in self._cached_attrs
                         if (n in attrs) and
                            (attrs[n] != self._cached_attrs[n])]

        for name in added_names:
            self.debug('detected new attribute: %s = %s', name, json_utils.dumps(attrs[name]))

        for name in removed_names:
            self.debug('detected removed attribute: %s', name)

        for name in changed_names:
            if name == 'definitions':
                self.debug('detected attribute definitions change')

            else:
                self.debug('detected attribute change: %s = %s -> %s',
                           name, json_utils.dumps(self._cached_attrs[name]), json_utils.dumps(attrs[name]))

        if removed_names or added_names or changed_names:
            try:
                await self._handle_device_update(**attrs)

            except exceptions.DeviceAlreadyExists:
                # when DeviceAlreadyExists is raised, we expect the slave to be disabled;
                # therefore we exit the polling loop right away
                return 0

            except exceptions.DeviceRenamed:
                # when DeviceRenamed is raised, we have to break the polling loop
                # right away, because another slave device has been added in place of this one
                return 0

            except Exception as e:
                self.error('failed to update device: %s', e)

        # if we reach this point, we can consider the slave device online

        if not self._online:
            self._online = True
            await self._handle_online()

            if not self._online:
                self.warning('device did not successfully go online, retrying in %s seconds',
                             settings.slaves.retry_interval)

                return settings.slaves.retry_interval

        # don't poll ports unless device is ready
        if not self._ready:
            return self._poll_interval

        # polling could have been stopped in the meantime
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

        # port values are also present among attrs when requesting GET /ports; we need to separate them
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
                    local_port.debug('detected attribute change: %s = %s -> %s',
                                     name, json_utils.dumps(local_attrs[name]), json_utils.dumps(attrs[name]))

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

    async def _fwupdate_poll_loop(self):
        counter = _FWUPDATE_POLL_TIMEOUT / _FWUPDATE_POLL_INTERVAL

        while True:
            await asyncio.sleep(_FWUPDATE_POLL_INTERVAL)
            if not self._fwupdate_poll_started:
                break  # loop stopped

            if not counter:
                self.error('timeout waiting for device to come up after firmware update')
                break  # we give up waiting for device to come up

            try:
                await self.api_call('GET', '/firmware')

            except Exception:
                pass

            counter -= 1

        # no matter what, when we exit this loop, the loop flag must be reset
        self._fwupdate_poll_started = False

    async def handle_event(self, event):
        method_name = '_handle_{}'.format(re.sub(r'[^\w]', '_', event['type']))
        method = getattr(self, method_name, None)
        if not method:
            self.warning('ignoring event of type %s', event['type'])
            return

        self.debug('handling event of type %s', event['type'])
        try:
            await method(**event['params'])

        except exceptions.DeviceRenamed:
            # treat DeviceRenamed as an expected exception, do not log anything but forward it
            raise

        except Exception as e:
            self.error('handling event of type %s failed: %s', event['type'], e)
            raise

    # noinspection PyShadowingBuiltins
    async def _handle_value_change(self, id, value):
        local_id = '{}.{}'.format(self._name, id)
        port = core_ports.get(local_id)
        if not port or not isinstance(port, SlavePort):
            raise exceptions.PortNotFound(self, local_id)

        if port.get_provisioning_value() is not None:
            self.debug('ignoring value-change event due to pending provisioning value')
            return

        self.debug('value of %s changed remotely from %s to %s',
                   port, json_utils.dumps(port.get_value()), json_utils.dumps(value))

        # trigger a master value-change if the returned value
        # has not changed from the one we locally have
        # (this happens when slave indirectly rejects pushed value,
        # by triggering itself a value-change with the old value)
        if port.get_cached_value() == value:
            port.trigger_value_change()

        port.set_cached_value(value)
        port.update_last_sync()
        await port.save()

    async def _handle_port_update(self, **attrs):
        local_id = '{}.{}'.format(self._name, attrs.get('id'))
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
                self.debug('%s.%s changed remotely: %s -> %s', port, name,
                           json_utils.dumps(old_value), json_utils.dumps(value))
                await port.handle_attr_change(name, value)

        port.update_cached_attrs(attrs)

        if 'value' in attrs:  # value has also been updated
            port.update_last_sync()

        await port.save()
        port.trigger_update()

    async def _handle_port_add(self, **attrs):
        local_id = '{}.{}'.format(self._name, attrs.get('id'))
        self.debug('port %s added remotely', local_id)

        await self._add_port(attrs)

    # noinspection PyShadowingBuiltins
    async def _handle_port_remove(self, id):
        local_id = '{}.{}'.format(self._name, id)
        port = core_ports.get(local_id)
        if not port or not isinstance(port, SlavePort):
            raise exceptions.PortNotFound(self, local_id)

        port.remove()

    async def _handle_device_update(self, **attrs):
        provisioning_attrs = self.get_provisioning_attrs()

        # we're working on a copy, just to be sure we can safely pop stuff from it
        attrs = dict(attrs)

        for name in attrs:
            if name in provisioning_attrs:
                self.debug('ignoring device-update attribute %s due to pending provisioning attribute', name)
                attrs.pop(name)

        self.update_cached_attrs(attrs)
        self.trigger_update()
        self.save()

    async def _handle_offline(self):
        self.debug('device is offline')

        self.trigger_update()

        for port in self._get_local_ports():
            if port.is_enabled():
                port.trigger_update()

    async def _handle_online(self):
        self.debug('device is online')

        # now that the device is back online, we can apply any pending provisioning data
        await self.apply_provisioning()

        if not self._poll_interval:
            # synchronize device attributes as well as ports,
            # but only if polling is disabled (since it does the same thing itself)

            try:
                await self.fetch_and_update_device()
                await self.fetch_and_update_ports()

            except Exception as e:
                self.error('failed to fetch device attributes and ports: %s', e, exc_info=True)

                self._online = False
                await self._handle_offline()

                return

            self.trigger_update()

        else:
            for port in self._get_local_ports():
                if port.is_enabled():
                    port.trigger_update()

        if not self._ready:
            self.debug('device is ready')
            self._ready = True

        self.save()

    def get_provisioning_attrs(self):
        provisioning = {}
        for name in self._provisioning_attrs:
            value = self._cached_attrs.get(name)
            if value is not None:
                provisioning[name] = value

        return provisioning

    def get_provisioning_webhooks(self):
        provisioning = {}
        for name in self._provisioning_webhooks:
            value = self._cached_webhooks.get(name)
            if value is not None:
                provisioning[name] = value

        return provisioning

    def get_provisioning_reverse(self):
        provisioning = {}
        for name in self._provisioning_reverse:
            value = self._cached_reverse.get(name)
            if value is not None:
                provisioning[name] = value

        return provisioning

    def clear_provisioning_attrs(self):
        self._provisioning_attrs = set()

    def clear_provisioning_webhooks(self):
        self._provisioning_webhooks = set()

    def clear_provisioning_reverse(self):
        self._provisioning_reverse = set()

    async def apply_provisioning(self):
        provisioned = False

        has_webhooks = 'webhooks' in self._cached_attrs.get('flags', [])
        has_reverse = 'reverse' in self._cached_attrs.get('flags', [])

        # device attributes provisioning
        attrs = self.get_provisioning_attrs()
        if attrs:
            self.debug('provisioning device attributes: %s', ', '.join(attrs.keys()))

            try:
                await self.api_call('PATCH', '/device', attrs)

            except Exception as e:
                self.error('failed to provision device attributes: %s', e)

            self.clear_provisioning_attrs()

            provisioned = True

        # webhooks params provisioning
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

        # reverse params provisioning
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

        # if we had some provisioning to do, we need to save the new device state (with cleared provisioning)
        if provisioned:
            self.save()

        # ports provisioning
        for port in self._get_local_ports():
            assert isinstance(port, SlavePort)

            provisioned = False

            # port attributes provisioning
            attrs = port.get_provisioning_attrs()
            if attrs:
                self.debug('provisioning %s attributes: %s', port, ', '.join(attrs.keys()))

                try:
                    await self.api_call('PATCH', '/ports/{}'.format(port.get_remote_id()), attrs)

                except Exception as e:
                    self.error('failed to provision %s attributes: %s', port, e)

                provisioned = True

            # port values provisioning
            value = port.get_provisioning_value()
            if value is not None:
                self.debug('provisioning %s value', port)

                try:
                    await self.api_call('PATCH', '/ports/{}/value'.format(port.get_remote_id()))

                except Exception as e:
                    self.error('failed to provision %s value: %s', port, e)

                provisioned = True

            port.clear_provisioning()

            # if we had some provisioning to do, we need to save the new port state (with cleared provisioning)
            if provisioned:
                await port.save()

        # if no webhooks params marked for provisioning, query the current params from device
        webhooks_queried = False
        if not webhooks_provisioned and has_webhooks:
            self.debug('querying current webhooks params')

            try:
                self._cached_webhooks = await self.api_call('GET', '/webhooks')
                webhooks_queried = True

            except Exception as e:
                self.error('failed to query current webhooks params: %s', e)

        # if no reverse params marked for provisioning, query the current params from device
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

    def schedule_provisioning_and_update(self, delay):
        if self._provisioning_timeout_handle:
            self._provisioning_timeout_handle.cancel()

        self._provisioning_timeout_handle = asyncio.create_task(utils.await_later(delay, self._provision_and_update))

    async def _provision_and_update(self):
        self.debug('starting provisioning & update procedure')
        self._provisioning_timeout_handle = None

        await self.apply_provisioning()
        await self.fetch_and_update_device()
        await self.fetch_and_update_ports()

    def intercept_request(self, method, path, params, request):
        # intercept API calls to device attributes, webhooks and reverse parameters, for devices that are offline

        if self._online:
            return False, None

        if method == 'GET':
            if path == '/device':
                # in theory, cached attributes should always be available, while device is online
                if self._cached_attrs:
                    return True, self._cached_attrs

            elif path == '/webhooks':
                # this is how we test that we have all required webhooks parameters in cache
                if len(set(core_api_schema.PATCH_WEBHOOKS['properties'].keys()) - set(self._cached_webhooks)) == 0:
                    return True, self._cached_webhooks

            elif path == '/reverse':
                # this is how we test that we have all required reverse parameters in cache
                if len(set(core_api_schema.PATCH_REVERSE['properties'].keys()) - set(self._cached_reverse)) == 0:
                    return True, self._cached_reverse

        elif method == 'PATCH':
            if path == '/device':
                for name, value in params.items():
                    self.debug('marking attribute %s for provisioning', name)
                    self._provisioning_attrs.add(name)
                    self._cached_attrs[name] = value

                # inform clients about the provisioning field change
                self.trigger_update()

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

        # by default, requests are not intercepted
        return False, None

    def intercept_response(self, method, path, body, response):
        if path.endswith('/'):
            path = path[:-1]

        if path == '/device':
            if method == 'PATCH':
                # intercept this API call to detect admin password changes
                new_admin_password = body and body.get('admin_password') or None
                if new_admin_password is not None:
                    self.debug('updating admin password')
                    self.set_admin_password(new_admin_password)
                    self.save()

                # detect local name changes
                new_name = body and body.get('name')
                if new_name and new_name != self._name:
                    try:
                        self.update_cached_attrs({'name': new_name}, partial=True)

                    except exceptions.DeviceRenamed:
                        pass

            elif method == 'GET':
                # intercept this API call so that we can update locally cached attributes whose values change often and
                # therefore do not trigger a device-update event
                attrs = {n: response[n] for n in _NO_EVENT_DEVICE_ATTRS if n in response}
                self.update_cached_attrs(attrs, partial=True)

        elif path == '/firmware':
            if method == 'PATCH' and not self._fwupdate_poll_started:
                # when performing firmware update, take device offline
                # and stop listening/polling mechanisms

                self.debug('firmware update process active')
                self.disable()
                self.trigger_update()
                self._start_fwupdate_polling()

            elif method == 'GET' and self._fwupdate_poll_started:
                if response.get('status') == 'idle':  # firmware update process not running
                    self.debug('firmware update process ended')
                    self.enable()
                    self._stop_fwupdate_polling()

        elif path == '/reset':
            if method == 'POST' and body.get('factory'):
                # when performing factory reset, disable device

                self.debug('device has been reset to factory defaults')
                self.disable()
                self.trigger_update()

    def intercept_error(self, error):
        if isinstance(error, core_responses.HTTPError):
            # Slave expression attribute is known as "device_expression" on Master; we must adapt the corresponding
            # error here
            m = _INVALID_EXPRESSION_RE.match(error.msg)
            if m:
                return core_responses.HTTPError(error.code, 'invalid field: device_' + m.group(1))

        return error



def get(name):
    return _slaves.get(name)


async def add(scheme, host, port, path, poll_interval, listen_enabled, admin_password=None, admin_password_hash=None):
    slave = Slave(None, scheme, host, port, path, poll_interval, listen_enabled, admin_password, admin_password_hash)

    slave.debug('starting add procedure')

    await slave.fetch_and_update_device()
    name = slave.get_name()

    if listen_enabled and 'listen' not in slave.get_cached_attr('flags'):
        slave.error('no listen support')
        raise exceptions.NoListenSupport(name)

    slave.enable()
    slave.save()
    slave.trigger_add()

    if not listen_enabled and not poll_interval:
        # device is permanently offline, but we must know its ports;
        # this would otherwise be called by Slave._handle_online()
        await slave.fetch_and_update_ports()

    _slaves[name] = slave

    return slave


def remove(slave):
    _slaves.pop(slave.get_name(), None)
    slave.remove()


def get_all():
    return _slaves.values()


def _slave_ready(slave):
    return slave.is_enabled() and not slave.is_permanently_offline()


def ready():
    # allow 110% of slaves.timeout setting for all slaves to get ready;
    # after that time has passed, slaves are as ready as they can be
    if time.time() - _load_time > int(settings.slaves.timeout * 1.1):
        return True

    slaves = (s for s in _slaves.values() if s.is_enabled() and not s.is_permanently_offline())

    return all(s.is_ready() for s in slaves)


def load():
    global _load_time

    _load_time = time.time()

    for entry in persist.query('slaves'):
        entry['name'] = entry.pop('id')

        try:
            slave = Slave(**entry)

        except Exception as e:
            logger.error('failed to load slave %s: %s', entry['name'], e, exc_info=True)
            continue

        _slaves[slave.get_name()] = slave

        if entry['enabled']:
            logger.debug('loaded %s', slave)
            slave.enable()

        else:
            logger.debug('loaded %s (disabled)', slave)

        slave.trigger_add()


async def cleanup():
    for slave in _slaves.values():
        await slave.cleanup()
