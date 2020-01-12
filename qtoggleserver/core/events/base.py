
from __future__ import annotations

import abc
import logging
import time

from qtoggleserver.core import api as core_api
from qtoggleserver.core.typing import GenericJSONDict


logger = logging.getLogger(__package__)


class Event(metaclass=abc.ABCMeta):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_NONE
    TYPE = 'base-event'

    def __init__(self, timestamp: float = None) -> None:
        self._type: str = self.TYPE
        self._timestamp: float = timestamp or time.time()

    def __str__(self) -> str:
        return f'{self._type} event'

    async def to_json(self) -> GenericJSONDict:
        return {
            'type': self._type,
            'params': await self.get_params()
        }

    async def get_params(self) -> GenericJSONDict:
        return {}

    def get_type(self) -> str:
        return self._type

    def get_timestamp(self) -> float:
        return self._timestamp

    def is_duplicate(self, event: Event) -> bool:
        return False


class Handler(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def handle_event(self, event: Event) -> None:
        raise NotImplementedError()

    async def cleanup(self) -> None:
        pass
