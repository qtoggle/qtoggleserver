
import logging
import os

import psutil

from qtoggleserver.conf import settings

from . import battery
from . import date
from . import fwupdate
from . import net
from . import storage
from . import temperature


logger = logging.getLogger(__name__)


def reboot() -> None:
    logger.debug('rebooting')
    if not settings.debug:
        os.system('reboot')


def uptime() -> int:
    with open('/proc/uptime', 'r') as f:
        line = f.readlines()[0]
        return int(float(line.split()[0]))


def get_cpu_usage() -> int:
    return int(psutil.cpu_percent())


def get_mem_usage() -> int:
    vm = psutil.virtual_memory()
    return int(100 * (1 - vm.available / vm.total))
