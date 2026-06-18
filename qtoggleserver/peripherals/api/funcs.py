import logging

from qtoggleserver import peripherals, persist
from qtoggleserver.core import api as core_api
from qtoggleserver.core.api import schema as core_api_schema
from qtoggleserver.core.ports import BasePort
from qtoggleserver.core.typing import GenericJSONDict, GenericJSONList
from qtoggleserver.peripherals.api import schema as peripherals_api_schema


logger = logging.getLogger(__name__)


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def get_peripherals(request: core_api.APIRequest) -> GenericJSONList:
    return [p.to_json() for p in peripherals.get_all()]


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def post_peripherals(request: core_api.APIRequest, params: GenericJSONDict) -> GenericJSONDict:
    core_api_schema.validate(params, peripherals_api_schema.POST_PERIPHERALS)
    args = params.copy()
    args.setdefault("params", {})

    name = args.get("name")
    if name and peripherals.get(name):
        raise core_api.APIError(400, "duplicate-peripheral")

    try:
        peripheral = await peripherals.add(args)
    except peripherals.NoSuchDriver:
        raise core_api.APIError(404, "no-such-driver")
    except peripherals.DuplicatePeripheral:
        raise core_api.APIError(400, "duplicate-peripheral")
    except TypeError as e:
        if "arguments" in str(e):
            raise core_api.APIError(400, "invalid-field", field="params")
        else:
            raise core_api.APIError(400, "invalid-request", details=str(e))
    except Exception as e:
        raise core_api.APIError(400, "invalid-request", details=str(e))

    # Always trigger add event before initializing ports
    await peripheral.trigger_add()

    try:
        await peripheral.init_ports()
    except Exception as e:
        await peripherals.remove(peripheral.get_id())
        await peripheral.trigger_remove()
        raise core_api.APIError(400, "invalid-request", details=str(e))

    return peripheral.to_json()


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def delete_peripheral(request: core_api.APIRequest, peripheral_id: str) -> None:
    p = peripherals.get(peripheral_id)
    if not p:
        raise core_api.APIError(404, "no-such-peripheral")
    if p.is_static():
        raise core_api.APIError(400, "peripheral-not-removable")

    await p.cleanup_ports(persisted_data=True)
    await peripherals.remove(peripheral_id, persisted_data=True)
    await p.trigger_remove()


async def _restore_peripheral(old_args: GenericJSONDict) -> None:
    """Attempt to restore a peripheral from its saved args after a failed update."""
    peripheral_id = old_args.get("name") or old_args.get("id")
    logger.warning('restoring old peripheral "%s" after failed update', peripheral_id)
    try:
        old_p = await peripherals.add(old_args)
        await old_p.init_ports()
    except Exception:
        logger.critical('failed to restore old peripheral "%s"', peripheral_id, exc_info=True)


async def _migrate_peripheral_rename(p: peripherals.Peripheral, new_name: str | None) -> None:
    """Migrate port persisted data and remove the orphaned peripheral persist entry when a peripheral is renamed."""
    for port in p.get_ports():
        old_port_id = port.get_id()
        initial_id = port.get_initial_id()
        new_port_id = f"{new_name}.{initial_id}" if new_name else initial_id

        if old_port_id == new_port_id:
            continue

        logger.debug('migrating port persisted data from "%s" to "%s"', old_port_id, new_port_id)
        data = await persist.get(BasePort.PERSIST_COLLECTION, old_port_id)
        if data:
            await persist.replace(BasePort.PERSIST_COLLECTION, new_port_id, dict(data, id=new_port_id))
        await persist.remove(BasePort.PERSIST_COLLECTION, filt={"id": old_port_id})

    logger.debug('removing orphaned peripheral persist entry "%s"', p.get_id())
    await persist.remove("peripherals", filt={"id": p.get_id()})


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def patch_peripheral(
    request: core_api.APIRequest, peripheral_id: str, params: GenericJSONDict
) -> GenericJSONDict:
    core_api_schema.validate(params, peripherals_api_schema.PATCH_PERIPHERAL)

    p = peripherals.get(peripheral_id)
    if not p:
        raise core_api.APIError(404, "no-such-peripheral")
    if p.is_static():
        raise core_api.APIError(400, "peripheral-not-removable")

    # Check if any structural changes (driver, name, params, or force_enabled)
    old_driver = p.get_driver()
    old_name = p.get_name()
    old_params = p.get_params()
    old_force_enabled = p.get_force_enabled()
    new_driver = params.get("driver", old_driver)
    new_name = params.get("name", old_name)
    new_params = params.get("params", old_params)
    new_force_enabled = params.get("force_enabled", old_force_enabled)

    structural_change = (
        old_driver != new_driver
        or old_name != new_name
        or old_params != new_params
        or old_force_enabled != new_force_enabled
    )

    # Apply non-structural changes immediately
    if "display_name" in params:
        p.set_display_name(params["display_name"])

    # If only non-structural changes, return early
    if not structural_change:
        await p.trigger_update()
        return p.to_json()

    # For structural changes, perform full removal/re-add

    # Save old args for potential rollback if the new add fails
    old_args: GenericJSONDict = {
        "driver": p.get_driver(),
        "name": p.get_name(),
        "display_name": p.get_display_name(),
        "force_enabled": p.get_force_enabled(),
        "params": p.get_params().copy(),
    }

    args: GenericJSONDict = old_args.copy()
    args.update(params)
    args.setdefault("params", {})

    if old_name != new_name:
        logger.info('renaming peripheral "%s" to "%s"', old_name, new_name)
        await _migrate_peripheral_rename(p, new_name)

    await p.cleanup_ports(persisted_data=False)
    await peripherals.remove(peripheral_id, persisted_data=False)

    try:
        new_p = await peripherals.add(args)
    except Exception as e:
        await _restore_peripheral(old_args)
        if isinstance(e, peripherals.NoSuchDriver):
            raise core_api.APIError(404, "no-such-driver")
        if isinstance(e, peripherals.DuplicatePeripheral):
            raise core_api.APIError(400, "duplicate-peripheral")
        if isinstance(e, TypeError) and "arguments" in str(e):
            raise core_api.APIError(400, "invalid-field", field="params")
        raise core_api.APIError(400, "invalid-request", details=str(e))

    try:
        await new_p.init_ports()
    except Exception as e:
        logger.exception("failed to initialize ports for %s", new_p)
        new_p.set_force_enabled(False)
        await new_p.disable()
        raise core_api.APIError(400, "invalid-request", details=str(e))

    await new_p.trigger_update()
    return new_p.to_json()


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def put_peripherals(request: core_api.APIRequest, params: GenericJSONList) -> None:
    core_api_schema.validate(params, peripherals_api_schema.PUT_PERIPHERALS)

    logger.debug("restoring peripherals")

    for p in list(peripherals.get_all()):
        if p.is_static():
            continue
        await p.cleanup_ports(persisted_data=True)
        await peripherals.remove(p.get_id(), persisted_data=True)
        await p.trigger_remove()

    peripheral_list = []
    for args in params:
        args = args.copy()
        if args.pop("static", None):
            continue
        args.setdefault("params", {})
        p = await peripherals.add(args)
        peripheral_list.append(p)

    # First trigger add event, then init ports

    for p in peripheral_list:
        await p.trigger_add()

    for p in peripheral_list:
        try:
            await p.init_ports()
        except Exception:
            logger.exception("failed to initialize ports for %s", p)
            p.set_force_enabled(False)
            await p.disable()
