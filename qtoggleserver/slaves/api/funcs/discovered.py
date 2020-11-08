
from qtoggleserver.core import api as core_api
from qtoggleserver.core.api import schema as core_api_schema
from qtoggleserver.core.typing import GenericJSONDict, GenericJSONList
from qtoggleserver.slaves import discover as slaves_discover
from qtoggleserver.slaves import exceptions as slaves_exceptions

from .. import schema as api_schema


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def get_discovered(request: core_api.APIRequest, timeout: int) -> GenericJSONList:
    if timeout is None:
        raise core_api.APIError(400, 'missing-field', field='timeout')

    discovered_devices = slaves_discover.get_discovered_devices()
    if discovered_devices is None:
        await slaves_discover.discover(timeout)

    return [d.to_json() for d in slaves_discover.get_discovered_devices().values()]


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def delete_discovered(request: core_api.APIRequest) -> None:
    await slaves_discover.finish()


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def patch_discovered_device(request: core_api.APIRequest, name: str, params: GenericJSONDict) -> GenericJSONDict:
    core_api_schema.validate(params, api_schema.PATCH_DISCOVERED_DEVICE)

    discovered_devices = slaves_discover.get_discovered_devices() or {}
    discovered_device = discovered_devices.get(name)
    if not discovered_device:
        raise core_api.APIError(404, 'no-such-device')

    attrs = params['attrs']
    try:
        discovered_device = await slaves_discover.configure(discovered_device, attrs)

    except Exception as e:
        raise slaves_exceptions.adapt_api_error(e) from e

    return discovered_device.to_json()
