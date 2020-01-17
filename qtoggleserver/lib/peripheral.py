
from __future__ import annotations

import abc
import asyncio
import functools
import logging
import queue
import threading

from typing import Any, Callable, Dict, List, Optional

from qtoggleserver.core import ports as core_ports
from qtoggleserver.utils import conf as conf_utils
from qtoggleserver.utils import logging as logging_utils

from . import add_cleanup_hook


logger = logging.getLogger(__name__)


class RunnerBusy(Exception):
    pass


class ThreadedRunner(threading.Thread, metaclass=abc.ABCMeta):
    QUEUE_TIMEOUT = 1

    def __init__(self, queue_size: Optional[int] = None) -> None:
        self._running: bool = False
        self._loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self._queue: queue.Queue = queue.Queue(queue_size or 0)
        self._queue_size: int = queue_size
        self._stopped_future: asyncio.Future = self._loop.create_future()

        super().__init__()

    def run(self) -> None:
        while self._running:
            try:
                func, callback = self._queue.get(timeout=self.QUEUE_TIMEOUT)

            except queue.Empty:
                continue

            try:
                result = func()

            except Exception as e:
                self._loop.call_soon_threadsafe(callback, None, e)

            else:
                self._loop.call_soon_threadsafe(callback, result, None)

        self._loop.call_soon_threadsafe(self._stopped_future.set_result, None)

    def schedule_func(self, func: Callable, callback: Callable) -> None:
        try:
            self._queue.put_nowait((func, callback))

        except queue.Full:
            raise RunnerBusy() from None

    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        self._running = True
        super().start()

    async def stop(self) -> None:
        self._running = False

        await self._stopped_future


class Peripheral(conf_utils.ConfigurableMixin, logging_utils.LoggableMixin, metaclass=abc.ABCMeta):
    RUNNER_CLASS = ThreadedRunner
    RUNNER_QUEUE_SIZE = 8

    logger = logger
    _peripherals_by_address: Dict[str, Peripheral] = {}

    @classmethod
    def get(cls, address: str, name: str, **kwargs) -> Peripheral:
        if name is None:
            name = ''

        if address not in cls._peripherals_by_address:
            logger.debug('initializing peripheral %s(%s@%s)', cls.__name__, name, address)
            peripheral = cls.make_peripheral(address, name, **kwargs)
            cls._peripherals_by_address[address] = peripheral

        return cls._peripherals_by_address[address]

    @classmethod
    def make_peripheral(cls, address: str, name: str, **kwargs) -> Peripheral:
        return cls(address, name, **kwargs)

    def __init__(self, address: str, name: str, **kwargs) -> None:
        logging_utils.LoggableMixin.__init__(self, name, self.logger)

        self._address = address
        self._name = name
        self._ports = []
        self._enabled = False
        self._online = False
        self._runner = None

        add_cleanup_hook(self.handle_cleanup)

    def __str__(self) -> str:
        return self._name

    def get_address(self) -> str:
        return self._address

    def get_name(self) -> str:
        return self._name

    def add_port(self, port: core_ports.BasePort) -> None:
        self._ports.append(port)

    def get_ports(self) -> List[core_ports.BasePort]:
        return list(self._ports)

    def is_enabled(self) -> bool:
        return self._enabled

    async def enable(self) -> None:
        if self._enabled:
            return

        self._enabled = True
        await self.handle_enable()
        self.debug('peripheral enabled')

    async def disable(self) -> None:
        if not self._enabled:
            return

        self._enabled = False
        await self.handle_disable()
        self.debug('peripheral disabled')

    async def check_disabled(self, exclude_port: Optional[core_ports.BasePort] = None) -> None:
        if not self._enabled:
            return

        for port in self._ports:
            if port.is_enabled() and port != exclude_port:
                break

        else:
            self.debug('all ports are disabled, disabling peripheral')
            await self.disable()

    def is_online(self) -> bool:
        return self._enabled and self._online

    def set_online(self, online: bool) -> None:
        if online and not self._online:
            self.debug('is online')
            self.handle_online()

        elif not online and self._online:
            self.debug('is offline')
            self.handle_offline()

        self._online = online

    def handle_offline(self) -> None:
        self.trigger_port_update()

    def handle_online(self) -> None:
        self.trigger_port_update()

    def trigger_port_update(self) -> None:
        for port in self._ports:
            if port.is_enabled():
                port.trigger_update()

    def get_runner(self) -> ThreadedRunner:
        if self._runner is None:
            self._runner = self.make_runner()

        return self._runner

    def make_runner(self) -> ThreadedRunner:
        self.debug('starting threaded runner')
        runner = self.RUNNER_CLASS(queue_size=self.RUNNER_QUEUE_SIZE)
        runner.start()

        return runner

    async def run_threaded(self, func: Callable, *args, **kwargs) -> Any:
        future = asyncio.get_running_loop().create_future()

        def callback(result: Any, exception: Optional[Exception]) -> None:
            if exception:
                future.set_exception(exception)

            else:
                future.set_result(result)

        runner = self.get_runner()
        runner.schedule_func(functools.partial(func, *args, **kwargs), callback)

        return await future

    async def handle_enable(self) -> None:
        pass

    async def handle_disable(self) -> None:
        pass

    async def handle_cleanup(self) -> None:
        if self._runner:
            self.debug('stopping threaded runner')
            await self._runner.stop()
            self.debug('threaded runner stopped')


class PeripheralPort(core_ports.Port, metaclass=abc.ABCMeta):
    PERIPHERAL_CLASS = Peripheral
    ID = 'port'

    ADDITIONAL_ATTRDEFS = {
        'address': {
            'display_name': 'Address',
            'description': 'The peripheral address.',
            'type': 'string',
            'modifiable': False
        }
    }

    def __init__(self, address: str, peripheral_name: Optional[str] = None, **kwargs) -> None:
        self._peripheral: Peripheral = self.PERIPHERAL_CLASS.get(address, peripheral_name, **kwargs)
        self._peripheral.add_port(self)

        _id = self.make_id()
        if self._peripheral.get_name():
            _id = f'{self._peripheral.get_name()}.{_id}'

        super().__init__(_id)

    def make_id(self) -> str:
        return self.ID

    def get_peripheral(self) -> Peripheral:
        return self._peripheral

    async def attr_get_address(self) -> str:
        return self._peripheral.get_address()

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
