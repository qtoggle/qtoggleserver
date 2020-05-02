
import asyncio
import logging

from typing import List, Set

from qtoggleserver.conf import settings
from qtoggleserver.utils import dynload as dynload_utils

from .base import Event, Handler


logger = logging.getLogger(__name__)

_registered_handlers: List[Handler] = []
_active_handle_tasks: Set[asyncio.Task] = set()


def register_handler(handler: Handler) -> None:
    _registered_handlers.append(handler)


async def handle_event(event: Event) -> None:
    logger.debug('%s triggered', event)

    for handler in _registered_handlers:
        if handler.is_fire_and_forget():
            task = asyncio.create_task(handler.handle_event(event))
            task.add_done_callback(_active_handle_tasks.discard)
            _active_handle_tasks.add(task)

        else:
            # Synchronously call non-fire-and-forget handlers, shielding the loop from any exception
            try:
                await handler.handle_event(event)

            except Exception as e:
                logger.error('event handling failed: %s', e, exc_info=True)


async def init() -> None:
    for handler_args in settings.event_handlers:
        handler_class_path = handler_args.pop('driver')

        try:
            logger.debug('loading event handler %s', handler_class_path)
            handler_class = dynload_utils.load_attr(handler_class_path)
            handler = handler_class(**handler_args)

        except Exception as e:
            logger.error('failed to load event handler %s: %s', handler_class_path, e, exc_info=True)

        else:
            _registered_handlers.append(handler)


async def cleanup() -> None:
    if _active_handle_tasks:
        await asyncio.wait(_active_handle_tasks)

    handler_cleanup_tasks = [handler.cleanup() for handler in _registered_handlers]
    if handler_cleanup_tasks:
        await asyncio.wait(handler_cleanup_tasks)
