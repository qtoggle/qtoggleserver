
import logging

from qtoggleserver import persist

from . import devices as slaves_devices
from . import discover


logger = logging.getLogger(__name__)


def reset() -> None:
    logger.debug('clearing slaves persisted data')
    persist.remove('slaves')
    persist.remove('slave_ports')


async def init() -> None:
    logger.debug('loading devices')
    await slaves_devices.load()

    logger.debug('initializing discover mechanism')
    await discover.init()


async def cleanup() -> None:
    logger.debug('cleaning up discover mechanism')
    await discover.cleanup()

    logger.debug('cleaning up devices')
    await slaves_devices.cleanup()
