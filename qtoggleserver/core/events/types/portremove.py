
from qtoggleserver.core import api as core_api

from .base import Event


class PortRemove(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY
    TYPE = 'port-remove'

    def __init__(self, port):
        self.port = port

        super().__init__({'id': port.get_id()})

    def __str__(self):
        return '{}({}) event'.format(self._type, self.port.get_id())

    def get_handler_args(self):
        return self.port,
