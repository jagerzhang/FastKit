# 数据缓存
## Redis

```python
from fastkit.cache import get_redis_pool

redis_pool = get_redis_pool("127.0.0.1", "6379", "passwd")
redis_pool.set("a", 1)
redis_pool.get("a")
```

## CacheOut

基于本地共享内存的缓存方法，支持各种缓存场景，详见说明：[https://cacheout.readthedocs.io/en/latest/index.html](https://cacheout.readthedocs.io/en/latest/index.html)

```python
from fastkit.cache import get_cacheout_pool

cache = get_cacheout_pool(cache_name="custom")
cache.set("a", 1)
cache.get("a")
```
