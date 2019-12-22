
import abc
import asyncio
import functools
import queue
import logging
import threading

from qtoggleserver import utils
from qtoggleserver.core import ports as core_ports

from . import add_cleanup_hook


logger = logging.getLogger(__name__)


class RunnerBusy(Exception):
    pass


class ThreadedRunner(threading.Thread, metaclass=abc.ABCMeta):
    QUEUE_TIMEOUT = 1

    def __init__(self, queue_size=None):
        self._running = False
        self._loop = asyncio.get_event_loop()
        self._queue = queue.Queue(queue_size or 0)
        self._queue_size = queue_size
        self._stopped_future = self._loop.create_future()

        super().__init__()

    def run(self):
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

    def schedule_func(self, func, callback):
        try:
            self._queue.put_nowait((func, callback))

        except queue.Full:
            raise RunnerBusy() from None

    def is_running(self):
        return self._running

    def start(self):
        self._running = True
        super().start()

    def stop(self):
        self._running = False

        return self._stopped_future


class Peripheral(utils.ConfigurableMixin, utils.LoggableMixin, metaclass=abc.ABCMeta):
    RUNNER_CLASS = ThreadedRunner
    RUNNER_QUEUE_SIZE = 8

    logger = logger
    _peripherals_by_address = {}

    @classmethod
    def get(cls, address, name, **kwargs):
        if name is None:
            name = ''

        if address not in cls._peripherals_by_address:
            logger.debug('initializing peripheral %s(%s@%s)', cls.__name__, name, address)
            peripheral = cls.make_peripheral(address, name, **kwargs)
            cls._peripherals_by_address[address] = peripheral

        return cls._peripherals_by_address[address]

    @classmethod
    def make_peripheral(cls, address, name, **kwargs):
        return cls(address, name, **kwargs)

    def __init__(self, address, name, **kwargs):
        utils.LoggableMixin.__init__(self, name, self.logger)

        self._address = address
        self._name = name
        self._ports = []
        self._enabled = False
        self._runner = None

        add_cleanup_hook(self.handle_cleanup)

    def __str__(self):
        return self._name

    def get_address(self):
        return self._address

    def get_name(self):
        return self._name

    def add_port(self, port):
        self._ports.append(port)

    def get_ports(self):
        return list(self._ports)

    def trigger_port_update(self):
        for port in self._ports:
            port.trigger_update()

    def is_enabled(self):
        return self._enabled

    async def enable(self):
        if self._enabled:
            return

        self._enabled = True
        await self.handle_enable()
        self.debug('peripheral enabled')

    async def disable(self):
        if not self._enabled:
            return

        self._enabled = False
        await self.handle_disable()
        self.debug('peripheral disabled')

    async def check_disabled(self, exclude_port=None):
        if not self._enabled:
            return

        for port in self._ports:
            if port.is_enabled() and port != exclude_port:
                break

        else:
            self.debug('all ports are disabled, disabling peripheral')
            await self.disable()

    def get_runner(self):
        if self._runner is None:
            self._runner = self.make_runner()

        return self._runner

    def make_runner(self):
        self.debug('starting threaded runner')
        runner = self.RUNNER_CLASS(queue_size=self.RUNNER_QUEUE_SIZE)
        runner.start()

        return runner

    async def run_threaded(self, func, *args, **kwargs):
        future = asyncio.get_running_loop().create_future()

        def callback(result, exception):
            if exception:
                future.set_exception(exception)

            else:
                future.set_result(result)

        runner = self.get_runner()
        runner.schedule_func(functools.partial(func, *args, **kwargs), callback)

        return await future

    async def handle_enable(self):
        pass

    async def handle_disable(self):
        pass

    async def handle_cleanup(self):
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

    def __init__(self, address, peripheral_name=None, **kwargs):
        self._peripheral = self.PERIPHERAL_CLASS.get(address, peripheral_name, **kwargs)
        self._peripheral.add_port(self)

        _id = self.make_id()
        if self._peripheral.get_name():
            _id = '{}.{}'.format(self._peripheral.get_name(), _id)

        super().__init__(_id)

    def make_id(self):
        return self.ID

    def get_peripheral(self):
        return self._peripheral

    async def attr_get_address(self):
        return self._peripheral.get_address()

    async def handle_enable(self):
        if not self._peripheral.is_enabled():
            await self._peripheral.enable()

    async def handle_disable(self):
        if self._peripheral.is_enabled():
            await self._peripheral.check_disabled(self)
