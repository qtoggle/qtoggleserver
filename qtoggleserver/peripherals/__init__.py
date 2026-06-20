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


async def add(peripheral_args: dict[str, Any], static: bool = False) -> Peripheral:
    peripheral_args = peripheral_args.copy()
    class_path = peripheral_args["driver"]

    # Merge params into peripheral args
    params = peripheral_args.pop("params", {})
    peripheral_args.update(params)

    logger.debug('creating peripheral with driver "%s"', class_path)
    try:
        peripheral_class = dynload_utils.load_attr(class_path)
    except Exception:
        raise NoSuchDriver(class_path)

    p: Peripheral = peripheral_class(static=static, **peripheral_args)
    if p.get_id() in _registered_peripherals:
        raise DuplicatePeripheral(f"Peripheral {p.get_id()} already exists")

    p.debug("initializing")
    await p.handle_init()
    _registered_peripherals[p.get_id()] = p

    if not static:
        persist_data = {
            "driver": p.get_driver(),
            "name": p.get_name(),
            "display_name": p.get_display_name(),
            "force_enabled": p.get_force_enabled(),
            "params": p.get_params(),
        }
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


async def init() -> None:
    logger.debug("loading static peripherals")
    for peripheral_args in settings.peripherals:
        try:
            await add(peripheral_args, static=True)
        except Exception:
            logger.error("failed to load peripheral %s", peripheral_args.get("driver"), exc_info=True)

    logger.debug("loading dynamic peripherals")
    for peripheral_args in await persist.query("peripherals"):
        try:
            await add(peripheral_args)
        except Exception:
            logger.error("failed to load peripheral %s", peripheral_args.get("driver"), exc_info=True)


async def cleanup() -> None:
    tasks = [asyncio.create_task(remove(p_id, persisted_data=False)) for p_id in _registered_peripherals.keys()]
    if tasks:
        await asyncio.wait(tasks)
