
import logging

from qtoggleserver import persist


logger = logging.getLogger(__name__)


def reset() -> None:
    logger.debug('clearing slaves persisted data')
    persist.remove('slaves')
    persist.remove('slave_ports')
