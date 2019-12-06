
import abc
import logging

from qtoggleserver import utils
from qtoggleserver.conf import settings


STATUS_IDLE = 'idle'
STATUS_CHECKING = 'checking'
STATUS_DOWNLOADING = 'downloading'
STATUS_EXTRACTING = 'extracting'
STATUS_VALIDATING = 'validating'
STATUS_FLASHING = 'flashing'
STATUS_RESTARTING = 'restarting'
STATUS_ERROR = 'error'


logger = logging.getLogger(__name__)

_fwupdate = None


class FWUpdateException(Exception):
    pass


class FWUpdateDisabled(FWUpdateException):
    pass


class BaseDriver(metaclass=abc.ABCMeta):
    def __init__(self):
        pass

    @abc.abstractmethod
    def get_current_version(self):
        pass

    @abc.abstractmethod
    def get_latest(self):
        pass

    @abc.abstractmethod
    def get_status(self):
        return STATUS_IDLE

    @abc.abstractmethod
    def update_to_version(self, version):
        pass

    @abc.abstractmethod
    def update_to_url(self, url):
        pass


def _get_fwupdate():
    global _fwupdate

    if not settings.system.fwupdate_driver:
        raise FWUpdateDisabled()

    if _fwupdate is None:
        logger.debug('initializing fwupdate')

        cls = utils.load_attr(settings.system.fwupdate_driver)
        _fwupdate = cls()

    return _fwupdate


async def get_current_version():
    current_version = await _get_fwupdate().get_current_version()
    logger.debug('current version: %s', current_version)

    return current_version


async def get_latest():
    latest_version, latest_date, latest_url = await _get_fwupdate().get_latest()
    logger.debug('latest version: %s/%s at %s', latest_version, latest_date, latest_url)

    return latest_version, latest_date, latest_url


async def get_status():
    status = await _get_fwupdate().get_status()
    logger.debug('status: %s', status)

    return status


async def update_to_version(version):
    logger.debug('updating to version %s', version)

    await _get_fwupdate().update_to_version(version)


async def update_to_url(url):
    logger.debug('updating to url %s', url)

    await _get_fwupdate().update_to_url(url)
