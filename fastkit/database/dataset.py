from urllib.parse import quote_plus
from dataset import Database
from fastkit.logging import logger


class DataSet(Database):
    _instances = {}

    @classmethod
    def get_instance(cls,
                     host,
                     port,
                     database,
                     user="root",
                     passwd="",
                     pool_recycle=1800,
                     pool_size=32,
                     max_overflow=64,
                     charset="utf8",
                     ensure_schema=False,
                     **kwargs):
        """获取数据库实例
        注：可防止重复初始化并处理连接关闭的情况
        """
        key = f"{user}:{passwd}@{host}:{port}/{database}?charset={charset}&ensure_schema={ensure_schema}&args={kwargs}"
        instance = cls._instances.get(key)

        if instance:
            # 当连接池被关闭时，重新初始化
            if getattr(instance, "engine", None) is None:
                logger.warning("Dataset closed connection. Reinitializing...")
                del cls._instances[key]
                instance = None

        if instance is None:
            cls._instances[key]: Database = cls._create_instance(
                host, port, database, user, passwd, pool_recycle, pool_size,
                max_overflow, charset, ensure_schema, **kwargs)

        return cls._instances[key]

    @classmethod
    def _create_instance(cls, host, port, database, user, passwd, pool_recycle,
                         pool_size, max_overflow, charset, ensure_schema,
                         **kwargs):
        url = f"mysql+pymysql://{user}:{quote_plus(passwd)}@{host}:{port}/{database}?charset={charset}"
        kwargs.setdefault("pool_pre_ping", True)
        engine_kwargs = {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_recycle": pool_recycle,
            **kwargs
        }
        return cls(url,
                   engine_kwargs=engine_kwargs,
                   ensure_schema=ensure_schema)

    def __init__(self, url, engine_kwargs, *args, **kwargs):
        super().__init__(url, engine_kwargs=engine_kwargs, *args, **kwargs)

    def __getitem__(self, key):
        """表对象添加重试机制
        """
        item = super().__getitem__(key)
        return self._wrap_methods(item)

    def close(self, force: bool = False):
        """关闭连接池
        注：默认不关闭，防止意外关闭了其他相同数据库连接池，需要传入强制参数方可关闭
        """
        if not force:
            return False

        return super().close()

    def query(self, query, *args, **kwargs):
        """原始SQL查询添加重试机制
        """
        return self._wrap_methods(super().query)(query, *args, **kwargs)

    def _wrap_methods(self, func):
        """
        注入重试机制
        """

        def _retry(func):
            """重试逻辑
            """

            def wrapper(*args, **kwargs):
                retries = 0
                while retries < 3:
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if "Lost connection to MySQL server" in str(
                                e) or "MySQL server has gone away" in str(e):
                            logger.warning("MySQL连接丢失或已断开，正在重试...")
                            retries += 1
                        else:
                            raise
                raise Exception("多次重试后仍失败")

            return wrapper

        class RetryWrapper:
            """断连重试
            """

            def __init__(self, func):
                self.func = func

            def __getattr__(self, name):
                attr = getattr(self.func, name)
                if callable(attr):
                    return self._wrap_method(attr)
                return attr

            def __call__(self, *args, **kwargs):
                return _retry(self.func)(*args, **kwargs)

            def _wrap_method(self, method):
                return _retry(method)

        return RetryWrapper(func)


def get_dataset_pool(host: str,
                     port: int,
                     database: str,
                     user: str = "root",
                     passwd: str = "",
                     pool_recycle=1800,
                     pool_size=32,
                     max_overflow=64,
                     charset="utf8",
                     ensure_schema=False,
                     **kwargs) -> Database:
    """
    初始化 DataSet 连接池
    Args:
        host: 数据库主机名
        port: 数据库端口
        database: 数据库名称
        user: 数据库用户名，默认为"root"
        passwd: 数据库密码，默认为空
        pool_recycle: 连接池回收时间，默认为1800秒
        pool_size: 连接池大小，默认为32
        max_overflow: 连接池溢出大小，默认为64
        charset: 数据库字符集，默认为"utf8"
        ensure_schema: 禁止自动创建表和字段
        force_init: 是否强制初始化连接池
        **kwargs: 其他 create_engine 方法参数
    """
    return DataSet.get_instance(host,
                                port,
                                database,
                                user,
                                passwd,
                                pool_recycle,
                                pool_size,
                                max_overflow,
                                charset,
                                ensure_schema=ensure_schema,
                                **kwargs)
