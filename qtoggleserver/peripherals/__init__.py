
import asyncio
import logging

from typing import Dict, Iterable

from qtoggleserver.conf import settings
from qtoggleserver.utils import dynload as dynload_utils

from .peripheral import Peripheral
from .peripheralport import PeripheralPort
from .threadedrunner import ThreadedRunner, RunnerBusy


logger = logging.getLogger(__name__)

_registered_peripherals: Dict[str, Peripheral] = {}


def all_peripherals() -> Iterable[Peripheral]:
    return _registered_peripherals.values()


async def init() -> None:
    for peripheral_args in settings.peripherals:
        peripheral_class_path = peripheral_args.pop('driver')

        try:
            logger.debug('loading peripheral %s', peripheral_class_path)
            peripheral_class = dynload_utils.load_attr(peripheral_class_path)
            peripheral = peripheral_class(**peripheral_args)

        except Exception as e:
            logger.error('failed to load peripheral %s: %s', peripheral_class_path, e, exc_info=True)

        else:
            peripheral.debug('initializing')
            await peripheral.handle_init()
            _registered_peripherals[peripheral.get_id()] = peripheral


async def cleanup() -> None:
    tasks = [peripheral.handle_cleanup() for peripheral in _registered_peripherals.values()]
    if tasks:
        await asyncio.wait(tasks)
