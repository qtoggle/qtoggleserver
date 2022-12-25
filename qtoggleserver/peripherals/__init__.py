import asyncio
import logging

from typing import Any, Optional

from qtoggleserver import persist
from qtoggleserver.conf import settings
from qtoggleserver.core import ports
from qtoggleserver.core.typing import GenericJSONDict
from qtoggleserver.utils import dynload as dynload_utils


logger = logging.getLogger(__name__)

from .peripheral import Peripheral
from .peripheralport import PeripheralPort


_registered_peripherals: dict[str, Peripheral] = {}


class PeripheralException(Exception):
    pass


class NoSuchDriver(PeripheralException):
    pass


class DuplicatePeripheral(PeripheralException):
    pass


def get_all() -> list[Peripheral]:
    return list(_registered_peripherals.values())


def get(peripheral_id: str) -> Optional[Peripheral]:
    return _registered_peripherals.get(peripheral_id)


async def add(peripheral_params: dict[str, Any], static: bool = False) -> Peripheral:
    params = dict(peripheral_params)
    class_path = params.pop('driver')
    params.pop('static', None)

    logger.debug('creating peripheral with driver "%s"', class_path)
    try:
        peripheral_class = dynload_utils.load_attr(class_path)
    except Exception:
        raise NoSuchDriver(class_path)

    p = peripheral_class(params=peripheral_params, static=static, **params)
    if p.get_id() in _registered_peripherals:
        raise DuplicatePeripheral(f'Peripheral {p.get_id()} already exists')

    p.debug('initializing')
    await p.handle_init()
    _registered_peripherals[p.get_id()] = p

    if not static:
        peripheral_params = dict(peripheral_params)
        peripheral_params.pop('static', None)
        await persist.replace('peripherals', p.get_id(), peripheral_params)

    return p


async def remove(peripheral_id: str, persisted_data: bool = True) -> None:
    p = _registered_peripherals[peripheral_id]

    p.debug('cleaning up')
    await p.handle_cleanup()
    _registered_peripherals.pop(peripheral_id)

    logger.debug('peripheral %s removed', peripheral_id)

    if persisted_data:
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
    for peripheral_params in settings.peripherals:
        try:
            await add(peripheral_params, static=True)
        except Exception:
            logger.error('failed to load peripheral %s', peripheral_params.get('driver'), exc_info=True)

    logger.debug('loading dynamic peripherals')
    for peripheral_params in await persist.query('peripherals'):
        try:
            await add(peripheral_params)
        except Exception:
            logger.error('failed to load peripheral %s', peripheral_params.get('driver'), exc_info=True)


async def cleanup() -> None:
    tasks = [asyncio.create_task(remove(p_id, persisted_data=False)) for p_id in _registered_peripherals.keys()]
    if tasks:
        await asyncio.wait(tasks)
