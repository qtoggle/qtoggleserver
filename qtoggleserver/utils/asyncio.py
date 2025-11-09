import asyncio
import logging

from typing import Any, Awaitable, Coroutine


logger = logging.getLogger(__name__)


async def await_later(delay: float, aw: Awaitable) -> None:
    await asyncio.sleep(delay)
    await aw


def fire_and_forget(coro: Coroutine[Any, Any, Any]) -> None:
    """Schedule coro as a background task, log any exception and consume it."""
    task = asyncio.create_task(coro)

    def _on_done(t: asyncio.Task) -> None:
        try:
            t.result()
        except Exception as e:
            logger.error("Error while handling task: %s", e, exc_info=True)
        except asyncio.CancelledError:
            # Task was cancelled while we were handling it - nothing to do.
            pass

    task.add_done_callback(_on_done)
