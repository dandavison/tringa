from tringa.utils import async_to_sync_iterator


def test_async_to_sync_iterator():
    async def my_async_gen():
        for i in range(7):
            yield i

    sync_iter = async_to_sync_iterator(my_async_gen())
    assert list(sync_iter) == list(range(7))
