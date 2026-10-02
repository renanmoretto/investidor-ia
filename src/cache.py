from collections.abc import Awaitable, Callable
from functools import wraps

from src import db


def cache_it(
    func: Callable[..., Awaitable],
    expire: int = 60 * 5,  # 5 min
) -> Callable[..., Awaitable]:
    """The result is stored as JSON, so the function must return JSON types only."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        key = f'{func.__name__}:{args}:{kwargs}'
        result = db.cache_get(key)
        if result is None:
            result = await func(*args, **kwargs)
            db.cache_set(key, result, expire=expire)
        return result

    return wrapper
