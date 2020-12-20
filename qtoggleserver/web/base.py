
import asyncio
import inspect
import logging
import re

from typing import Any, Callable, Dict, Optional

from tornado.iostream import StreamClosedError
from tornado.web import RequestHandler, HTTPError


from qtoggleserver.core import api as core_api
from qtoggleserver.core import responses as core_responses
from qtoggleserver.core.device import attrs as core_device_attrs
from qtoggleserver.core.api import auth as core_api_auth
from qtoggleserver.utils import json as json_utils


SESSION_ID_RE = re.compile(r'[a-zA-Z0-9]{1,32}')

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

        super().__init__(*args, **kwargs)

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


class APIHandler(BaseHandler):
    AUTH_ENABLED = True

    def __init__(self, *args, **kwargs) -> None:
        self.access_level: int = core_api.ACCESS_LEVEL_NONE
        self.username: Optional[str] = None

        super().__init__(*args, **kwargs)

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

        # Validate session id
        session_id = self.request.headers.get('Session-Id')
        if session_id:
            if not SESSION_ID_RE.match(session_id):
                raise core_api.APIError(400, 'invalid-header', header='Session-Id')

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
