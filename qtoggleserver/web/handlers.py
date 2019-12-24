
import inspect
import logging

from tornado.web import RequestHandler, HTTPError, StaticFileHandler as TornadoStaticFileHandler
from tornado.iostream import StreamClosedError

from qtoggleserver.conf import settings
from qtoggleserver.core import api as core_api
from qtoggleserver.core import responses as core_responses
from qtoggleserver.core.api import auth as core_api_auth
from qtoggleserver.core.api import funcs as core_api_funcs
from qtoggleserver.core.device import attrs as core_device_attrs
from qtoggleserver.slaves.api import funcs as slaves_api_funcs
from qtoggleserver.ui.api import funcs as ui_api_funcs
from qtoggleserver.utils import json as json_utils

from .constants import FRONTEND_URL_PREFIX
from .j2template import J2TemplateMixin
from .quicontext import make_context


logger = logging.getLogger(__name__)


class NoSuchFunction(HTTPError):
    def __init__(self):
        super().__init__(404, 'no such function')


class BaseHandler(RequestHandler):
    _UNDEFINED = {}

    def __init__(self, *args, **kwargs):
        self._json = self._UNDEFINED
        self._response_body = ''
        self._response_body_json = None

        RequestHandler.__init__(self, *args, **kwargs)

    def get_request_json(self):
        if self._json is self._UNDEFINED:
            try:
                self._json = json_utils.loads(self.request.body)

            except ValueError as e:
                logger.error('could not decode json from request body: %s', e)

                raise core_api.APIError(400, 'malformed body') from e

        return self._json

    def finish(self, chunk=None):
        self._response_body = chunk

        return super().finish(chunk)

    def finish_json(self, data):
        self._response_body_json = data

        data = json_utils.dumps(data)
        data += '\n'

        self.set_header('Content-Type', 'application/json; charset=utf-8')
        return self.finish(data)

    def get_response_body(self):
        return self._response_body

    def get_response_body_json(self):
        return self._response_body_json

    def get_response_headers(self):
        return dict(self._headers.get_all())

    def get(self, **kwargs):
        raise NoSuchFunction()

    head = post = delete = patch = put = options = get

    def _handle_request_exception(self, exception):
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
            pass  # nevermind

    def data_received(self, chunk):
        pass


class StaticFileHandler(TornadoStaticFileHandler):
    def data_received(self, chunk):
        pass

    def set_extra_headers(self, path):
        self.set_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')


class JSModuleMapperStaticFileHandler(StaticFileHandler):
    def initialize(self, path, mapping, default_filename=None):
        super().initialize(path, default_filename)
        self._mapping = {k.encode(): v.encode() for k, v in mapping.items()}
        self._mapped_content = None

    def get_content_size(self):
        return len(self.get_mapped_content())

    def get_content(self, abspath, start=None, end=None):
        return self.get_mapped_content()

    @classmethod
    def get_content_version(cls, abspath):
        return ''

    def get_mapped_content(self):
        if self._mapped_content is None:
            content = b''.join(list(super().get_content(self.absolute_path)))

            if self.absolute_path.endswith('.js'):
                for k, v in self._mapping.items():
                    content = content.replace(k, v)

            self._mapped_content = content

        return self._mapped_content


class NoSuchFunctionHandler(BaseHandler):
    pass


class RedirectFrontendHandler(BaseHandler):
    def get(self):
        self.redirect(f'/{FRONTEND_URL_PREFIX}/')


class TemplateHandler(J2TemplateMixin, BaseHandler):
    def prepare(self):
        self.set_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')

    def get_context(self, path, offs=0):
        # Adjust static URL prefix to a relative path matching currently requested frontend path

        context = make_context()
        slashes = path.count('/') + offs
        if slashes == 0:
            prefix = 'frontend/'

        elif slashes > 1:
            prefix = '/'.join(['..'] * (slashes - 1)) + '/'

        else:
            prefix = ''

        context['static_url'] = prefix + context['static_url']

        return context


class FrontendHandler(TemplateHandler):
    def get(self, path):
        self.render('index.html', **self.get_context(path))


class ManifestHandler(TemplateHandler):
    def get(self, path):
        pretty_name = self.get_query_argument('pretty_name', None)
        description = self.get_query_argument('description', None)

        context = self.get_context(path, offs=1)
        if pretty_name:
            context['pretty_name'] = pretty_name
        if description:
            context['description'] = description

        self.set_header('Content-Type', 'application/manifest+json; charset="utf-8"')
        self.render('manifest.json', **context)


class ServiceWorkerHandler(TemplateHandler):
    def get(self):
        self.set_header('Content-Type', 'application/javascript; charset="utf-8"')
        self.render('service-worker.js', **make_context())


class APIHandler(BaseHandler):
    AUTH_ENABLED = True

    def __init__(self, *args, **kwargs):
        self.access_level = core_api.ACCESS_LEVEL_NONE
        self.username = None

        BaseHandler.__init__(self, *args, **kwargs)

    def prepare(self):
        # disable cache
        self.set_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')

        if not self.AUTH_ENABLED:
            return

        # parse auth header
        auth = self.request.headers.get('Authorization')
        if auth:
            try:
                usr = core_api_auth.parse_auth_header(auth, core_api_auth.ORIGIN_CONSUMER,
                                                      core_api_auth.consumer_password_hash_func)

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

        logger.debug('granted access level %s (username=%s)',
                     core_api.ACCESS_LEVEL_MAPPING[self.access_level], self.username)

    async def call_api_func(self, func, default_status=200, **kwargs):
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

    async def _handle_api_call_exception(self, func, kwargs, error):
        kwargs = dict(kwargs)
        params = kwargs.pop('params', None)
        args = json_utils.dumps(kwargs)
        body = params and json_utils.dumps(params) or '{}'

        if isinstance(error, core_responses.HTTPError):
            error = core_api.APIError(error.code, error.msg)

        if isinstance(error, core_api.APIError):
            logger.error('api call %s failed: %s (args=%s, body=%s)', func.__name__, error, args, body)

            self.set_status(error.status)
            if not self._finished:  # Avoid finishing an already finished request
                await self.finish_json(dict({'error': error.message}, **error.params))

        elif isinstance(error, StreamClosedError) and func.__name__ == 'get_listen':
            logger.debug('api call get_listen could not complete: stream closed')

        else:
            logger.error('api call %s failed: %s (args=%s, body=%s)', func.__name__, error, args, body, exc_info=True)

            self.set_status(500)
            if not self._finished:  # Avoid finishing an already finished request
                await self.finish_json({'error': str(error)})


class DeviceHandler(APIHandler):
    async def get(self):
        await self.call_api_func(core_api_funcs.get_device)

    async def patch(self):
        await self.call_api_func(core_api_funcs.patch_device, default_status=204)


class ResetHandler(APIHandler):
    async def post(self):
        await self.call_api_func(core_api_funcs.post_reset, default_status=204)


class FirmwareHandler(APIHandler):
    async def get(self):
        await self.call_api_func(core_api_funcs.get_firmware)

    async def patch(self):
        await self.call_api_func(core_api_funcs.patch_firmware, default_status=204)


class AccessHandler(APIHandler):
    async def get(self):
        await self.call_api_func(core_api_funcs.get_access, access_level=self.access_level)


class SlaveDevicesHandler(APIHandler):
    async def get(self):
        await self.call_api_func(slaves_api_funcs.get_slave_devices)

    async def post(self):
        await self.call_api_func(slaves_api_funcs.post_slave_devices, default_status=201)


class SlaveDeviceHandler(APIHandler):
    async def patch(self, name):
        await self.call_api_func(slaves_api_funcs.patch_slave_device, name=name, default_status=204)

    async def delete(self, name):
        await self.call_api_func(slaves_api_funcs.delete_slave_device, name=name, default_status=204)


class SlaveDeviceEventsHandler(APIHandler):
    AUTH_ENABLED = False  # we'll take care of the authentication inside API call functions

    async def post(self, name):
        await self.call_api_func(slaves_api_funcs.post_slave_device_events, name=name, default_status=204)


class SlaveDeviceForwardHandler(APIHandler):
    async def get(self, name, path):
        await self.call_api_func(slaves_api_funcs.slave_device_forward,
                                 name=name, method=self.request.method, path=path)

    post = patch = delete = get


class PortsHandler(APIHandler):
    async def get(self):
        await self.call_api_func(core_api_funcs.get_ports)

    async def post(self):
        if not settings.core.virtual_ports:
            raise NoSuchFunction()

        await self.call_api_func(core_api_funcs.post_ports, default_status=201)


class PortHandler(APIHandler):
    async def delete(self, port_id):
        if not settings.core.virtual_ports:
            raise NoSuchFunction()

        await self.call_api_func(core_api_funcs.delete_port, port_id=port_id, default_status=204)

    async def patch(self, port_id):
        await self.call_api_func(core_api_funcs.patch_port, port_id=port_id, default_status=204)


class PortValueHandler(APIHandler):
    async def get(self, port_id):
        await self.call_api_func(core_api_funcs.get_port_value, port_id=port_id)

    async def patch(self, port_id):
        await self.call_api_func(core_api_funcs.patch_port_value, port_id=port_id, default_status=204)


class PortSequenceHandler(APIHandler):
    async def post(self, port_id):
        if not settings.core.sequences_support:
            raise NoSuchFunction()

        await self.call_api_func(core_api_funcs.post_port_sequence, port_id=port_id, default_status=204)


class WebhooksHandler(APIHandler):
    async def get(self):
        await self.call_api_func(core_api_funcs.get_webhooks)

    async def patch(self):
        await self.call_api_func(core_api_funcs.patch_webhooks, default_status=204)


class ListenHandler(APIHandler):
    async def get(self):
        session_id = self.get_argument('session_id', None)
        timeout = self.get_argument('timeout', None)

        await self.call_api_func(core_api_funcs.get_listen,
                                 session_id=session_id, timeout=timeout, access_level=self.access_level)


class ReverseHandler(APIHandler):
    async def get(self):
        await self.call_api_func(core_api_funcs.get_reverse)

    async def patch(self):
        await self.call_api_func(core_api_funcs.patch_reverse, default_status=204)


class DashboardPanelsHandler(APIHandler):
    async def get(self):
        await self.call_api_func(ui_api_funcs.get_panels)

    async def put(self):
        await self.call_api_func(ui_api_funcs.put_panels, default_status=204)


class PrefsHandler(APIHandler):
    async def get(self):
        await self.call_api_func(ui_api_funcs.get_prefs)

    async def put(self):
        await self.call_api_func(ui_api_funcs.put_prefs, default_status=204)
