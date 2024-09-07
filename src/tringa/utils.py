import asyncio
import subprocess
import sys
from queue import Queue
from threading import Thread
from typing import AsyncIterator, Iterator, TypeVar

from tringa.msg import info

T = TypeVar("T")


class async_to_sync_iterator[T](Iterator[T]):
    def __init__(self, async_iterator: AsyncIterator[T]) -> None:
        self.queue = Queue()
        self.sentinel = object()
        # TODO: terminate thread cleanly on error
        Thread(target=lambda: asyncio.run(self._produce(async_iterator))).start()

    async def _produce(self, async_iterator: AsyncIterator[T]) -> None:
        async for t in async_iterator:
            self.queue.put(t)
        self.queue.put(self.sentinel)

    def __next__(self) -> T:
        t = self.queue.get()
        if t == self.sentinel:
            raise StopIteration
        else:
            return t


async def execute(cmd: list[str]) -> bytes:
    info(" ".join(cmd))
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()
    assert process.returncode is not None
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd)
    return stdout


def tee(x: T) -> T:
    print(x, file=sys.stderr)
    return x
