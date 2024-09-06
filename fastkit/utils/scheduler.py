import time
from asyncio import sleep
from site import getsitepackages
from os import getenv
import functools
import inspect
from asyncio import iscoroutinefunction
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from redlock import RedLockFactory, RedLockError
from fastkit.logging import get_logger

SCHEDULERS = {}

site_path = getsitepackages()[0]


class Scheduler:
    """任务调度
    """

    def __init__(self,
                 name: str = "default",
                 scheduler_type: str = "background",
                 logger: object = None,
                 auto_start: bool = True,
                 timezone: str = None,
                 redis_nodes: list = None):
        self.logger = get_logger(logger_name="console")
        self.redlock = RedLockFactory(
            connection_details=redis_nodes) if redis_nodes else None
        self.redis_nodes = redis_nodes
        self.scheduler = self._init_scheduler(name=name,
                                              scheduler_type=scheduler_type,
                                              auto_start=auto_start,
                                              logger=logger,
                                              timezone=timezone)

    def _init_scheduler(self,
                        name="default",
                        scheduler_type="background",
                        logger=None,
                        auto_start=True,
                        timezone=None):
        """
        生成APS任务调度实例
        """
        global SCHEDULERS
        if scheduler_type not in SCHEDULERS:
            SCHEDULERS[scheduler_type] = {}

        if name not in SCHEDULERS.get(scheduler_type, {}):
            timezone = timezone or getenv("TZ", "Asia/Shanghai")
            logger = logger or self.logger
            if scheduler_type == "background":
                SCHEDULERS[scheduler_type][name] = BackgroundScheduler(
                    timezone=timezone, logger=logger)
            elif scheduler_type == "asyncio":
                SCHEDULERS[scheduler_type][name] = AsyncIOScheduler(
                    timezone=timezone, logger=logger)
            else:
                raise ValueError("Unsupported scheduler type")

        scheduler = SCHEDULERS[scheduler_type][name]
        if not scheduler.running and auto_start:
            scheduler.start()

        return scheduler

    def _get_func_id(self, func, trigger="one-off", args=None, kwargs=None):
        """获取函数唯一id
        """
        source_info = inspect.getsourcefile(func).replace(f"{site_path}/", "")
        line_number = inspect.getsourcelines(func)[1]
        func_id = f"{trigger}>{func.__name__}@{source_info}:{line_number}"
        if args:
            func_id += f"#{args}"
        if kwargs:
            func_id += f"#{kwargs}"
        return func_id

    def add_job(self,
                func,
                trigger,
                args=None,
                kwargs=None,
                single_job=True,
                **job_kwargs):
        """添加任务（支持单任务防重复添加）

        Args:
            func (object): 函数对象
            trigger (触发器类型): apscheduler触发器类型, 支持 interval, date, cron. Defaults to "interval".
            args (_type_, optional): 函数执行参数. Defaults to None.
            kwargs (_type_, optional): 函数执行参数. Defaults to None.
            single_job (bool, optional): 是否为单任务. Defaults to True.
            **job_kwargs: apscheduler job参数. Defaults to {}.
        """

        job_id = self._get_func_id(func, trigger, args, kwargs)

        # 单个添加
        @self.lock(local_runtime=True)
        def _add_single_job():
            job = self.scheduler.add_job(func,
                                         trigger,
                                         args=args,
                                         kwargs=kwargs,
                                         **job_kwargs)
            self.logger.info(f"Job {job_id} added successfully.")
            return job

        # 常规添加
        def _add_job():
            job = self.scheduler.add_job(func,
                                         trigger,
                                         args=args,
                                         kwargs=kwargs,
                                         **job_kwargs)
            self.logger.info(f"Job {job_id} added successfully.")
            return job

        if single_job:
            return _add_single_job()  # 调用内部函数
        else:
            return _add_job()  # 调用内部函数

    def __getattr__(self, name):
        """代理调度器方法
        """
        attr = getattr(self.scheduler, name)
        if callable(attr):
            return self._wrap_method(attr)
        return attr

    def _wrap_method(self, method):
        """包装调度器方法
        """

        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            return method(*args, **kwargs)

        return wrapper

    def lock(self, local_runtime: bool = False):
        """调度器分布式锁
        local_runtime: 本地运行时，需要加入0.5秒休眠，避免加锁失败
        """

        def decorator(func):
            if not self.redlock:
                return func

            if iscoroutinefunction(func):

                @functools.wraps(func)
                async def wrapper(*args, **kwargs):
                    lock_key = self._get_func_id(func, "one-off", args, kwargs)
                    try:
                        with self.redlock.create_lock(lock_key):
                            if local_runtime:
                                sleep(0.5)
                            return await func(*args, **kwargs)
                    except RedLockError:
                        self.logger.debug(f"函数已被执行，本次执行已跳过: {lock_key}")
            else:

                @functools.wraps(func)
                def wrapper(*args, **kwargs):
                    try:
                        lock_key = self._get_func_id(func, "one-off", args,
                                                     kwargs)
                        with self.redlock.create_lock(lock_key):
                            # 本地多进程很多时候几乎是同一时刻添加，导致锁无法生效
                            if local_runtime:
                                time.sleep(0.5)
                            return func(*args, **kwargs)
                    except RedLockError:
                        self.logger.debug(f"函数已被执行，本次执行已跳过: {lock_key}")

            return wrapper

        return decorator
