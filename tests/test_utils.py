from tringa.utils import async_iterator_to_list


def test_async_to_sync_iterator():
    async def my_async_gen():
        for i in range(7):
            yield i

    assert async_iterator_to_list(my_async_gen()) == list(range(7))
