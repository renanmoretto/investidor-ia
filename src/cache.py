from typing import Callable, Any
from pathlib import Path

import diskcache


CACHE_DIR = Path(__file__).parent.parent / 'cache'
CACHE_DIR.mkdir(exist_ok=True, parents=True)


cache = diskcache.Cache(str(CACHE_DIR))


def cache_it(
    func: Callable,
    expire: int = 60 * 30,  # 15 minutes
) -> Callable:
    def wrapper(*args, **kwargs):
        key = f'{func.__name__}:{args}:{kwargs}'
        result = cache.get(key)
        if result is None:
            result = func(*args, **kwargs)
            cache.set(key, result, expire=expire)
        return result

    return wrapper
