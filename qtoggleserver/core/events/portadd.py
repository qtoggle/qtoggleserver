
from qtoggleserver.core import api as core_api

from .base import Event


class PortAdd(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY
    TYPE = 'port-add'

    def __init__(self, port):
        self.port = port

        super().__init__(port.to_json)

    def __str__(self):
        return '{}({}) event'.format(self._type, self.port.get_id())
