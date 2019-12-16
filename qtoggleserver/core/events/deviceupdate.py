
from qtoggleserver.core import api as core_api
from qtoggleserver.core.device import attrs as core_device_attrs

from .base import Event


class DeviceUpdate(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = 'device-update'

    def __init__(self):
        self._attrs = core_device_attrs.to_json()

        super().__init__(self._attrs)

    def is_duplicate(self, event):
        return isinstance(event, self.__class__)

    def get_handler_args(self):
        return self._attrs,
