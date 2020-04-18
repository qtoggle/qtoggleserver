
from __future__ import annotations

import logging
import queue

from typing import Optional

from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPResponse

from qtoggleserver import persist
from qtoggleserver.conf import settings
from qtoggleserver.core import responses as core_responses
from qtoggleserver.core.api import auth as core_api_auth
from qtoggleserver.core.device import attrs as core_device_attrs
from qtoggleserver.core.typing import GenericJSONDict
from qtoggleserver.utils import json as json_utils


logger = logging.getLogger(__name__)

_webhooks: Optional[Webhooks] = None


class WebhooksError(Exception):
    pass


class InvalidParamError(WebhooksError):
    def __init__(self, param: str) -> None:
        self.param: str = param

        super().__init__(f'Invalid field: {param}')


class WebhooksRequest:
    def __init__(self, body: GenericJSONDict) -> None:
        self.body: GenericJSONDict = body
        self.retries: int = 0


class Webhooks:
    def __init__(
        self,
        scheme: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        path: Optional[str] = None,
        timeout: Optional[int] = None,
        retries: Optional[int] = None,
        **kwargs
    ) -> None:

        # The enabled value comes with kwargs but is ignored; webhooks will be explicitly enabled afterwards

        self._enabled: bool = False
        self._scheme: Optional[str] = scheme
        self._host: Optional[str] = host
        self._port: Optional[int] = port
        self._path: Optional[str] = path
        self._timeout: Optional[int] = timeout
        self._retries: Optional[int] = retries
        self._url: Optional[str] = None

        self._queue: queue.Queue = queue.Queue(settings.core.event_queue_size)

    def __str__(self) -> str:
        s = 'webhooks'

        if not self._enabled:
            s += ' [disabled]'

        if self._scheme:
            s += ' ' + self.get_url()

        return s

    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        if self._enabled:
            return

        logger.debug('enabling %s', self)

        self._enabled = True

    def disable(self) -> None:
        if not self._enabled:
            return

        logger.debug('disabling %s', self)

        self._enabled = False

        # Drop all queued requests
        while not self._queue.empty():
            self._queue.get()

    def get_url(self) -> str:
        if not self._url:
            if self._scheme == 'http' and self._port == 80 or self._scheme == 'https' and self._port == 443:
                self._url = f'{self._scheme}://{self._host}{self._path}'

            else:
                self._url = f'{self._scheme}://{self._host}:{self._port}{self._path}'

        return self._url

    def call(self, body: GenericJSONDict) -> None:
        if not self._enabled:
            return

        request = WebhooksRequest(body)

        if self._queue.empty():
            return self._request(request)

        try:
            self._queue.put(request)

        except queue.Full:
            logger.error('%s: queue is full', self)
            return

    def _request(self, request: WebhooksRequest) -> None:
        if not self._enabled:
            return

        url = self.get_url()
        body = json_utils.dumps(request.body)

        def on_response(response: HTTPResponse) -> None:
            try:
                core_responses.parse(response)

            except core_responses.Error as e:
                logger.error('%s: call failed: %s', self, e)

                # Retry mechanism
                if not self._retries:
                    return self._check_pending()

                if request.retries <= self._retries:
                    request.retries += 1
                    logger.debug('%s: resending request (retry %s/%s)', self, request.retries, self._retries)

                    self._request(request)

                else:
                    self._check_pending()

            else:
                logger.debug('%s: call succeeded', self)
                self._check_pending()

        http_client = AsyncHTTPClient()
        # TODO use webhooks password
        headers = {
            'Content-Type': json_utils.JSON_CONTENT_TYPE,
            'Authorization': core_api_auth.make_auth_header(
                core_api_auth.ORIGIN_DEVICE,
                username=None,
                password_hash=core_device_attrs.normal_password_hash
            )
        }
        request = HTTPRequest(
            url,
            'POST',
            headers=headers,
            body=body,
            connect_timeout=self._timeout,
            request_timeout=self._timeout,
            follow_redirects=True
        )

        logger.debug('%s: calling', self)

        http_client.fetch(request, callback=on_response)  # TODO implement me using await

    def _check_pending(self) -> None:
        try:
            request = self._queue.get(block=False)

        except queue.Empty:
            return

        self._request(request)

    def to_json(self) -> GenericJSONDict:
        d = {
            'enabled': self._enabled,
            'scheme': self._scheme,
            'host': self._host,
            'port': self._port,
            'path': self._path,
            'timeout': self._timeout,
            'retries': self._retries
        }

        return d


def get() -> Optional[Webhooks]:
    return _webhooks


def setup(
    enabled: bool,
    scheme: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    path: Optional[str] = None,
    timeout: Optional[int] = None,
    retries: Optional[int] = None,
    **kwargs
) -> None:

    global _webhooks

    if _webhooks and _webhooks.is_enabled():
        _webhooks.disable()

    _webhooks = Webhooks(scheme, host, port, path, timeout, retries)
    if enabled:
        _webhooks.enable()


def load() -> None:
    data = persist.get_value('webhooks')
    if data is None:
        setup(enabled=False)
        logger.debug('loaded %s', _webhooks)

        return

    setup(**data)
    logger.debug('loaded %s', _webhooks)


def save() -> None:
    if _webhooks is None:
        return

    logger.debug('saving persisted data')
    persist.set_value('webhooks', _webhooks.to_json())


def reset() -> None:
    logger.debug('clearing persisted data')
    persist.remove('webhooks')


async def init() -> None:
    logger.debug('loading persisted data')
    load()


async def cleanup() -> None:
    pass
