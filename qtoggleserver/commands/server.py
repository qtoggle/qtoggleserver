#!/usr/bin/env python

import asyncio
import logging
import ssl

from qtoggleserver import commands
from qtoggleserver.conf import settings
from qtoggleserver.web import server as web_server


logger = logging.getLogger('qtoggleserver.server')


def init_web_server() -> None:
    listen, port = settings.server.addr, settings.server.port

    ssl_context = None
    if settings.server.https.cert_file and settings.server.https.key_file:
        logger.info('setting up HTTPS using certificate from %s', settings.server.https.cert_file)
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(settings.server.https.cert_file, settings.server.https.key_file)

    try:
        web_server.get_application().listen(port, listen, ssl_options=ssl_context)
        logger.info('server listening on %s:%s', listen, port)

    except Exception as e:
        logger.error('server listen failed: %s', e)
        raise


def execute() -> None:
    loop = asyncio.get_event_loop()

    loop.run_until_complete(commands.init())
    init_web_server()

    try:
        loop.run_forever()
        loop.run_until_complete(commands.cleanup())

    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

    commands.logger.info('bye!')


if __name__ == '__main__':
    execute()
