from __future__ import annotations

import abc
import logging
import time

from typing import Optional

from qtoggleserver import system
from qtoggleserver.core import api as core_api
from qtoggleserver.core.typing import GenericJSONDict
from qtoggleserver.utils import logging as logging_utils


logger = logging.getLogger(__package__)


class Event(metaclass=abc.ABCMeta):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_NONE
    TYPE = 'base-event'
    _UNINITIALIZED = {}

    def __init__(self, timestamp: float = None) -> None:
        self._type: str = self.TYPE
        if timestamp is None:
            if system.date.has_real_date_time():
                timestamp = time.time()
            else:
                timestamp = 0

        self._timestamp: float = timestamp
        self._params: Optional[GenericJSONDict] = self._UNINITIALIZED

    def __str__(self) -> str:
        return f'{self._type} event'

    async def to_json(self) -> GenericJSONDict:
        if self._params is self._UNINITIALIZED:
            raise Exception('Parameters are uninitialized')

        result = {
            'type': self._type
        }

        if self._params:
            result['params'] = self._params

        return result

    async def init_params(self) -> None:
        self._params = await self.get_params()

    async def get_params(self) -> GenericJSONDict:
        return {}

    def get_type(self) -> str:
        return self._type

    def get_timestamp(self) -> float:
        return self._timestamp

    def is_duplicate(self, event: Event) -> bool:
        return False


class Handler(logging_utils.LoggableMixin, metaclass=abc.ABCMeta):
    FIRE_AND_FORGET = True

    logger = logger

    def __init__(self, name: Optional[str] = None) -> None:
        logging_utils.LoggableMixin.__init__(self, name, self.logger)

        self._name: Optional[str] = name

    def __str__(self) -> str:
        return f'event handler {self._name}'

    def get_id(self) -> str:
        return self._name or f'{self.__class__.__name__}({hex(id(self))})'

    @abc.abstractmethod
    async def handle_event(self, event: Event) -> None:
        raise NotImplementedError()

    async def cleanup(self) -> None:
        pass

    def is_fire_and_forget(self) -> bool:
        return self.FIRE_AND_FORGET
