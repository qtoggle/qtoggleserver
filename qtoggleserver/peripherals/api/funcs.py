import logging

from qtoggleserver import peripherals
from qtoggleserver.core import api as core_api
from qtoggleserver.core.api import schema as core_api_schema
from qtoggleserver.core.typing import GenericJSONDict, GenericJSONList
from qtoggleserver.peripherals.api import schema as peripherals_api_schema


logger = logging.getLogger(__name__)


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def get_peripherals(request: core_api.APIRequest) -> GenericJSONList:
    return [p[1] for p in peripherals.get_all_with_args()]


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def post_peripherals(request: core_api.APIRequest, params: GenericJSONDict) -> GenericJSONDict:
    core_api_schema.validate(params, peripherals_api_schema.POST_PERIPHERALS)

    name = params.get('name')
    if name and peripherals.get(name):
        raise core_api.APIError(400, 'duplicate-peripheral')

    try:
        peripheral = await peripherals.add(params)
    except peripherals.NoSuchDriver:
        raise core_api.APIError(404, 'no-such-driver')
    except peripherals.DuplicatePeripheral:
        raise core_api.APIError(400, 'duplicate-peripheral')
    except Exception as e:
        raise core_api.APIError(400, 'invalid-request', details=str(e))

    try:
        await peripherals.init_ports(peripheral)
    except Exception:
        await peripherals.remove(peripheral.get_id())
        raise

    params = dict(params)
    params['id'] = peripheral.get_id()
    params['static'] = False
    return params


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def delete_peripheral(request: core_api.APIRequest, peripheral_id: str) -> None:
    args = peripherals.get_args(peripheral_id)
    p = peripherals.get(peripheral_id)
    if not args:
        raise core_api.APIError(404, 'no-such-peripheral')
    if args.get('static'):
        raise core_api.APIError(400, 'peripheral-not-removable')

    await peripherals.cleanup_ports(p, persisted_data=True)
    await peripherals.remove(peripheral_id, persisted_data=True)


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def put_peripherals(request: core_api.APIRequest, params: GenericJSONList) -> None:
    core_api_schema.validate(params, peripherals_api_schema.PUT_PERIPHERALS)

    logger.debug('restoring peripherals')

    for p, args in peripherals.get_all_with_args():
        if args.get('static'):
            continue
        await peripherals.cleanup_ports(p, persisted_data=True)
        await peripherals.remove(p.get_id(), persisted_data=True)

    peripheral_list = []
    for args in params:
        if args.get('static'):
            continue
        p = await peripherals.add(args)
        peripheral_list.append(p)

    for p in peripheral_list:
        await peripherals.init_ports(p)
