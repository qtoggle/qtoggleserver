
import logging

from typing import Optional

import psutil

from qtoggleserver.conf import settings
from qtoggleserver.utils.cmd import run_get_cmd


_has_sensors_battery = None

logger = logging.getLogger(__name__)


class BatteryError(Exception):
    pass


def has_battery_support() -> bool:
    global _has_sensors_battery

    if _has_sensors_battery is None:
        try:
            _ = psutil.sensors_battery().percent
            _has_sensors_battery = True
            logger.debug('battery sensor support detected')

        except AttributeError:
            _has_sensors_battery = False

    return _has_sensors_battery or bool(settings.system.battery.get_cmd)


def get_battery_level() -> Optional[int]:
    if settings.system.battery.get_cmd:
        return int(run_get_cmd(
            settings.system.battery.get_cmd,
            cmd_name='battery',
            exc_class=BatteryError,
            required_fields=['level']
        )['level'])

    if _has_sensors_battery:
        return int(psutil.sensors_battery().percent)
