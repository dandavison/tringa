import asyncio
import sys
from queue import Queue
from threading import Thread
from typing import AsyncIterator, Iterator, TypeVar

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


def tee(x: T) -> T:
    print(x, file=sys.stderr)
    return x


if __name__ == "__main__":

    async def my_async_gen():
        for i in range(7):
            yield i

    print(list(async_to_sync_iterator(my_async_gen())))
