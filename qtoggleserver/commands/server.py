#!/usr/bin/env python

import asyncio
import logging

from qtoggleserver import commands
from qtoggleserver.conf import settings
from qtoggleserver.web import server as web_server


logger = logging.getLogger('qtoggleserver.server')


def init_web_server():
    listen, port = settings.server.addr, settings.server.port

    try:
        web_server.get_application().listen(port, listen)
        logger.info('server listening on %s:%s', listen, port)

    except Exception as e:
        logger.error('server listen failed: %s', e)
        raise


def execute():
    loop = asyncio.get_event_loop()

    loop.run_until_complete(commands.init())
    init_web_server()

    try:
        loop.run_forever()
        loop.run_until_complete(commands.done())

    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

    commands.logger.info('bye!')


if __name__ == '__main__':
    execute()
