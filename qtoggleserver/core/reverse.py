
import asyncio
import logging
import re
import types

from tornado import httputil
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from qtoggleserver import persist
from qtoggleserver.conf import settings
from qtoggleserver.core import api as core_api
from qtoggleserver.core import responses as core_responses
from qtoggleserver.core.api import auth as core_api_auth
from qtoggleserver.utils import http as http_utils
from qtoggleserver.utils import json as json_utils


# a list of API calls that are prohibited via reverse mechanism
BLACKLIST_CALLS = [
    ('GET', re.compile(r'^/listen'))
]

logger = logging.getLogger(__name__)
_reverse = None


class InvalidParamError(Exception):
    def __init__(self, param):
        self._param = param
        super().__init__('invalid field: {}'.format(param))


class InvalidConsumerRequestError(Exception):
    pass


class UnauthorizedConsumerRequestError(Exception):
    pass


class Reverse:
    # noinspection PyUnusedLocal
    def __init__(self, scheme=None, host=None, port=None, path=None, device_id=None, password=None, timeout=None,
                 **kwargs):

        # the enabled value comes with kwargs but is ignored,
        # as the reverse object will be explicitly enabled afterwards

        self._scheme = scheme
        self._host = host
        self._port = port
        self._path = path
        self._device_id = device_id
        self._password = password
        self._timeout = timeout

        self._enabled = False
        self._url = None

    def __str__(self):
        s = 'reverse'

        if not self._enabled:
            s += ' [disabled]'

        if self._scheme:
            s += ' ' + self.get_url()

        return s

    def get_url(self):
        if not hasattr(self, '_url'):
            if self._scheme == 'http' and self._port == 80 or self._scheme == 'https' and self._port == 443:
                self._url = '{}://{}{}'.format(self._scheme, self._host, self._path)

            else:
                self._url = '{}://{}:{}{}'.format(self._scheme, self._host, self._port, self._path)

        return self._url

    def is_enabled(self):
        return self._enabled

    def enable(self):
        if self._enabled:
            return

        logger.debug('starting wait loop')

        self._enabled = True
        asyncio.create_task(self._session_loop())

    def disable(self):
        if not self._enabled:
            return

        logger.debug('wait stopped')

        self._enabled = False

    def to_json(self):
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

    async def _session_loop(self):
        api_response_dict = None
        sleep_interval = 0

        while True:
            if not self._enabled:
                break

            if sleep_interval:
                await asyncio.sleep(sleep_interval)
                sleep_interval = 0

            try:
                api_request_dict = await self._wait(api_response_dict)  # TODO properly implement me

            except UnauthorizedConsumerRequestError:
                api_response_dict = {
                    'status': 401,
                    'body': json_utils.dumps({'error': 'authentication required'})
                }

                continue

            except Exception as e:
                logger.error('wait failed: %s, retrying in %s seconds', e, settings.reverse.retry_interval,
                             exc_info=True)
                sleep_interval = settings.reverse.retry_interval
                continue

            # the reverse mechanism has been disabled while waiting
            if not self._enabled:
                break

            try:
                api_response_dict = await self._process_api_request(api_request_dict)

            except Exception as e:
                logger.error('reverse API call failed: %s', e, exc_info=True)
                sleep_interval = settings.reverse.retry_interval
                api_response_dict = None
                continue

    async def _wait(self, api_request_dict, api_response_dict):
        url = self.get_url()

        headers = {
            'Content-Type': http_utils.JSON_CONTENT_TYPE,
            'Authorization': core_api_auth.make_auth_header(core_api_auth.ORIGIN_DEVICE,
                                                            username=self._device_id,
                                                            password_hash=self._password)
        }

        body_str = None
        if api_response_dict:  # answer request
            body_str = api_response_dict['body']
            headers['Status'] = '{} {}'.format(api_response_dict['status'],
                                               httputil.responses[api_response_dict['status']])
            headers['API-Call-Id'] = api_request_dict['api_call_id']

        http_client = AsyncHTTPClient()
        request = HTTPRequest(url, 'POST', headers=headers, body=body_str,
                              connect_timeout=self._timeout, request_timeout=self._timeout)

        if api_response_dict:
            logger.debug('sending answer request to %s %s (API call id %s) to %s',
                         api_request_dict['method'], api_request_dict['path'], api_request_dict['api_call_id'], url)

        else:
            logger.debug('sending initial request to %s', url)

        try:
            # this response is in fact an API request
            consumer_response = await http_client.fetch(request, raise_error=False)

        except Exception as e:
            # We need to catch exceptions here even though raise_error is False,
            # because it only affects HTTP errors
            consumer_response = types.SimpleNamespace(error=e, code=599)

        api_request_dict = self._parse_consumer_response(consumer_response)

        return api_request_dict

    @staticmethod
    def _parse_consumer_response(response):
        body = core_responses.parse(response)  # will raise for non-2xx

        auth = response.headers.get('Authorization')
        if not auth:
            raise UnauthorizedConsumerRequestError('missing authorization header')

        try:
            usr = core_api_auth.parse_auth_header(auth, core_api_auth.ORIGIN_CONSUMER,
                                                  core_api_auth.consumer_password_hash_func)

        except core_api_auth.AuthError as e:
            raise UnauthorizedConsumerRequestError(str(e)) from e

        access_level = core_api.ACCESS_LEVEL_MAPPING[usr]

        try:
            method = response.headers['Method']

        except KeyError:
            raise InvalidConsumerRequestError('missing Method header') from None

        try:
            path = response.headers['Path']

        except KeyError:
            raise InvalidConsumerRequestError('missing Path header') from None

        try:
            api_call_id = response.headers['API-Call-Id']

        except KeyError:
            raise InvalidConsumerRequestError('missing API-Call-Id header') from None

        return {
            'body': body,
            'method': method,
            'path': path,
            'api_call_id': api_call_id,
            'access_level': access_level,
            'username': usr
        }

    async def _process_api_request(self, request_dict):
        from qtoggleserver.web import server as web_server

        if self._is_black_listed(request_dict):
            return {
                'status': 404,
                'body': json_utils.dumps({'error': 'no such function'})
            }

        request = httputil.HTTPServerRequest(method=request_dict['method'],
                                             uri=request_dict['path'],
                                             body=request_dict['body'])

        dispatcher = web_server.get_application().find_handler(request)
        dispatcher.execute()

        status = dispatcher.handler.get_status()
        body = dispatcher.handler.get_response_body()

        return {
            'status': status,
            'body': body
        }

    @staticmethod
    def _is_black_listed(request_dict):
        for method, path_re in BLACKLIST_CALLS:
            if request_dict['method'] != method:
                continue

            if path_re.match(request_dict['path']):
                return True

        return False


def get():
    return _reverse


def setup(enabled, scheme=None, host=None, port=None, path=None, device_id=None, password=None, timeout=None, **kwargs):
    global _reverse

    if _reverse and _reverse.is_enabled():
        _reverse.disable()

    _reverse = Reverse(scheme, host, port, path, device_id, password, timeout)
    if enabled:
        _reverse.enable()


def load():
    data = persist.get_value('reverse')
    if data is None:
        setup(enabled=False)
        logger.debug('loaded %s', _reverse)

        return

    setup(**data)
    logger.debug('loaded %s', _reverse)


def save():
    if _reverse is None:
        return

    logger.debug('saving data')
    persist.set_value('reverse', _reverse.to_json())


def reset():
    logger.debug('clearing persisted data')
    persist.remove('reverse')
