#!/usr/bin/env python

from qtoggleserver import commands
from qtoggleserver.web import server as web_server


async def main() -> bool:
    await web_server.init()

    return True  # Run loop afterwards


def execute() -> None:
    commands.execute(main())


if __name__ == '__main__':
    execute()
