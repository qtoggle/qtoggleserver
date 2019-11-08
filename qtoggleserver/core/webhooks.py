
import logging
import queue

from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from qtoggleserver import persist
from qtoggleserver.conf import settings
from qtoggleserver.core.api import auth as core_api_auth
from qtoggleserver.core.device import attrs as core_device_attrs
from qtoggleserver.core import responses as core_responses
from qtoggleserver.utils import http as http_utils
from qtoggleserver.utils import json as json_utils


logger = logging.getLogger(__name__)
_webhooks = None


class InvalidParamError(Exception):
    def __init__(self, param):
        self._param = param
        super().__init__('invalid field: {}'.format(param))


class WebhooksRequest:
    def __init__(self, body):
        self.body = body
        self.retries = 0


class Webhooks:
    # noinspection PyUnusedLocal
    def __init__(self, scheme=None, host=None, port=None, path=None, timeout=None, retries=None, **kwargs):

        # the enabled value comes with kwargs but is ignored,
        # as the webhook will be explicitly enabled afterwards

        self._enabled = False
        self._scheme = scheme
        self._host = host
        self._port = port
        self._path = path
        self._timeout = timeout
        self._retries = retries
        self._url = None

        self._queue = queue.Queue(settings.core.event_queue_size)

    def __str__(self):
        s = 'webhooks'

        if not self._enabled:
            s += ' [disabled]'

        if self._scheme:
            s += ' ' + self.get_url()

        return s

    def is_enabled(self):
        return self._enabled

    def enable(self):
        if self._enabled:
            return

        logger.debug('enabling %s', self)

        self._enabled = True

    def disable(self):
        if not self._enabled:
            return

        logger.debug('disabling %s', self)

        self._enabled = False

        # drop all queued requests
        while not self._queue.empty():
            self._queue.get()

    def get_url(self):
        if not hasattr(self, '_url'):
            if self._scheme == 'http' and self._port == 80 or self._scheme == 'https' and self._port == 443:
                self._url = '{}://{}{}'.format(self._scheme, self._host, self._path)

            else:
                self._url = '{}://{}:{}{}'.format(self._scheme, self._host, self._port, self._path)

        return self._url

    def call(self, body):
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

    def _request(self, request):
        if not self._enabled:
            return

        url = self.get_url()
        body = json_utils.dumps(request.body)

        def on_response(response):
            try:
                core_responses.parse(response)

            except core_responses.Error as e:
                logger.error('%s: call failed: %s', self, e)

                # retry mechanism
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
            'Content-Type': http_utils.JSON_CONTENT_TYPE,
            'Authorization': core_api_auth.make_auth_header(core_api_auth.ORIGIN_DEVICE, username=None,
                                                            password_hash=core_device_attrs.normal_password_hash)
        }
        request = HTTPRequest(url, 'POST', headers=headers, body=body,
                              connect_timeout=self._timeout, request_timeout=self._timeout,
                              follow_redirects=True)

        logger.debug('%s: calling', self)

        http_client.fetch(request, on_response)  # TODO await

    def _check_pending(self):
        try:
            request = self._queue.get(block=False)

        except queue.Empty:
            return

        self._request(request)

    def to_json(self):
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


def get():
    return _webhooks


def setup(enabled, scheme=None, host=None, port=None, path=None, timeout=None, retries=None, **kwargs):
    global _webhooks

    if _webhooks and _webhooks.is_enabled():
        _webhooks.disable()

    _webhooks = Webhooks(scheme, host, port, path, timeout, retries)
    if enabled:
        _webhooks.enable()


def load():
    data = persist.get_value('webhooks')
    if data is None:
        setup(enabled=False)
        logger.debug('loaded %s', _webhooks)

        return

    setup(**data)
    logger.debug('loaded %s', _webhooks)


def save():
    if _webhooks is None:
        return

    logger.debug('saving data')
    persist.set_value('webhooks', _webhooks.to_json())


def reset():
    logger.debug('clearing persisted data')
    persist.remove('webhooks')
