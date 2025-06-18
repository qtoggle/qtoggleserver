import asyncio

from collections.abc import Awaitable, Callable

from qtoggleserver import startup


def execute(main_func: Callable[[], Awaitable[bool]]) -> None:
    loop = asyncio.new_event_loop()

    loop.run_until_complete(startup.init_loop())
    loop.run_until_complete(startup.init())

    try:
        run_loop = loop.run_until_complete(main_func())
        if run_loop:
            loop.run_forever()
        loop.run_until_complete(startup.cleanup())

    finally:
        try:
            loop.run_until_complete(startup.cleanup_loop())
        except asyncio.CancelledError:
            pass  # ignore any cancelled errors

        loop.close()

    startup.logger.info("bye!")
