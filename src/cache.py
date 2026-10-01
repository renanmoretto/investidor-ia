from collections.abc import Awaitable, Callable
from functools import wraps

import diskcache

from src.settings import CACHE_DIR


cache = diskcache.Cache(str(CACHE_DIR))


def cache_it(
    func: Callable[..., Awaitable],
    expire: int = 60 * 5,  # 5 min
) -> Callable[..., Awaitable]:
    @wraps(func)
    async def wrapper(*args, **kwargs):
        key = f'{func.__name__}:{args}:{kwargs}'
        result = cache.get(key)
        if result is None:
            result = await func(*args, **kwargs)
            cache.set(key, result, expire=expire)
        return result

    return wrapper
