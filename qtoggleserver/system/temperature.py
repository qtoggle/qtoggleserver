
from typing import Optional

import psutil

from qtoggleserver.conf import settings
from qtoggleserver.utils.cmd import run_get_cmd


class TemperatureError(Exception):
    pass


def has_temperature_support() -> bool:
    return bool(settings.system.temperature.sensor_name) or bool(settings.system.temperature.get_cmd)


def get_temperature() -> Optional[int]:
    if settings.system.temperature.get_cmd:
        return int(run_get_cmd(
            settings.system.temperature.get_cmd,
            cmd_name='temperature',
            exc_class=TemperatureError,
            required_fields=['value']
        )['value'])

    if settings.system.temperature.sensor_name:
        temperatures = psutil.sensors_temperatures()
        temp_info_list = temperatures[settings.system.temperature.sensor_name]
        temp_info = temp_info_list[settings.system.temperature.sensor_index]

        return int(temp_info.current)
