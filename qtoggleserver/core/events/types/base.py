
import abc
import logging

from qtoggleserver.core import api as core_api


logger = logging.getLogger(__package__)


class Event(metaclass=abc.ABCMeta):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_NONE
    TYPE = 'base-event'

    def __init__(self):
        self._type = self.TYPE

    def __str__(self):
        return '{} event'.format(self._type)

    async def to_json(self):
        return {
            'type': self._type,
            'params': await self.get_params()
        }

    async def get_params(self):
        return {}

    def get_type(self):
        return self._type

    def is_duplicate(self, event):
        return False
