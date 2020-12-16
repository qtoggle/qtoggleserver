
import logging

from qtoggleserver import persist

from . import devices as slaves_devices
from . import ports as slaves_ports
from . import discover


logger = logging.getLogger(__name__)


async def reset_ports() -> None:
    logger.debug('clearing slave ports persisted data')
    await persist.remove(slaves_ports.SlavePort.PERSIST_COLLECTION)


async def reset_slaves() -> None:
    logger.debug('clearing slaves persisted data')
    await persist.remove('slaves')


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
