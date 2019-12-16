
import asyncio

from .base import BaseEventHandler


_registered_handlers = []


def register_handler(handler):
    _registered_handlers.append(handler)


async def handle_event(event):
    for handler in _registered_handlers:
        asyncio.create_task(handler.handle_event(event))
