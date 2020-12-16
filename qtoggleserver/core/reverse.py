
from __future__ import annotations

import asyncio
import logging
import re

from types import SimpleNamespace
from typing import Optional

from tornado import httputil
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPResponse

from qtoggleserver import persist
from qtoggleserver.conf import settings
from qtoggleserver.core import api as core_api
from qtoggleserver.core import responses as core_responses
from qtoggleserver.core.api import auth as core_api_auth
from qtoggleserver.core.typing import GenericJSONDict
from qtoggleserver.utils import json as json_utils


# A list of API calls that are prohibited via reverse mechanism
BLACKLIST_CALLS = [
    ('GET', re.compile(r'^/listen'))
]

logger = logging.getLogger(__name__)

_reverse: Optional[Reverse] = None


class ReverseError(Exception):
    pass


class InvalidParamError(ReverseError):
    def __init__(self, param: str) -> None:
        self.param: str = param

        super().__init__(f'Invalid field: {param}')


class InvalidConsumerRequestError(ReverseError):
    pass


class UnauthorizedConsumerRequestError(ReverseError):
    pass


class Reverse:
    def __init__(
        self,
        scheme: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        path: Optional[str] = None,
        device_id: Optional[str] = None,
        password_hash: Optional[str] = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> None:

        # The enabled value comes with kwargs but is ignored; the reverse object will be explicitly enabled afterwards

        self._scheme = scheme
        self._host = host
        self._port = port
        self._path = path
        self._device_id = device_id
        self._password_hash = password_hash
        self._timeout = timeout

        self._enabled: bool = False
        self._url: Optional[str] = None

    def __str__(self) -> str:
        s = 'reverse'

        if not self._enabled:
            s += ' [disabled]'

        if self._scheme:
            s += ' ' + self.get_url()

        return s

    def get_url(self) -> str:
        if not self._url:
            if self._scheme == 'http' and self._port == 80 or self._scheme == 'https' and self._port == 443:
                self._url = f'{self._scheme}://{self._host}{self._path}'

            else:
                self._url = f'{self._scheme}://{self._host}:{self._port}{self._path}'

        return self._url

    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        if self._enabled:
            return

        logger.debug('starting wait loop')

        self._enabled = True
        asyncio.create_task(self._session_loop())

    def disable(self) -> None:
        if not self._enabled:
            return

        logger.debug('wait stopped')

        self._enabled = False

    def to_json(self) -> GenericJSONDict:
        d = {
            'enabled': self._enabled,
            'scheme': self._scheme,
            'host': self._host,
            'port': self._port,
            'path': self._path,
            'device_id': self._device_id,
            'timeout': self._timeout
        }

        return d

    async def _session_loop(self) -> None:
        api_response_dict = None
        api_request_dict = {}  # TODO this does not work
        sleep_interval = 0

        while True:
            if not self._enabled:
                break

            if sleep_interval:
                await asyncio.sleep(sleep_interval)
                sleep_interval = 0

            try:
                api_request_dict = await self._wait(api_request_dict, api_response_dict)  # TODO properly implement me

            except UnauthorizedConsumerRequestError:
                api_response_dict = {
                    'status': 401,
                    'body': json_utils.dumps({'error': 'authentication-required'})
                }

                continue

            except Exception as e:
                logger.error(
                    'wait failed: %s, retrying in %s seconds',
                    e,
                    settings.reverse.retry_interval,
                    exc_info=True
                )
                sleep_interval = settings.reverse.retry_interval
                continue

            # The reverse mechanism has been disabled while waiting
            if not self._enabled:
                break

            try:
                api_response_dict = await self._process_api_request(api_request_dict)

            except Exception as e:
                logger.error('reverse API call failed: %s', e, exc_info=True)
                sleep_interval = settings.reverse.retry_interval
                api_response_dict = None
                continue

    async def _wait(self, api_request_dict: GenericJSONDict, api_response_dict: GenericJSONDict) -> GenericJSONDict:
        url = self.get_url()

        headers = {
            'Content-Type': json_utils.JSON_CONTENT_TYPE,
            'Authorization': core_api_auth.make_auth_header(
                core_api_auth.ORIGIN_DEVICE,
                username=self._device_id,
                password_hash=self._password_hash
            )
        }

        body_str = None
        if api_response_dict:  # Answer request
            body_str = api_response_dict['body']
            headers['Status'] = f'{api_response_dict["status"]} {httputil.responses[api_response_dict["status"]]}'
            headers['Session-Id'] = api_request_dict['session_id']

        http_client = AsyncHTTPClient()
        request = HTTPRequest(
            url,
            'POST',
            headers=headers,
            body=body_str,
            connect_timeout=self._timeout,
            request_timeout=self._timeout
        )

        if api_response_dict:
            logger.debug(
                'sending answer request to %s %s (API call id %s) to %s',
                api_request_dict['method'],
                api_request_dict['path'],
                api_request_dict['session_id'],
                url
            )

        else:
            logger.debug('sending initial request to %s', url)

        try:
            # This response is in fact an API request
            consumer_response = await http_client.fetch(request, raise_error=False)

        except Exception as e:
            # We need to catch exceptions here even though raise_error is False, because it only affects HTTP errors
            consumer_response = SimpleNamespace(error=e, code=599)

        api_request_dict = self._parse_consumer_response(consumer_response)

        return api_request_dict

    @staticmethod
    def _parse_consumer_response(response: HTTPResponse) -> GenericJSONDict:
        body = core_responses.parse(response)  # Will raise for non-2xx

        auth = response.headers.get('Authorization')
        if not auth:
            raise UnauthorizedConsumerRequestError('Missing authorization header')

        try:
            usr = core_api_auth.parse_auth_header(
                auth, core_api_auth.ORIGIN_CONSUMER,
                core_api_auth.consumer_password_hash_func
            )

        except core_api_auth.AuthError as e:
            raise UnauthorizedConsumerRequestError(str(e)) from e

        access_level = core_api.ACCESS_LEVEL_MAPPING[usr]

        try:
            method = response.headers['Method']

        except KeyError:
            raise InvalidConsumerRequestError('Missing Method header') from None

        try:
            path = response.headers['Path']

        except KeyError:
            raise InvalidConsumerRequestError('Missing Path header') from None

        try:
            session_id = response.headers['Session-Id']

        except KeyError:
            raise InvalidConsumerRequestError('Missing Session-Id header') from None

        return {
            'body': body,
            'method': method,
            'path': path,
            'session_id': session_id,
            'access_level': access_level,
            'username': usr
        }

    async def _process_api_request(self, request_dict: GenericJSONDict) -> GenericJSONDict:
        from qtoggleserver.web import server as web_server

        if self._request_is_black_listed(request_dict):
            return {
                'status': 404,
                'body': json_utils.dumps({'error': 'no-such-function'})
            }

        request = httputil.HTTPServerRequest(
            method=request_dict['method'],
            uri=request_dict['path'],
            body=request_dict['body']
        )

        dispatcher = web_server.get_application().find_handler(request)
        await dispatcher.execute()

        status = dispatcher.handler.get_status()
        body = dispatcher.handler.get_response_body()

        return {
            'status': status,
            'body': body
        }

    @staticmethod
    def _request_is_black_listed(request_dict: GenericJSONDict) -> bool:
        for method, path_re in BLACKLIST_CALLS:
            if request_dict['method'] != method:
                continue

            if path_re.match(request_dict['path']):
                return True

        return False


def get() -> Optional[Reverse]:
    return _reverse


def setup(
    enabled: bool,
    scheme: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    path: Optional[str] = None,
    device_id: Optional[str] = None,
    password_hash: Optional[str] = None,
    timeout: Optional[int] = None,
    **kwargs
) -> None:

    global _reverse

    if _reverse and _reverse.is_enabled():
        _reverse.disable()

    _reverse = Reverse(scheme, host, port, path, device_id, password_hash, timeout)
    if enabled:
        _reverse.enable()


async def load() -> None:
    data = await persist.get_value('reverse')
    if data is None:
        setup(enabled=False)
        logger.debug('loaded %s', _reverse)

        return

    setup(**data)
    logger.debug('loaded %s', _reverse)


async def save() -> None:
    if _reverse is None:
        return

    logger.debug('saving persisted data')
    await persist.set_value('reverse', _reverse.to_json())


async def reset() -> None:
    logger.debug('clearing persisted data')
    await persist.remove('reverse')


async def init() -> None:
    logger.debug('loading persisted data')
    await load()


async def cleanup() -> None:
    pass
