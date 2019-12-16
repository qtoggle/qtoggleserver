
from qtoggleserver.core import api as core_api
from qtoggleserver.core.device import attrs as core_device_attrs

from .base import Event


class DeviceUpdate(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN

    def is_duplicate(self, event):
        return isinstance(event, self.__class__)

    def __init__(self):
        super().__init__('device-update', core_device_attrs.to_json)
