from django.core.cache import cache

def set_cache(
    key: str, 
    value: dict,
    timeout: int | None = None,
) -> None:

    cache.set(key,value,timeout)

def get_cache(key: str) -> dict:

    return cache.get(key)

def delete_cache(key: str) -> None:

    cache.delete(key)