
import asyncio

from typing import List, Optional, Tuple

from tornado import process as tornado_process


async def call_subprocess(args: List[str], stdin_data: Optional[bytes] = None) -> Tuple[int, bytes, bytes]:
    p = tornado_process.Subprocess(
        args,
        stdin=tornado_process.Subprocess.STREAM,
        stdout=tornado_process.Subprocess.STREAM,
        stderr=tornado_process.Subprocess.STREAM
    )

    if stdin_data:
        await p.stdin.write(stdin_data)
        p.stdin.close()

    exit_future = p.wait_for_exit(raise_error=False)
    stdout_future = p.stdout.read_until_close()
    stderr_future = p.stderr.read_until_close()

    await asyncio.wait({exit_future, stdout_future, stderr_future})

    return exit_future.result(), stdout_future.result(), stderr_future.result()
