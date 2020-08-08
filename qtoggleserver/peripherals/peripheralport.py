
from __future__ import annotations

import abc

from typing import Optional

from qtoggleserver.core import ports as core_ports

from .peripheral import Peripheral


class PeripheralPort(core_ports.Port, metaclass=abc.ABCMeta):
    ID = 'port'

    def __init__(self, peripheral: Peripheral, id: Optional[str] = None) -> None:
        self._peripheral: Peripheral = peripheral
        self._initial_id: str = id or self.make_id()

        id_ = self._initial_id
        if self._peripheral.get_name():
            id_ = f'{self._peripheral.get_name()}.{id_}'

        super().__init__(id_)

    def make_id(self) -> str:
        return self.ID

    def get_initial_id(self) -> str:
        return self._initial_id

    def get_peripheral(self) -> Peripheral:
        return self._peripheral

    async def handle_enable(self) -> None:
        if not self._peripheral.is_enabled():
            await self._peripheral.enable()

    async def handle_disable(self) -> None:
        if self._peripheral.is_enabled():
            await self._peripheral.check_disabled(self)

    async def attr_is_online(self) -> bool:
        if not self.is_enabled():
            return False

        return self._peripheral.is_online()
