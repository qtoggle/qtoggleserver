import asyncio
import logging

from typing import Any, Iterable, Optional

from qtoggleserver import persist
from qtoggleserver.conf import settings
from qtoggleserver.core import ports
from qtoggleserver.core.typing import GenericJSONDict
from qtoggleserver.utils import dynload as dynload_utils


logger = logging.getLogger(__name__)

from .peripheral import Peripheral
from .peripheralport import PeripheralPort


_registered_peripherals: dict[str, tuple[Peripheral, GenericJSONDict]] = {}


class PeripheralException(Exception):
    pass


class NoSuchDriver(PeripheralException):
    pass


def get_all() -> list[Peripheral]:
    return [v[0] for v in _registered_peripherals.values()]


def get_all_with_args() -> list[tuple[Peripheral, GenericJSONDict]]:
    return [(v[0], dict(v[1], id=v[0].get_id())) for v in _registered_peripherals.values()]


def get(peripheral_id: str) -> Optional[Peripheral]:
    result = _registered_peripherals.get(peripheral_id)
    if not result:
        return

    p, _ = result
    return p


def get_args(peripheral_id: str) -> Optional[dict]:
    result = _registered_peripherals.get(peripheral_id)
    if not result:
        return

    _, args = result
    return args


async def add(peripheral_args: dict[str, Any], static: bool = False) -> Peripheral:
    if not static:
        if not (peripheral_args.get('name') or peripheral_args.get('internal_id')):
            raise ValueError('Dynamic peripherals must have either name or internal_id set')

    args = dict(peripheral_args)
    class_path = args.pop('driver')

    logger.debug('loading peripheral %s', class_path)
    try:
        peripheral_class = dynload_utils.load_attr(class_path)
    except Exception:
        raise NoSuchDriver(class_path)
    p = peripheral_class(**args)
    p.debug('initializing')
    await p.handle_init()
    _registered_peripherals[p.get_id()] = p, dict(peripheral_args, static=static)

    if not static:
        await persist.replace('peripherals', p.get_id(), peripheral_args)

    return p


async def remove(peripheral_id: str) -> None:
    p, args = _registered_peripherals[peripheral_id]

    p.debug('cleaning up')
    await p.handle_cleanup()
    _registered_peripherals.pop(peripheral_id)

    logger.debug('peripheral %s removed', peripheral_id)

    if not args.get('static'):
        await persist.remove('peripherals', filt={'id': peripheral_id})


async def init_ports(peripheral: Peripheral) -> None:
    port_args = await peripheral.get_port_args()
    loaded_ports = await ports.load(port_args)
    peripheral.set_ports(loaded_ports)


async def cleanup_ports(peripheral: Peripheral, persisted_data: bool) -> None:
    tasks = [asyncio.create_task(port.remove(persisted_data=persisted_data)) for port in peripheral.get_ports()]
    if tasks:
        await asyncio.wait(tasks)


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
