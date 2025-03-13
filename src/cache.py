from typing import Callable, Any


class Cache:
    def __init__(self):
        self.cache = {}

    def get(self, key: str) -> Any:
        return self.cache.get(key)

    def set(self, key: str, value: Any):
        self.cache[key] = value


cache = Cache()


def cache_it(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        key = f'{func.__name__}:{args}:{kwargs}'
        cached_value = cache.get(key)
        if cached_value:
            return cached_value
        result = func(*args, **kwargs)
        cache.set(key, result)
        return result

    return wrapper
