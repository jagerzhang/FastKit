# -*- coding: utf-8 -*-
from .httpclient import Client
from .httpclient import AsyncClient

DEFAULT_REQUEST_RETRY_CONFIG = {
    "stop_max_attempt_number": 3,  # 最大重试 3 次
    "stop_max_delay": 60,  # 最大重试耗时 60 s
    "wait_exponential_multiplier": 2,  # 重试间隔时间倍数 2s、4s、8s...
    "wait_exponential_max": 10  # 最大重试间隔时间 10s
}

# 内置默认的HTTP请求方法
client = requests = Client(**DEFAULT_REQUEST_RETRY_CONFIG)
aioclient = aiorequests = AsyncClient(**DEFAULT_REQUEST_RETRY_CONFIG)
