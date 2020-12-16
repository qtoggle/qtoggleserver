
from typing import Dict

from qtoggleserver import slaves
from qtoggleserver import system
from qtoggleserver.conf import settings
from qtoggleserver.core import api as core_api
from qtoggleserver.core import device as core_device
from qtoggleserver.core import history as core_history
from qtoggleserver.core import main
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core import reverse as core_reverse
from qtoggleserver.core import sessions as core_sessions
from qtoggleserver.core import vports as core_vports
from qtoggleserver.core import webhooks as core_webhooks
from qtoggleserver.core.api import schema as core_api_schema
from qtoggleserver.core.typing import GenericJSONDict, GenericJSONList


@core_api.api_call(core_api.ACCESS_LEVEL_NONE)
async def get_access(request: core_api.APIRequest) -> Dict[str, str]:
    return {
        'level': core_api.ACCESS_LEVEL_MAPPING[request.access_level]
    }


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
async def get_listen(
    request: core_api.APIRequest
) -> GenericJSONList:

    session_id = request.headers.get('Session-Id')
    if not session_id:
        raise core_api.APIError(400, 'missing-header', header='Session-Id')

    timeout = request.query.get('timeout')
    if timeout is not None:
        try:
            timeout = int(timeout)

        except ValueError:
            raise core_api.APIError(400, 'invalid-field', field='timeout') from None

        if timeout < 1 or timeout > 3600:
            raise core_api.APIError(400, 'invalid-field', field='timeout')

    else:
        timeout = 60  # default

    session = core_sessions.get(session_id)
    events = await session.reset_and_wait(timeout, request.access_level)

    return [await e.to_json() for e in events]


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def post_reset(request: core_api.APIRequest, params: GenericJSONDict) -> None:
    core_api_schema.validate(params, core_api_schema.POST_RESET)

    factory = params.get('factory')

    if factory:
        core_api.logger.info('resetting to factory defaults')

        await core_ports.reset()
        await core_vports.reset()
        await core_device.reset()
        if settings.webhooks.enabled:
            await core_webhooks.reset()
        if settings.reverse.enabled:
            await core_reverse.reset()
        if settings.slaves.enabled:
            await slaves.reset_ports()
            await slaves.reset_slaves()
        if core_history.is_enabled():
            await core_history.reset()

    main.loop.call_later(2, system.reboot)
