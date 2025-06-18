import logging
import os
import subprocess

import psutil

from qtoggleserver.conf import settings

from . import battery, conf, date, dns, fwupdate, net, storage, temperature


__all__ = [
    "battery",
    "conf",
    "date",
    "dns",
    "fwupdate",
    "net",
    "storage",
    "temperature",
]


logger = logging.getLogger(__name__)


def is_setup_mode() -> bool:
    if not settings.system.setup_mode_cmd:
        return False

    try:
        subprocess.check_call(settings.system.setup_mode_cmd, stderr=subprocess.STDOUT, shell=True)
        return True
    except subprocess.CalledProcessError:
        return False


def reboot() -> None:
    logger.debug("rebooting")
    if not settings.debug:
        os.system("reboot")


def uptime() -> int:
    with open("/proc/uptime") as f:
        line = f.readlines()[0]
        return int(float(line.split()[0]))


def get_cpu_usage() -> int:
    return int(psutil.cpu_percent())


def get_mem_usage() -> int:
    vm = psutil.virtual_memory()
    return int(100 * (1 - vm.available / vm.total))


async def init() -> None:
    logger.debug("initializing DNS")
    await dns.init()


async def cleanup() -> None:
    logger.debug("cleaning up DNS")
    await dns.cleanup()
