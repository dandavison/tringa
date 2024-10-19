import asyncio
import shlex
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime
from typing import AsyncIterator, Iterator

from tringa.msg import debug


def async_iterator_to_list[T](async_iterator: AsyncIterator[T]) -> list[T]:
    async def collect() -> list[T]:
        return [x async for x in async_iterator]

    return asyncio.run(collect())


async def execute(cmd: list[str]) -> bytes:
    with log_time(cmd):
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


@contextmanager
def log_time(cmd: list[str]) -> Iterator[None]:
    t0 = datetime.now()
    yield
    t1 = datetime.now()
    d = (t1 - t0).total_seconds()
    debug(f"{shlex.join(cmd)} took {d:.2f}s")


def tee[T](x: T) -> T:
    print(x, file=sys.stderr)
    return x
