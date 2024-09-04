# -*- coding: utf-8 -*-
"""公共装饰器方法
"""
from concurrent.futures import ThreadPoolExecutor


def async_func(max_threads=10):
    """
    函数异步运行装饰器，支持限制并发数
    Args:
        max_threads: (int) 最大并发数，默认为 10
    """
    executor = ThreadPoolExecutor(max_threads)

    def decorator(func):

        def wrapper(*args, **kwargs):
            executor.submit(func, *args, **kwargs)

        return wrapper

    return decorator
