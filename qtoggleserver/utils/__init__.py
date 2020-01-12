
import asyncio
import logging
import sys

from typing import Any, Callable, Optional


# TODO move these to modules

class ConfigurableMixin:
    @classmethod
    def configure(cls, **kwargs) -> None:
        for name, value in kwargs.items():
            conf_method = getattr(cls, f'configure_{name.lower()}', None)
            if conf_method:
                conf_method(value)

            else:
                setattr(cls, name.upper(), value)


class LoggableMixin:
    def __init__(self, name: Optional[str], parent_logger: Optional[logging.Logger] = None) -> None:
        if parent_logger and name:
            name = f'{parent_logger.name}.{name}'

        else:
            name = parent_logger.name

        self._parent_logger: logging.Logger = parent_logger
        self._logger: logging.Logger = logging.getLogger(name)

    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        self._logger.log(level, msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs) -> None:
        self.log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        self.log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self.log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self.log(logging.ERROR, msg, *args, **kwargs)

    def set_logger_name(self, name: str) -> None:
        if name:
            self._logger = logging.getLogger(f'{self._parent_logger.name}.{name}')

        else:
            self._logger = self._parent_logger


def load_attr(attr_path: str) -> Any:
    m, attr = attr_path.rsplit('.', 1)

    try:
        __import__(m)
        mod = sys.modules[m]

    except ImportError as e:
        raise Exception(f'Error importing {attr_path}: {e}') from e

    try:
        attr = getattr(mod, attr)

    except AttributeError as e:
        raise Exception(f'Error importing {attr_path}: {e}') from e

    return attr


async def await_later(delay: float, coroutine: Callable, *args, loop: asyncio.AbstractEventLoop = None) -> None:
    await asyncio.sleep(delay, loop=loop)
    await coroutine(*args)
