import asyncio
import logging

from collections.abc import ValuesView
from typing import Any

from qtoggleserver import persist
from qtoggleserver.conf import settings
from qtoggleserver.utils import dynload as dynload_utils

from .exceptions import DuplicatePeripheral, NoSuchDriver
from .peripheral import Peripheral
from .peripheralport import PeripheralPort


__all__ = ["Peripheral", "PeripheralPort"]


logger = logging.getLogger(__name__)

_registered_peripherals: dict[str, Peripheral] = {}


def get_all() -> ValuesView[Peripheral]:
    return _registered_peripherals.values()


def get(peripheral_id: str) -> Peripheral | None:
    return _registered_peripherals.get(peripheral_id)


async def add(peripheral_args: dict[str, Any], static: bool = False, persisted_data: bool = True) -> Peripheral:
    peripheral_args = peripheral_args.copy()
    class_path = peripheral_args["driver"]

    # Merge params into peripheral args
    params = peripheral_args.pop("params", {})
    peripheral_args.update(params)

    logger.debug('creating peripheral with driver "%s"', class_path)
    try:
        peripheral_class = dynload_utils.load_attr(class_path)
    except Exception:
        raise NoSuchDriver(class_path) from None

    p: Peripheral = peripheral_class(static=static, **peripheral_args)
    if p.get_id() in _registered_peripherals:
        raise DuplicatePeripheral(f"Peripheral {p.get_id()} already exists")

    p.debug("initializing")
    await p.handle_init()
    _registered_peripherals[p.get_id()] = p

    if not static and persisted_data:
        persist_data = p.to_persisted()
        await persist.replace("peripherals", p.get_id(), persist_data)

    return p


async def remove(peripheral_id: str, persisted_data: bool = True) -> None:
    p = _registered_peripherals[peripheral_id]

    p.debug("cleaning up")
    await p.handle_cleanup()
    _registered_peripherals.pop(peripheral_id)

    logger.debug("peripheral %s removed", peripheral_id)

    if persisted_data:
        await persist.remove("peripherals", filt={"id": peripheral_id})


async def update(p: Peripheral) -> None:
    """Update the persisted state of an existing peripheral (non-static)."""
    if p.is_static():
        return

    persist_data = p.to_persisted()
    await persist.replace("peripherals", p.get_id(), persist_data)


async def migrate_on_change(p: Peripheral, new_name: str | None, new_params: dict[str, Any]) -> None:
    """Migrate persisted data when a peripheral undergoes a structural change that causes ID change.

    This handles:
    - Name changes for named peripherals (ID is the name)
    - Param changes for unnamed peripherals (ID is derived from params hash)

    Migrates port persisted data to new IDs and removes orphaned peripheral persist entry.
    """
    # Import here to avoid circular dependency
    from qtoggleserver.core.ports import BasePort

    # Determine if the peripheral ID will change
    will_id_change = False
    if p.get_name() is not None:
        # Named peripheral - ID changes only if name changes
        will_id_change = p.get_name() != new_name
    else:
        # Unnamed peripheral - ID is based on params hash, check if params changed
        old_params = p.get_params()
        will_id_change = old_params != new_params

    # Migrate port persisted data if peripheral will have a new ID
    if will_id_change:
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


async def init() -> None:
    logger.debug("loading static peripherals")
    for peripheral_args in settings.peripherals:
        try:
            await add(peripheral_args, static=True, persisted_data=False)
        except Exception:
            logger.error("failed to load peripheral %s", peripheral_args.get("driver"), exc_info=True)

    logger.debug("loading dynamic peripherals")
    for peripheral_args in await persist.query("peripherals"):
        try:
            await add(peripheral_args, persisted_data=False)
        except Exception:
            logger.error("failed to load peripheral %s", peripheral_args.get("driver"), exc_info=True)


async def cleanup() -> None:
    tasks = [asyncio.create_task(remove(p_id, persisted_data=False)) for p_id in _registered_peripherals.keys()]
    if tasks:
        await asyncio.wait(tasks)
