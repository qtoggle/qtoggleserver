import asyncio
import logging

from typing import Any, Iterable

from qtoggleserver.conf import settings
from qtoggleserver.utils import dynload as dynload_utils


logger = logging.getLogger(__name__)

from .peripheral import Peripheral
from .peripheralport import PeripheralPort


_registered_peripherals: dict[str, Peripheral] = {}


def all_peripherals() -> Iterable[Peripheral]:
    return _registered_peripherals.values()


async def load(peripheral_args: dict[str, Any]) -> Peripheral:
    peripheral_args = dict(peripheral_args)
    peripheral_class_path = peripheral_args.pop('driver')

    logger.debug('loading peripheral %s', peripheral_class_path)
    peripheral_class = dynload_utils.load_attr(peripheral_class_path)
    p = peripheral_class(**peripheral_args)
    p.debug('initializing')
    await p.handle_init()
    _registered_peripherals[p.get_id()] = p

    return p


async def unload(peripheral: Peripheral) -> None:
    peripheral.debug('cleaning up')
    await peripheral.handle_cleanup()
    _registered_peripherals.pop(peripheral.get_id())
    logger.debug('peripheral %s unloaded', peripheral.get_id())


async def init() -> None:
    for peripheral_args in settings.peripherals:
        try:
            await load(peripheral_args)
        except Exception:
            logger.error('failed to load peripheral %s', peripheral_args.get('driver'), exc_info=True)


async def cleanup() -> None:
    tasks = [asyncio.create_task(unload(p)) for p in _registered_peripherals.values()]
    if tasks:
        await asyncio.wait(tasks)
