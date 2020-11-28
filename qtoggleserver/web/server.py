
import asyncio
import logging
import ssl

from typing import List, Optional

from tornado.web import Application, HTTPServer, RequestHandler, URLSpec
from qui.web import tornado as qui_tornado

from qtoggleserver import system
from qtoggleserver.conf import settings
from qtoggleserver.core import history
from qtoggleserver.slaves.discover import is_enabled as is_discover_enabled
from qtoggleserver.web import handlers


logger = logging.getLogger(__name__)

_application: Optional[Application] = None
_server: Optional[HTTPServer] = None


def _log_request(handler: RequestHandler) -> None:
    if handler.get_status() < 400:
        log_method = logger.debug

    elif handler.get_status() < 500:
        log_method = logger.warning

    else:
        log_method = logger.error

    request_time = 1000.0 * handler.request.request_time()
    log_method('%d %s %.2fms', handler.get_status(), handler._request_summary(), request_time)


def _make_routing_table() -> List[URLSpec]:
    handlers_list = []

    # Frontend

    if settings.frontend.enabled:
        handlers_list += qui_tornado.make_routing_table()

        handlers_list += [
            URLSpec(r'^/api/frontend/dashboard/panels/?$', handlers.DashboardPanelsHandler),
            URLSpec(r'^/api/frontend/prefs/?$', handlers.PrefsHandler),
            URLSpec(r'^/api/frontend/?$', handlers.FrontendHandler),
        ]

    handlers_list += [
        # Device management
        URLSpec(r'^/api/device/?$', handlers.DeviceHandler),
        URLSpec(r'^/api/reset/?$', handlers.ResetHandler),
        URLSpec(r'^/api/access/?$', handlers.AccessHandler),

        # Port management
        URLSpec(r'^/api/ports/?$', handlers.PortsHandler),
        URLSpec(r'^/api/ports/(?P<port_id>[A-Za-z0-9_.-]+)/?$', handlers.PortHandler),

        # Port values
        URLSpec(r'^/api/ports/(?P<port_id>[A-Za-z0-9_.-]+)/value/?$', handlers.PortValueHandler),
    ]

    if settings.core.sequences_support:
        handlers_list += [
            URLSpec(r'^/api/ports/(?P<port_id>[A-Za-z0-9_.-]+)/sequence/?$', handlers.PortSequenceHandler)
        ]

    if history.is_enabled():
        handlers_list += [
            URLSpec(r'^/api/ports/(?P<port_id>[A-Za-z0-9_.-]+)/history/?$', handlers.PortHistoryHandler),
        ]

    if settings.core.backup_support:
        handlers_list += [
            URLSpec(r'^/api/backup/endpoints/?$', handlers.BackupEndpointsHandler)
        ]

    # Firmware

    if settings.system.fwupdate.driver:
        handlers_list += [
            URLSpec(r'^/api/firmware/?$', handlers.FirmwareHandler)
        ]

    # Slave devices management

    if settings.slaves.enabled:
        handlers_list += [
            URLSpec(r'^/api/devices/?$', handlers.SlaveDevicesHandler),
            URLSpec(r'^/api/devices/(?P<name>[A-Za-z0-9_-]+)/?$', handlers.SlaveDeviceHandler),
            URLSpec(r'^/api/devices/(?P<name>[A-Za-z0-9_-]+)/events/?$', handlers.SlaveDeviceEventsHandler),
            URLSpec(r'^/api/devices/(?P<name>[A-Za-z0-9_-]+)/forward/(?P<path>.+)$', handlers.SlaveDeviceForwardHandler)
        ]

        if is_discover_enabled():
            handlers_list += [
                URLSpec(r'^/api/discovered/?$', handlers.DiscoveredHandler),
                URLSpec(r'^/api/discovered/(?P<name>[A-Za-z0-9_-]+)/?$', handlers.DiscoveredDeviceHandler)
            ]

    # Notifications

    if settings.webhooks.enabled:
        handlers_list += [
            URLSpec(r'^/api/webhooks/?$', handlers.WebhooksHandler)
        ]

    if settings.core.listen_support:
        handlers_list += [
            URLSpec(r'^/api/listen/?$', handlers.ListenHandler)
        ]

    # Reverse API calls

    if settings.reverse.enabled:
        handlers_list += [
            URLSpec(r'^/api/reverse/?$', handlers.ReverseHandler)
        ]

    # System API calls

    if system.conf.can_write_conf_file():
        handlers_list += [
            URLSpec(r'^/api/system/?$', handlers.SystemHandler)
        ]

    # Default 404 API handler

    handlers_list += [
        URLSpec(r'^/api/.*$', handlers.NoSuchFunctionHandler)
    ]

    return handlers_list


def get_application() -> Application:
    global _application

    if _application is None:
        _application = Application(
            handlers=_make_routing_table(),
            debug=False,
            compress_response=settings.server.compress_response,
            log_function=_log_request
        )

    return _application


def get_server() -> Optional[HTTPServer]:
    return _server


async def init() -> None:
    global _server

    address, port = settings.server.addr, settings.server.port

    ssl_context = None
    if settings.server.https.cert_file and settings.server.https.key_file:
        logger.info('setting up HTTPS using certificate from %s', settings.server.https.cert_file)
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(settings.server.https.cert_file, settings.server.https.key_file)

    app = get_application()

    try:
        _server = app.listen(port, address, ssl_options=ssl_context)
        logger.info('server listening on %s:%s', address, port)

    except Exception as e:
        logger.error('server listen failed: %s', e)
        raise


async def cleanup() -> None:
    global _server

    if not _server:
        return

    _server.stop()

    # Allow a small amount of time for web server callbacks to complete
    await asyncio.sleep(1)
