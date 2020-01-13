
import logging

from typing import Optional


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
