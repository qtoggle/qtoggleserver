
import logging
import os

from qtoggleserver.conf import settings

from . import date
from . import fwupdate
from . import net


logger = logging.getLogger(__name__)


def reboot():
    logger.debug('rebooting')
    if not settings.debug:
        os.system('reboot')


def uptime():
    with open('/proc/uptime', 'r') as f:
        line = f.readlines()[0]
        return int(float(line.split()[0]))
