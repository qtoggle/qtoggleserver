
import asyncio

from typing import Awaitable

from qtoggleserver import startup


def execute(main_code: Awaitable) -> None:
    loop = asyncio.get_event_loop()

    loop.run_until_complete(startup.init_loop())
    loop.run_until_complete(startup.init())

    try:
        run_loop = loop.run_until_complete(main_code)
        if run_loop:
            loop.run_forever()
        loop.run_until_complete(startup.cleanup())

    finally:
        try:
            loop.run_until_complete(startup.cleanup_loop())

        except asyncio.CancelledError:
            pass  # Ignore any cancelled errors

        loop.close()

    startup.logger.info('bye!')
