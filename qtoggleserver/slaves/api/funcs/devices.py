
from __future__ import annotations

import asyncio
import re

from typing import Any, List, Optional

from qtoggleserver.conf import settings
from qtoggleserver.core import api as core_api
from qtoggleserver.core import events as core_events
from qtoggleserver.core import responses as core_responses
from qtoggleserver.core.api import auth as core_api_auth
from qtoggleserver.core.api import schema as core_api_schema
from qtoggleserver.core.typing import GenericJSONDict
from qtoggleserver.slaves import devices as slaves_devices
from qtoggleserver.slaves import exceptions as slaves_exceptions

from .. import schema as api_schema


_LONG_TIMEOUT_API_CALLS = [
    ('PATCH', re.compile(r'/device/?')),
    ('GET', re.compile(r'/firmware/?')),
    ('PATCH', re.compile(r'/firmware/?')),
    ('PATCH', re.compile(r'/ports/[^/]+/?')),
    ('PATCH', re.compile(r'/ports/[^/]+/value/?')),
    ('POST', re.compile(r'/devices/?')),
    ('PATCH', re.compile(r'/devices/[^/]+/?'))
]


async def add_slave_device(properties: GenericJSONDict) -> slaves_devices.Slave:
    scheme = properties['scheme']
    host = properties['host']
    port = properties['port']
    path = properties['path']
    admin_password = properties.get('admin_password')
    admin_password_hash = properties.get('admin_password_hash')
    poll_interval = properties.get('poll_interval', 0)
    listen_enabled = properties.get('listen_enabled')

    # Look for slave duplicate
    for slave in slaves_devices.get_all():
        if (slave.get_scheme() == scheme and
            slave.get_host() == host and
            slave.get_port() == port and
            slave.get_path() == path):

            raise core_api.APIError(400, 'duplicate-device')

    if poll_interval and listen_enabled:
        raise core_api.APIError(400, 'listening-and-polling')

    # Ensure admin password is supplied, in a way or another
    if admin_password is None and admin_password_hash is None:
        raise core_api.APIError(400, 'missing-field', field='admin_password')

    try:
        slave = await slaves_devices.add(
            scheme,
            host,
            port,
            path,
            poll_interval,
            listen_enabled,
            admin_password=admin_password,
            admin_password_hash=admin_password_hash
        )

    except (core_responses.HostUnreachable,
            core_responses.NetworkUnreachable,
            core_responses.UnresolvableHostname) as e:

        raise core_api.APIError(502, 'unreachable') from e

    except core_responses.ConnectionRefused as e:
        raise core_api.APIError(502, 'connection-refused') from e

    except core_responses.InvalidJson as e:
        raise core_api.APIError(502, 'invalid-device') from e

    except core_responses.Timeout as e:
        raise core_api.APIError(504, 'device-timeout') from e

    except slaves_exceptions.InvalidDevice as e:
        raise core_api.APIError(502, 'invalid-device') from e

    except slaves_exceptions.NoListenSupport as e:
        raise core_api.APIError(400, 'no-listen-support') from e

    except slaves_exceptions.DeviceAlreadyExists as e:
        raise core_api.APIError(400, 'duplicate-device') from e

    except core_api.APIError:
        raise

    except core_responses.HTTPError as e:
        # We need to treat the 401/403 slave responses as a 400
        if e.code in (401, 403):
            raise core_api.APIError(400, 'forbidden') from e

        raise core_api.APIError.from_http_error(e) from e

    except Exception as e:
        raise slaves_exceptions.adapt_api_error(e) from e

    return slave


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def get_slave_devices(request: core_api.APIRequest) -> List[GenericJSONDict]:
    return [slave.to_json() for slave in slaves_devices.get_all()]


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def put_slave_devices(request: core_api.APIRequest, params: List[GenericJSONDict]) -> None:
    if not settings.core.backup_support:
        raise core_api.APIError(404, 'no-such-function')

    core_api_schema.validate(
        params,
        api_schema.PUT_SLAVE_DEVICES
    )

    core_api.logger.debug('restoring slave devices')

    # Disable event handling during the processing of this request, as we're going to trigger a full-update at the end
    core_events.disable()

    try:
        # Remove all slave devices
        for slave in list(slaves_devices.get_all()):
            await slaves_devices.remove(slave)

        add_device_schema = dict(api_schema.POST_SLAVE_DEVICES)
        add_device_schema['additionalProperties'] = True

        # Validate supplied slave properties
        for properties in params:
            core_api_schema.validate(properties, add_device_schema)

        # Create slave devices
        await asyncio.gather(*(add_slave_device(properties) for properties in params))

    finally:
        core_events.enable()

    await core_events.trigger_full_update()

    core_api.logger.debug('slave devices restore done')


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def post_slave_devices(request: core_api.APIRequest, params: GenericJSONDict) -> GenericJSONDict:
    core_api_schema.validate(params, api_schema.POST_SLAVE_DEVICES)
    slave = await add_slave_device(params)

    return slave.to_json()


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def patch_slave_device(request: core_api.APIRequest, name: str, params: GenericJSONDict) -> None:
    core_api_schema.validate(params, api_schema.PATCH_SLAVE_DEVICE)

    slave = slaves_devices.get(name)
    if not slave:
        raise core_api.APIError(404, 'no-such-device')

    if params.get('enabled') is True and not slave.is_enabled():
        await slave.enable()

    elif params.get('enabled') is False and slave.is_enabled():
        await slave.disable()

    if params.get('poll_interval') and params.get('listen_enabled'):
        raise core_api.APIError(400, 'listening-and-polling')

    if params.get('poll_interval') is not None:
        slave.set_poll_interval(params['poll_interval'])

    if params.get('listen_enabled') is not None:
        if params['listen_enabled']:
            # We need to know if device supports listening; we therefore call GET /device before enabling it

            if slave.is_enabled():
                try:
                    attrs = await slave.api_call('GET', '/device')

                except Exception as e:
                    raise slaves_exceptions.adapt_api_error(e) from e

                if 'listen' not in attrs['flags']:
                    raise core_api.APIError(400, 'no-listen-support')

            slave.enable_listen()

        else:
            slave.disable_listen()

    slave.save()
    await slave.trigger_update()


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def slave_device_forward(
    request: core_api.APIRequest,
    name: str,
    method: str,
    path: str,
    params: Optional[GenericJSONDict] = None,
    internal_use: bool = False
) -> Any:

    slave = slaves_devices.get(name)

    if not slave:
        raise core_api.APIError(404, 'no-such-device')

    if not internal_use:
        if not path.startswith('/'):
            path = '/' + path

        if path.startswith('/listen'):
            raise core_api.APIError(404, 'no-such-function')

    intercepted, response = await slave.intercept_request(method, path, params, request)
    if intercepted:
        return response

    override_disabled = request.query_arguments.get('override_disabled')
    if not slave.is_enabled() and (override_disabled != 'true'):
        raise core_api.APIError(404, 'device-disabled')

    override_offline = request.query_arguments.get('override_offline')
    if (not slave.is_online() or not slave.is_ready()) and (override_offline != 'true'):
        raise core_api.APIError(503, 'device-offline')

    # Use default slave timeout unless API call requires longer timeout
    timeout = settings.slaves.timeout
    for m, path_re in _LONG_TIMEOUT_API_CALLS:
        if method == m and path_re.fullmatch(path):
            timeout = settings.slaves.long_timeout
            break

    try:
        response = await slave.api_call(method, path, params, timeout=timeout, retry_counter=None)

    except Exception as e:
        raise slaves_exceptions.adapt_api_error(e) from e

    return response


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def delete_slave_device(request: core_api.APIRequest, name: str) -> None:
    slave = slaves_devices.get(name)
    if not slave:
        raise core_api.APIError(404, 'no-such-device')

    await slaves_devices.remove(slave)


@core_api.api_call(core_api.ACCESS_LEVEL_NONE)
async def post_slave_device_events(request: core_api.APIRequest, name: str, params: GenericJSONDict) -> None:
    slave = slaves_devices.get(name)
    if not slave:
        raise core_api.APIError(404, 'no-such-device')

    # Slave events endpoint has special privilege requirements: its token signature must be validated using slave admin
    # password

    auth = request.headers.get('Authorization')
    if not auth:
        slave.warning('missing authorization header')
        raise core_api.APIError(401, 'authentication-required')

    try:
        core_api_auth.parse_auth_header(
            auth,
            core_api_auth.ORIGIN_DEVICE,
            lambda u: slave.get_admin_password_hash(),
            require_usr=False
        )

    except core_api_auth.AuthError as e:
        slave.warning(str(e))
        raise core_api.APIError(401, 'authentication-required') from e

    core_api_schema.validate(params, api_schema.POST_SLAVE_DEVICE_EVENTS)

    if slave.get_poll_interval() > 0:
        raise core_api.APIError(400, 'polling-enabled')

    if slave.is_listen_enabled():
        raise core_api.APIError(400, 'listening-enabled')

    # At this point we can be sure the slave is permanently offline

    try:
        await slave.handle_event(params)

    except Exception as e:
        raise core_api.APIError(500, 'unexpected-error', message=str(e)) from e

    slave.update_last_sync()
    slave.save()

    # As soon as we receive event requests (normally generated by a webhook), we can consider the device is temporarily
    # reachable, so we apply provisioning values and update data locally
    slave.schedule_provisioning_and_update(1)
