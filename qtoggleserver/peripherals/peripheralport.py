
from __future__ import annotations

import abc

from qtoggleserver.core import ports as core_ports

from .peripheral import Peripheral


class PeripheralPort(core_ports.Port, metaclass=abc.ABCMeta):
    ID = 'port'

    def __init__(self, peripheral: Peripheral) -> None:
        self._peripheral: Peripheral = peripheral

        _id = self.make_id()
        if self._peripheral.get_name():
            _id = f'{self._peripheral.get_name()}.{_id}'

        super().__init__(_id)

    def make_id(self) -> str:
        return self.ID

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
