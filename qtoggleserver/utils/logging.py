
import logging.handlers

from typing import Optional


class FifoMemoryHandler(logging.handlers.MemoryHandler):
    def __init__(self, capacity: int) -> None:
        super().__init__(capacity, flushLevel=logging.FATAL + 1)

    def flush(self) -> None:
        self.acquire()

        while len(self.buffer) > self.capacity:
            self.buffer.pop(0)

        self.release()


class LoggableMixin:
    def __init__(self, name: Optional[str], parent_logger: logging.Logger) -> None:
        if name:
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
