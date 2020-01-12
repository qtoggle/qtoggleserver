
import asyncio
import logging

from qtoggleserver import utils
from qtoggleserver.conf import settings

from .base import Event, Handler


logger = logging.getLogger(__name__)

_registered_handlers = []
_active_handle_tasks = set()


def register_handler(handler: Handler) -> None:
    _registered_handlers.append(handler)


def handle_event(event: Event) -> None:
    for handler in _registered_handlers:
        task = asyncio.create_task(handler.handle_event(event))
        task.add_done_callback(_active_handle_tasks.discard)
        _active_handle_tasks.add(task)


def init() -> None:
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


async def cleanup() -> None:
    if _active_handle_tasks:
        await asyncio.wait(_active_handle_tasks)
