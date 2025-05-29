#!/usr/bin/env python

import code

from qtoggleserver import commands


async def main() -> bool:
    import qtoggleserver  # noqa: F401 - Required for locals()

    code.interact(local=locals())

    return False  # don't run loop afterwards


def execute() -> None:
    commands.execute(main)


if __name__ == "__main__":
    execute()
