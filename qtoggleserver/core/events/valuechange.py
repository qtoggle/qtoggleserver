
from qtoggleserver.core import api as core_api

from .base import Event


class ValueChange(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY

    def __init__(self, port):
        self.port = port

        super().__init__('value-change', {
            'id': port.get_id(),
            'value': port.get_value()
        })

    def find_duplicate(self, events):
        for e in events:
            if isinstance(e, self.__class__) and e.port == self.port:
                return e

    def __str__(self):
        return '{}({}) event'.format(self._type, self.port.get_id())
