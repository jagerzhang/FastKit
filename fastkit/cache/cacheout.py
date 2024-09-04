from cacheout import Cache, FIFOCache, LIFOCache, LRUCache, MRUCache, LFUCache, RRCache

CACHE_INSTS = {}

# 创建一个字典，将不同的缓存类型映射到相应的类
CACHE_TYPES = {
    "cache": Cache,
    "fifo": FIFOCache,
    "lifo": LIFOCache,
    "lru": LRUCache,
    "mru": MRUCache,
    "lfu": LFUCache,
    "rr": RRCache
}


def get_cacheout_pool(cache_name: str = "default",
                      cache_type: str = "cache",
                      maxsize: int = 256,
                      ttl: int = 0,
                      **kwargs) -> Cache:
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
            raise ValueError(
                "Invalid cache type. Supported types: 'cache', 'fifo', 'lifo', 'lru', 'mru', 'lfu', 'rr'."
            )

        CACHE_INSTS[full_cache_name] = cache_class(maxsize=maxsize,
                                                   ttl=ttl,
                                                   **kwargs)

    return CACHE_INSTS[full_cache_name]
