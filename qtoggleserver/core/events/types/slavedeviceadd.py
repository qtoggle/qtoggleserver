
from qtoggleserver.core import api as core_api

from .base import Event


class SlaveDeviceAdd(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = 'slave-device-add'

    def __init__(self, slave):
        self.slave = slave

        super().__init__(slave.to_json)

    def __str__(self):
        return '{}({}) event'.format(self._type, self.slave.get_name())

    def get_handler_args(self):
        return self.slave,
