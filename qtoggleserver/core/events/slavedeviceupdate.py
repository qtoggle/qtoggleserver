
from qtoggleserver.core import api as core_api

from .base import Event


class SlaveDeviceUpdate(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN

    def __init__(self, slave):
        self.slave = slave

        super().__init__('slave-device-update', slave.to_json())

    def find_duplicate(self, events):
        for e in events:
            if isinstance(e, SlaveDeviceUpdate) and e.slave == self.slave:
                return e

    def __str__(self):
        return '{}({}) event'.format(self._type, self.slave.get_name())
