import abc
import asyncio
import functools
import hashlib
import inspect

from typing import Any, Callable, Optional, Union

from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.typing import GenericJSONDict
from qtoggleserver.utils import asyncio as asyncio_utils
from qtoggleserver.utils import logging as logging_utils

from . import logger


class Peripheral(logging_utils.LoggableMixin, metaclass=abc.ABCMeta):
    RUNNER_CLASS = asyncio_utils.ThreadedRunner
    RUNNER_QUEUE_SIZE = 64

    logger = logger

    def __init__(
        self,
        *,
        params: dict[str, Any],
        name: Optional[str] = None,
        id: Optional[str] = None,
        static: bool = False,
        **kwargs
    ) -> None:
        sorted_params = self._sorted_tuples_dict(params)
        auto_id_to_hash = f'{self.__class__.__module__}.{self.__class__.__name__}:{name}:{sorted_params}'
        auto_id = f'peripheral_{hashlib.sha256(auto_id_to_hash.encode()).hexdigest()[:8]}'

        self._params: dict[str, Any] = params
        self._name: Optional[str] = name
        self._id: str = name or id or auto_id  # name will always be used as id, if supplied
        self._static: bool = static

        self._ports: list[core_ports.BasePort] = []
        self._enabled: bool = False
        self._online: bool = False
        self._runner: Optional[asyncio_utils.ThreadedRunner] = None
        self._port_update_task: Optional[asyncio.Task] = None

        logging_utils.LoggableMixin.__init__(self, self.get_id(), self.logger)

    @staticmethod
    def _sorted_tuples_dict(params: dict[str, Any]) -> tuple:

        def dict_reorder(d: dict) -> tuple:
            return tuple((k, dict_reorder(v)) if isinstance(v, dict) else v for k, v in sorted(d.items()))

        return dict_reorder(params)

    def __str__(self) -> str:
        return f'peripheral {self.get_id()}'

    def get_id(self) -> str:
        return self._id

    def get_name(self) -> Optional[str]:
        return self._name

    def get_params(self) -> dict[str, Any]:
        return self._params

    def is_static(self) -> bool:
        return self._static

    def to_json(self) -> GenericJSONDict:
        return dict(self._params, id=self.get_id(), static=self.is_static(), name=self.get_name())

    async def get_port_args(self) -> list[dict[str, Any]]:
        port_args = self.make_port_args()
        # Compatibility shim for peripherals having non-awaitable make_port_args() method
        if inspect.isawaitable(port_args):
            port_args = await port_args

        # Transform port classes to dicts with drivers
        port_args = [
            {'driver': pa} if isinstance(pa, type) else pa
            for pa in port_args
        ]

        # Supply the peripheral argument
        for pa in port_args:
            pa.setdefault('peripheral', self)

        return port_args

    @abc.abstractmethod
    async def make_port_args(self) -> list[Union[dict[str, Any], type[core_ports.BasePort]]]:
        raise NotImplementedError()

    def set_ports(self, ports: list[core_ports.BasePort]) -> None:
        self._ports = ports

    def get_ports(self) -> list[core_ports.BasePort]:
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
            try:
                self.handle_online()
            except Exception:
                self.error('handle_online failed', exc_info=True)
        elif not online and self._online:
            self.debug('is offline')
            try:
                self.handle_offline()
            except Exception:
                self.error('handle_offline failed', exc_info=True)

        self._online = online

    def handle_offline(self) -> None:
        self.trigger_port_update_fire_and_forget()

    def handle_online(self) -> None:
        self.trigger_port_update_fire_and_forget()

    async def trigger_port_update(self, save: bool = False) -> None:
        self._port_update_task = None
        for port in self._ports:
            if port.is_enabled():
                await port.trigger_update()
                if save:
                    port.save_asap()

    def trigger_port_update_fire_and_forget(self, save: bool = False) -> None:
        if self._port_update_task:
            return  # already scheduled

        self._port_update_task = asyncio.create_task(self.trigger_port_update(save))

    def get_runner(self) -> asyncio_utils.ThreadedRunner:
        if self._runner is None:
            self._runner = self.make_runner()

        return self._runner

    def make_runner(self) -> asyncio_utils.ThreadedRunner:
        self.debug('starting threaded runner')
        runner = self.RUNNER_CLASS(queue_size=self.RUNNER_QUEUE_SIZE)
        runner.start()

        return runner

    async def run_threaded(self, func: Callable, *args, **kwargs) -> Any:
        future = asyncio.get_running_loop().create_future()

        def callback(result: Any, exception: Optional[Exception]) -> None:
            if future.cancelled():
                return

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

    async def handle_init(self) -> None:
        pass

    async def handle_cleanup(self) -> None:
        if self._port_update_task:
            await self._port_update_task

        if self._runner:
            self.debug('stopping threaded runner')
            await self._runner.stop()
            self.debug('threaded runner stopped')
