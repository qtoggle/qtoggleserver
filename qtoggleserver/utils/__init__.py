
import asyncio
import logging
import sys


# TODO move these to modules

class ConfigurableMixin:
    @classmethod
    def configure(cls, **kwargs):
        for name, value in kwargs.items():
            conf_method = getattr(cls, 'configure_{}'.format(name.lower()), None)
            if conf_method:
                conf_method(value)

            else:
                setattr(cls, name.upper(), value)


class LoggableMixin:
    def __init__(self, name, parent_logger=None):
        if parent_logger and name:
            name = '{}.{}'.format(parent_logger.name, name)

        else:
            name = parent_logger.name

        self._parent_logger = parent_logger
        self._logger = logging.getLogger(name)

    def log(self, level, msg, *args, **kwargs):
        self._logger.log(level, msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.log(logging.ERROR, msg, *args, **kwargs)

    def set_logger_name(self, name):
        if name:
            self._logger = logging.getLogger('{}.{}'.format(self._parent_logger.name, name))

        else:
            self._logger = self._parent_logger


def load_attr(attr_path):
    m, attr = attr_path.rsplit('.', 1)

    try:
        __import__(m)
        mod = sys.modules[m]

    except ImportError as e:
        raise Exception('Error importing {}: {}'.format(attr_path, e)) from e

    try:
        attr = getattr(mod, attr)

    except AttributeError as e:
        raise Exception('Error importing {}: {}'.format(attr_path, e)) from e

    return attr


async def await_later(delay, coro, *args, loop=None):
    await asyncio.sleep(delay, loop=loop)
    await coro(*args)
