from typing import Callable

import diskcache

from src.settings import CACHE_DIR


cache = diskcache.Cache(str(CACHE_DIR))


def cache_it(
    func: Callable,
    expire: int = 60 * 5,  # 5 min
) -> Callable:
    def wrapper(*args, **kwargs):
        key = f'{func.__name__}:{args}:{kwargs}'
        result = cache.get(key)
        if result is None:
            result = func(*args, **kwargs)
            cache.set(key, result, expire=expire)
        return result

    return wrapper
