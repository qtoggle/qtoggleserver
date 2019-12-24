
import logging
import os.path

from tornado.web import Application

from qtoggleserver.conf import settings
from qtoggleserver.web import handlers

from .constants import FRONTEND_DIR, FRONTEND_URL_PREFIX


logger = logging.getLogger(__name__)

_application = None


def _log_request(handler):
    if handler.get_status() < 400:
        log_method = logger.debug

    elif handler.get_status() < 500:
        log_method = logger.warning

    else:
        log_method = logger.error

    request_time = 1000.0 * handler.request.request_time()
    # noinspection PyProtectedMember
    log_method('%d %s %.2fms', handler.get_status(), handler._request_summary(), request_time)


def _make_handlers():
    handlers_list = []

    # frontend

    if settings.frontend.enabled:
        frontend_path = os.path.join(settings.pkg_path, FRONTEND_DIR)
        if not os.path.exists(frontend_path):  # Look outside of main package (dev mode)
            frontend_path = os.path.join(settings.pkg_path, '..', FRONTEND_DIR)

        if settings.frontend.debug:
            js_module_path_mapping = {
                '$qui': f'/{FRONTEND_URL_PREFIX}/static/qui/js',
                '$app': f'/{FRONTEND_URL_PREFIX}/static/app/js'
            }

            # In debug mode, we serve QUI static files from its own folder, assumed to be in node_modules/@qtoggle
            qui_path = os.path.join(frontend_path, 'node_modules', '@qtoggle', 'qui')

            handlers_list.append((fr'^/{FRONTEND_URL_PREFIX}/static/qui/(.*)$',
                                  handlers.JSModuleMapperStaticFileHandler,
                                  {'path': qui_path, 'mapping': js_module_path_mapping}))

            handlers_list.append((fr'^/{FRONTEND_URL_PREFIX}/static/app/(.*)$',
                                  handlers.JSModuleMapperStaticFileHandler,
                                  {'path': frontend_path, 'mapping': js_module_path_mapping}))

        else:
            if os.path.exists(os.path.join(frontend_path, 'dist')):  # "dist" folder (prod mode, unpackaged)
                frontend_path = os.path.join(frontend_path, 'dist')

            handlers_list.append((fr'^/{FRONTEND_URL_PREFIX}/static/(.*)$',
                                  handlers.StaticFileHandler,
                                  {'path': frontend_path}))

        handlers_list += [
            (r'^/?$', handlers.RedirectFrontendHandler),
            (fr'^/{FRONTEND_URL_PREFIX}/service-worker.js$', handlers.ServiceWorkerHandler),
            (fr'^/{FRONTEND_URL_PREFIX}(?P<path>.*)/manifest.json$', handlers.ManifestHandler),
            (fr'^/{FRONTEND_URL_PREFIX}(?P<path>.*)', handlers.FrontendHandler),
        ]

        handlers_list += [
            (fr'^/api/frontend/dashboard/panels/?$', handlers.DashboardPanelsHandler),
            (fr'^/api/frontend/prefs/?$', handlers.PrefsHandler),
        ]

    handlers_list += [
        # device management
        (r'^/api/device/?$', handlers.DeviceHandler),
        (r'^/api/reset/?$', handlers.ResetHandler),
        (r'^/api/access/?$', handlers.AccessHandler),

        # port management
        (r'^/api/ports/?$', handlers.PortsHandler),
        (r'^/api/ports/(?P<port_id>[\w.]+)/?$', handlers.PortHandler),

        # port values
        (r'^/api/ports/(?P<port_id>[\w.]+)/value/?$', handlers.PortValueHandler),
    ]

    if settings.core.sequences_support:
        handlers_list += [
            (r'^/api/ports/(?P<port_id>[\w.]+)/sequence/?$', handlers.PortSequenceHandler)
        ]

    # firmware

    if settings.system.fwupdate_driver:
        handlers_list += [
            (r'^/api/firmware/?$', handlers.FirmwareHandler)
        ]

    # slave devices management

    if settings.slaves.enabled:
        handlers_list += [
            (r'^/api/devices/?$', handlers.SlaveDevicesHandler),
            (r'^/api/devices/(?P<name>\w+)/?$', handlers.SlaveDeviceHandler),
            (r'^/api/devices/(?P<name>\w+)/events/?$', handlers.SlaveDeviceEventsHandler),
            (r'^/api/devices/(?P<name>\w+)/forward/(?P<path>.+)$', handlers.SlaveDeviceForwardHandler)
        ]

    # notifications

    if settings.webhooks.enabled:
        handlers_list += [
            (r'^/api/webhooks/?$', handlers.WebhooksHandler)
        ]

    if settings.core.listen_support:
        handlers_list += [
            (r'^/api/listen/?$', handlers.ListenHandler)
        ]

    # reverse API calls

    if settings.reverse.enabled:
        handlers_list += [
            (r'^/api/reverse/?$', handlers.ReverseHandler)
        ]

    handlers_list += [
        (r'^.*$', handlers.NoSuchFunctionHandler)
    ]

    return handlers_list


def get_application():
    global _application

    if _application is None:
        _application = Application(
            handlers=_make_handlers(),
            debug=False,
            compress_response=settings.server.compress_response,
            log_function=_log_request,
        )

    return _application
