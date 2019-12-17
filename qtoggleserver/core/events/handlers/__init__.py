
import logging
import asyncio


from qtoggleserver import utils
from qtoggleserver.conf import settings

from .base import BaseEventHandler


logger = logging.getLogger(__name__)

_registered_handlers = []


def register_handler(handler):
    _registered_handlers.append(handler)


def init():
    for handler_args in settings.event_handlers:
        handler_class_path = handler_args.pop('driver')

        try:
            logger.debug('loading event handler %s', handler_class_path)
            handler_class = utils.load_attr(handler_class_path)
            handler = handler_class(**handler_args)

        except Exception as e:
            logger.error('failed to load event handler %s: %s', handler_class_path, e, exc_info=True)

        else:
            _registered_handlers.append(handler)


def handle_event(event):
    for handler in _registered_handlers:
        asyncio.create_task(handler.handle_event(event))
