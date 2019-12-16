
from qtoggleserver.core import api as core_api

from .base import Event


class SlaveDeviceRemove(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = 'slave-device-remove'

    def __init__(self, name):
        self.name = name
        super().__init__({'name': name})

    def __str__(self):
        return '{}({}) event'.format(self._type, self.name)
