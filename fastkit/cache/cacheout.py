from asyncio import iscoroutinefunction
from functools import wraps
from cacheout import Cache, FIFOCache, LIFOCache, LRUCache, MRUCache, LFUCache, RRCache

from fastkit.utils.common import get_md5


def generate_cache_key(func, *args, **kwargs):
    """
    生成唯一的缓存键，基于函数名称和参数。

    :param func: 被装饰的函数
    :param args: 位置参数
    :param kwargs: 关键字参数
    :return: 生成的缓存键
    """
    # 将函数名称、位置参数和关键字参数组合成一个字符串
    key = f"{func.__module__}.{func.__name__}:{args}:{kwargs}"
    return f"{func.__module__}.{func.__name__}:{get_md5(key)}"


def cache_result_decorator(cache_instance):
    """
    装饰器，用于缓存函数的返回结果。

    :param cache_instance: 缓存实例
    """

    def decorator(ttl: int = 120):

        def wrapper(func):

            @wraps(func)
            async def async_inner(*args, **kwargs):
                cache_key = generate_cache_key(func, *args, **kwargs)
                # 检查缓存
                cached_result = cache_instance.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # 调用原异步函数
                result = await func(*args, **kwargs)

                # 将结果存入缓存
                if result is not None:
                    cache_instance.set(cache_key, result, ttl)

                return result

            @wraps(func)
            def sync_inner(*args, **kwargs):
                cache_key = generate_cache_key(func, *args, **kwargs)
                # 检查缓存
                cached_result = cache_instance.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # 调用原同步函数
                result = func(*args, **kwargs)

                # 将结果存入缓存
                if result is not None:
                    cache_instance.set(cache_key, result, ttl)

                return result

            # 根据函数类型返回相应的包装函数
            if iscoroutinefunction(func):
                return async_inner
            else:
                return sync_inner

        return wrapper

    return decorator


CACHE_INSTS = {}

# 创建一个字典，将不同的缓存类型映射到相应的类
CACHE_TYPES = {
    "cache": Cache,
    "fifo": FIFOCache,
    "lifo": LIFOCache,
    "lru": LRUCache,
    "mru": MRUCache,
    "lfu": LFUCache,
    "rr": RRCache,
}


def get_cacheout_pool(
    cache_name: str = "default", cache_type: str = "cache", maxsize: int = 256, ttl: int = 0, **kwargs
) -> Cache:
    """
    初始化本地内存缓存

    参数说明:
        cache_name (str): 缓存池名称，相同名称将复用池子，不会重复创建，如果不想复用，请注意自定义。
        cache_type (str): 缓存类型，可选值为 "cache", "fifo", "lifo", "lru", "mru", "lfu", "rr"，默认为 "cache"。
        maxsize (int): 缓存字典的最大大小。默认为 256。
        ttl (int): 所有缓存条目的默认TTL。默认为 0，表示条目不会过期。
        **kwargs: 其他参数，根据不同缓存类型的需求而定，具体可参考：https://cacheout.readthedocs.io/en/latest/index.html

    Returns:
        Cache: 返回相应类型的缓存对象。
    """

    full_cache_name = f"{cache_name}_{cache_type}"  # 在缓存名称中包含缓存类型信息
    if full_cache_name not in CACHE_INSTS:
        cache_class = CACHE_TYPES.get(cache_type)
        if cache_class is None:
            raise ValueError("Invalid cache type. Supported types: 'cache', 'fifo', 'lifo', 'lru', 'mru', 'lfu', 'rr'.")

        cache_instance = cache_class(maxsize=maxsize, ttl=ttl, **kwargs)
        # 将装饰器注入到缓存实例中
        cache_instance.cache_result = cache_result_decorator(cache_instance)
        CACHE_INSTS[full_cache_name] = cache_instance

    return CACHE_INSTS[full_cache_name]
