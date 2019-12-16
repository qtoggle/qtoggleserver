
from qtoggleserver.core import api as core_api

from .base import Event


class PortUpdate(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY

    def __init__(self, port):
        self.port = port

        super().__init__('port-update', port.to_json)

    def is_duplicate(self, event):
        return isinstance(event, self.__class__) and event.port == self.port

    def __str__(self):
        return '{}({}) event'.format(self._type, self.port.get_id())
