import asyncio
import logging

from typing import Any, Iterable

from qtoggleserver import persist
from qtoggleserver.conf import settings
from qtoggleserver.utils import dynload as dynload_utils


logger = logging.getLogger(__name__)

from .peripheral import Peripheral
from .peripheralport import PeripheralPort


_registered_peripherals: dict[str, tuple[Peripheral, bool]] = {}


def all_peripherals() -> Iterable[Peripheral]:
    return (v[0] for v in _registered_peripherals.values())


async def add(peripheral_args: dict[str, Any], static: bool = False) -> Peripheral:
    if not static:
        if not (peripheral_args.get('name') or peripheral_args.get('internal_id')):
            raise ValueError('Dynamic peripherals must have either name or internal_id set')

    args = dict(peripheral_args)
    class_path = args.pop('driver')

    logger.debug('loading peripheral %s', class_path)
    peripheral_class = dynload_utils.load_attr(class_path)
    p = peripheral_class(**args)
    p.debug('initializing')
    await p.handle_init()
    _registered_peripherals[p.get_id()] = p, static

    if not static:
        await persist.replace('peripherals', p.get_id(), peripheral_args)

    return p


async def remove(peripheral_id: str) -> None:
    p, static = _registered_peripherals[peripheral_id]
    p.debug('cleaning up')
    await p.handle_cleanup()
    _registered_peripherals.pop(peripheral_id)
    logger.debug('peripheral %s removed', peripheral_id)

    if not static:
        await persist.remove('peripherals', filt={'id': peripheral_id})


async def init() -> None:
    logger.debug('loading static peripherals')
    for peripheral_args in settings.peripherals:
        try:
            await add(peripheral_args, static=True)
        except Exception:
            logger.error('failed to load peripheral %s', peripheral_args.get('driver'), exc_info=True)

    logger.debug('loading dynamic peripherals')
    for peripheral_args in await persist.query('peripherals'):
        try:
            await add(peripheral_args)
        except Exception:
            logger.error('failed to load peripheral %s', peripheral_args.get('driver'), exc_info=True)


async def cleanup() -> None:
    tasks = [asyncio.create_task(remove(p_id)) for p_id in _registered_peripherals.keys()]
    if tasks:
        await asyncio.wait(tasks)
