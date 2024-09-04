# -*- coding: utf-8 -*-
import redis


def get_redis_pool(host: str,
                   port: int,
                   passwd: str,
                   database: int = 0,
                   timeout: int = 3):
    """
    初始化 Redis 连接池

    Args:
        host (str): 服务地址
        port (int): 服务端口
        passwd (str): 实例密码
        database (int, optional): 自定义数据库. Defaults to 0.
        timeout (int, optional): 连接超时. Defaults to 3.

    Returns:
        _type_: _description_
    """
    pool = redis.ConnectionPool(host=host,
                                port=int(port),
                                password=passwd,
                                db=database,
                                decode_responses=True,
                                socket_connect_timeout=timeout)
    return redis.Redis(connection_pool=pool)
