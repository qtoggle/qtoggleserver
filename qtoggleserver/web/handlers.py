
import asyncio
import inspect
import logging

from typing import Any, Callable, Dict, Optional

from tornado.iostream import StreamClosedError
from tornado.web import RequestHandler, HTTPError

from qtoggleserver.conf import settings
from qtoggleserver.core import api as core_api
from qtoggleserver.core import responses as core_responses
from qtoggleserver.core.api import auth as core_api_auth
from qtoggleserver.core.api import funcs as core_api_funcs
from qtoggleserver.core.device import attrs as core_device_attrs
from qtoggleserver.slaves.api import funcs as slaves_api_funcs
from qtoggleserver.ui.api import funcs as ui_api_funcs
from qtoggleserver.utils import json as json_utils


logger = logging.getLogger(__name__)


class NoSuchFunction(HTTPError):
    def __init__(self) -> None:
        super().__init__(404, 'no-such-function')


class BaseHandler(RequestHandler):
    _UNDEFINED = {}

    def __init__(self, *args, **kwargs) -> None:
        self._json: Any = self._UNDEFINED
        self._response_body: str = ''
        self._response_body_json: Any = None

        RequestHandler.__init__(self, *args, **kwargs)

    def get_request_json(self) -> Any:
        if self._json is self._UNDEFINED:
            try:
                self._json = json_utils.loads(self.request.body)

            except ValueError as e:
                logger.error('could not decode json from request body: %s', e)

                raise core_api.APIError(400, 'malformed-body') from e

        return self._json

    def finish(self, chunk: Optional[str] = None) -> asyncio.Future:
        self._response_body = chunk

        return super().finish(chunk)

    def finish_json(self, data: Any) -> asyncio.Future:
        self._response_body_json = data

        data = json_utils.dumps(data)
        data += '\n'

        self.set_header('Content-Type', 'application/json; charset=utf-8')
        return self.finish(data)

    def get_response_body(self) -> str:
        return self._response_body

    def get_response_body_json(self) -> Any:
        return self._response_body_json

    def get_response_headers(self) -> Dict[str, str]:
        return dict(self._headers.get_all())

    def get(self, **kwargs) -> None:
        raise NoSuchFunction()

    head = post = delete = patch = put = options = get

    def _handle_request_exception(self, exception: Exception) -> None:
        try:
            if isinstance(exception, HTTPError):
                logger.error('%s %s: %s', self.request.method, self.request.uri, exception)
                self.set_status(exception.status_code)
                self.finish_json({'error': (exception.log_message or
                                            getattr(exception, 'reason', None) or str(exception))})

            else:
                logger.error(str(exception), exc_info=True)
                self.set_status(500)
                self.finish_json({'error': 'internal server error'})

        except RuntimeError:
            pass  # Nevermind

    def data_received(self, chunk: bytes) -> None:
        pass


class NoSuchFunctionHandler(BaseHandler):
    pass


class APIHandler(BaseHandler):
    AUTH_ENABLED = True

    def __init__(self, *args, **kwargs) -> None:
        self.access_level: int = core_api.ACCESS_LEVEL_NONE
        self.username: Optional[str] = None

        BaseHandler.__init__(self, *args, **kwargs)

    def prepare(self) -> None:
        # Disable cache
        self.set_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')

        if not self.AUTH_ENABLED:
            return

        # Parse auth header
        auth = self.request.headers.get('Authorization')
        if auth:
            try:
                usr = core_api_auth.parse_auth_header(
                    auth,
                    core_api_auth.ORIGIN_CONSUMER,
                    core_api_auth.consumer_password_hash_func
                )

            except core_api_auth.AuthError as e:
                logger.warning(str(e))
                return

        else:
            if core_device_attrs.admin_password_hash == core_device_attrs.EMPTY_PASSWORD_HASH:
                logger.debug('authenticating request as admin due to empty admin password')
                usr = 'admin'

            else:
                logger.warning('missing authorization header')
                return

        self.access_level = core_api.ACCESS_LEVEL_MAPPING[usr]
        self.username = usr

        logger.debug(
            'granted access level %s (username=%s)',
            core_api.ACCESS_LEVEL_MAPPING[self.access_level],
            self.username
        )

    async def call_api_func(self, func: Callable, default_status: int = 200, **kwargs) -> None:
        try:
            if self.request.method in ('POST', 'PATCH', 'PUT'):
                kwargs['params'] = self.get_request_json()

            response = func(self, **kwargs)
            if inspect.isawaitable(response):
                response = await response

            self.set_status(default_status)
            if response is not None or default_status == 200:
                await self.finish_json(response)

            else:
                await self.finish()

        except Exception as e:
            await self._handle_api_call_exception(func, kwargs, e)

    async def _handle_api_call_exception(self, func: Callable, kwargs: dict, error: Exception) -> None:
        kwargs = dict(kwargs)
        params = kwargs.pop('params', None)
        args = json_utils.dumps(kwargs)
        body = params and json_utils.dumps(params) or '{}'

        if isinstance(error, core_responses.HTTPError):
            error = core_api.APIError.from_http_error(error)

        if isinstance(error, core_api.APIError):
            logger.error('api call %s failed: %s (args=%s, body=%s)', func.__name__, error, args, body)

            self.set_status(error.status)
            if not self._finished:  # Avoid finishing an already finished request
                await self.finish_json(error.to_json())

        elif isinstance(error, StreamClosedError) and func.__name__ == 'get_listen':
            logger.debug('api call get_listen could not complete: stream closed')

        else:
            logger.error('api call %s failed: %s (args=%s, body=%s)', func.__name__, error, args, body, exc_info=True)

            self.set_status(500)
            if not self._finished:  # Avoid finishing an already finished request
                await self.finish_json({'error': str(error)})


class DeviceHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(core_api_funcs.get_device)

    async def patch(self) -> None:
        await self.call_api_func(core_api_funcs.patch_device, default_status=204)


class ResetHandler(APIHandler):
    async def post(self) -> None:
        await self.call_api_func(core_api_funcs.post_reset, default_status=204)


class FirmwareHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(core_api_funcs.get_firmware)

    async def patch(self) -> None:
        await self.call_api_func(core_api_funcs.patch_firmware, default_status=204)


class AccessHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(core_api_funcs.get_access, access_level=self.access_level)


class SlaveDevicesHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(slaves_api_funcs.get_slave_devices)

    async def post(self) -> None:
        await self.call_api_func(slaves_api_funcs.post_slave_devices, default_status=201)


class SlaveDeviceHandler(APIHandler):
    async def patch(self, name: str) -> None:
        await self.call_api_func(slaves_api_funcs.patch_slave_device, name=name, default_status=204)

    async def delete(self, name: str) -> None:
        await self.call_api_func(slaves_api_funcs.delete_slave_device, name=name, default_status=204)


class SlaveDeviceEventsHandler(APIHandler):
    AUTH_ENABLED = False  # We'll take care of the authentication inside API call functions

    async def post(self, name: str) -> None:
        await self.call_api_func(slaves_api_funcs.post_slave_device_events, name=name, default_status=204)


class SlaveDeviceForwardHandler(APIHandler):
    async def get(self, name: str, path: str) -> None:
        await self.call_api_func(
            slaves_api_funcs.slave_device_forward,
            name=name,
            method=self.request.method,
            path=path
        )

    post = patch = delete = get


class DiscoveredHandler(APIHandler):
    async def get(self) -> None:
        timeout = self.get_argument('timeout', None)
        if timeout:
            timeout = int(timeout)

        await self.call_api_func(slaves_api_funcs.get_discovered, timeout=timeout)

    async def delete(self) -> None:
        await self.call_api_func(slaves_api_funcs.delete_discovered, default_status=204)


class DiscoveredDeviceHandler(APIHandler):
    async def patch(self, name: str) -> None:
        await self.call_api_func(slaves_api_funcs.patch_discovered_device, name=name)


class PortsHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(core_api_funcs.get_ports)

    async def post(self) -> None:
        if not settings.core.virtual_ports:
            raise NoSuchFunction()

        await self.call_api_func(core_api_funcs.post_ports, default_status=201)


class PortHandler(APIHandler):
    async def delete(self, port_id: str) -> None:
        if not settings.core.virtual_ports:
            raise NoSuchFunction()

        await self.call_api_func(core_api_funcs.delete_port, port_id=port_id, default_status=204)

    async def patch(self, port_id: str) -> None:
        await self.call_api_func(core_api_funcs.patch_port, port_id=port_id, default_status=204)


class PortValueHandler(APIHandler):
    async def get(self, port_id: str) -> None:
        await self.call_api_func(core_api_funcs.get_port_value, port_id=port_id)

    async def patch(self, port_id: str) -> None:
        await self.call_api_func(core_api_funcs.patch_port_value, port_id=port_id, default_status=204)


class PortSequenceHandler(APIHandler):
    async def patch(self, port_id: str) -> None:
        if not settings.core.sequences_support:
            raise NoSuchFunction()

        await self.call_api_func(core_api_funcs.patch_port_sequence, port_id=port_id, default_status=204)


class WebhooksHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(core_api_funcs.get_webhooks)

    async def patch(self) -> None:
        await self.call_api_func(core_api_funcs.patch_webhooks, default_status=204)


class ListenHandler(APIHandler):
    async def get(self) -> None:
        session_id = self.get_argument('session_id', None)
        timeout = self.get_argument('timeout', None)
        if timeout:
            timeout = int(timeout)

        await self.call_api_func(
            core_api_funcs.get_listen,
            session_id=session_id,
            timeout=timeout,
            access_level=self.access_level
        )


class ReverseHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(core_api_funcs.get_reverse)

    async def patch(self) -> None:
        await self.call_api_func(core_api_funcs.patch_reverse, default_status=204)


class DashboardPanelsHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(ui_api_funcs.get_panels)

    async def put(self) -> None:
        await self.call_api_func(ui_api_funcs.put_panels, default_status=204)


class PrefsHandler(APIHandler):
    async def get(self) -> None:
        await self.call_api_func(ui_api_funcs.get_prefs)

    async def put(self) -> None:
        await self.call_api_func(ui_api_funcs.put_prefs, default_status=204)
