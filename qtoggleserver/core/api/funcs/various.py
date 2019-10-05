
import re

from qtoggleserver import slaves
from qtoggleserver import system
from qtoggleserver.conf import settings
from qtoggleserver.core import api as core_api
from qtoggleserver.core import device as core_device
from qtoggleserver.core import main
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core import reverse as core_reverse
from qtoggleserver.core import sessions as core_sessions
from qtoggleserver.core import vports as core_vports
from qtoggleserver.core import webhooks as core_webhooks
from qtoggleserver.core.api import schema as core_api_schema


@core_api.api_call(core_api.ACCESS_LEVEL_NONE)
async def get_access(request, access_level):
    return {
        'level': core_api.ACCESS_LEVEL_MAPPING[access_level]
    }


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
async def get_listen(request, session_id, timeout, access_level):
    if session_id is None:
        raise core_api.APIError(400, 'missing field: session_id')

    if not re.match('[a-zA-Z0-9]{1,32}', session_id):
        raise core_api.APIError(400, 'invalid field: session_id')

    if timeout is not None:
        try:
            timeout = int(timeout)

        except Exception:
            raise core_api.APIError(400, 'invalid field: timeout')

        if timeout < 1 or timeout > 3600:
            raise core_api.APIError(400, 'invalid field: timeout')

    else:
        timeout = 60

    session = core_sessions.get(session_id)
    events = await session.reset_and_wait(timeout, access_level)

    return [e.to_json() for e in events]


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def post_reset(request, params):
    core_api_schema.validate(params, core_api_schema.POST_RESET)

    factory = params.get('factory')

    if factory:
        core_api.logger.info('resetting to factory defaults')

        core_ports.reset()
        core_vports.reset()
        core_device.reset()
        if settings.webhooks.enabled:
            core_webhooks.reset()
        if settings.reverse.enabled:
            core_reverse.reset()
        if settings.slaves.enabled:
            slaves.reset()

    main.loop.call_later(2, system.reboot)
