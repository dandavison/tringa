import asyncio
import subprocess
import sys
from typing import AsyncIterator

from tringa.msg import debug


def async_iterator_to_list[T](async_iterator: AsyncIterator[T]) -> list[T]:
    async def collect() -> list[T]:
        return [x async for x in async_iterator]

    return asyncio.run(collect())


async def execute(cmd: list[str]) -> bytes:
    debug(" ".join(cmd))
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    assert process.returncode is not None
    if process.returncode != 0:
        raise subprocess.CalledProcessError(
            process.returncode, " ".join(cmd), stdout, stderr
        )
    return stdout


def tee[T](x: T) -> T:
    print(x, file=sys.stderr)
    return x
