"""定时调度器
"""

from inspect import iscoroutinefunction
from os import getenv

from concurrent.futures import ThreadPoolExecutor as _ThreadPoolExecutor, wait as wait_task
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from fastkit.logging import get_logger
from fastkit.cache import get_redis_pool

from .base import get_func_id, InterruptibleSleep

SCHEDULERS = {}


class Scheduler:
    """任务调度器"""

    def __init__(
        self,
        name: str = "default",
        scheduler_type: str = "background",
        logger: object = None,
        auto_start: bool = True,
        timezone: str = None,
        redis_config: dict = None,
        executor_type: str = "threadpool",
        pool_size: int = 20,
    ):
        self.logger = get_logger(logger_name="console")
        self.redis_client = get_redis_pool(**redis_config) if redis_config else None
        self.executor_type = executor_type or "threadpool"
        self.scheduler: BackgroundScheduler = self._init_scheduler(
            name, scheduler_type, auto_start, logger, timezone, executor_type, pool_size
        )
        self.lock_timeout = 20
        self.executor = _ThreadPoolExecutor(max_workers=pool_size)
        self.interruptible_sleep = InterruptibleSleep()
        self.sleep = self.interruptible_sleep.sleep

    def add_job(self, func, trigger: str, args=None, kwargs=None, single_job: bool = False, **job_kwargs):
        """
        将任务添加到任务列表，并在调度器正在运行时唤醒调度器。

        :param func: 可调用对象（或其文本引用），在给定时间运行
        :param str|apscheduler.triggers.base.BaseTrigger trigger: 决定何时调用 ``func`` 的触发器
        :param list|tuple args: 调用 func 时的位置参数列表
        :param dict kwargs: 调用 func 时的关键字参数字典
        :param bool single_job: 任务是否应为单例
        :param job_kwargs: 其他任务参数
        :rtype: str
        """
        args = args or ()
        kwargs = kwargs or {}
        job_id = get_func_id(func, trigger, args, kwargs)
        job = None
        if single_job and self.redis_client:
            # 使用 Redis SETNX 确保多进程互斥
            lock_key = f"{job_id}"
            if self.redis_client.set(lock_key, "locked", nx=True, ex=2):
                if iscoroutinefunction(func):
                    job = self.scheduler.add_job(
                        self._lock_wrapper_async, args=(func, job_id, args, kwargs), trigger=trigger, **job_kwargs
                    )
                else:
                    job = self.scheduler.add_job(
                        self._lock_wrapper_sync, args=(func, job_id, args, kwargs), trigger=trigger, **job_kwargs
                    )
            else:
                self.logger.debug(f"单进程任务 {func.__name__} 已经被其他进程添加。")
        else:
            if single_job:
                self.logger.warning(
                    f"请注意：因未配置 redis，单例任务 {func.__name__} 互斥失败，所有进程应该都加了这个任务。"
                )

            job = self.scheduler.add_job(func, trigger=trigger, args=args, kwargs=kwargs, **job_kwargs)
        return job

    def _init_scheduler(
        self,
        name: str,
        scheduler_type: str,
        auto_start: bool,
        logger: object,
        timezone: str,
        executor_type: str,
        pool_size: int,
    ):
        global SCHEDULERS
        if scheduler_type not in SCHEDULERS:
            SCHEDULERS[scheduler_type] = {}

        kwargs = {
            "timezone": timezone or getenv("TZ", "Asia/Shanghai"),
            "logger": logger or self.logger,
            "executor": self._get_executor(executor_type, pool_size),
        }

        if name not in SCHEDULERS[scheduler_type]:
            if scheduler_type == "background":
                SCHEDULERS[scheduler_type][name] = BackgroundScheduler(**kwargs)
            elif scheduler_type == "asyncio":
                SCHEDULERS[scheduler_type][name] = AsyncIOScheduler(**kwargs)
            elif scheduler_type == "block":
                SCHEDULERS[scheduler_type][name] = BlockingScheduler(**kwargs)
            else:
                raise ValueError("不支持的调度器类型")

        scheduler = SCHEDULERS[scheduler_type][name]
        if not scheduler.running and auto_start and scheduler_type != "block":
            scheduler.start()

        return scheduler

    def _get_executor(self, executor_type: str, pool_size: int):
        if executor_type == "processpool":
            return {"default": ProcessPoolExecutor(pool_size)}
        return {"default": ThreadPoolExecutor(pool_size)}

    def scheduled_job(self, trigger="interval", id=None, args=None, kwargs=None, single_job=False, **job_kwargs):
        """
        :meth:`add_job` 的装饰器版本，除了 ``replace_existing`` 始终为 ``True``。
        """

        def inner(func):
            job_id = id or get_func_id(func, trigger, args, kwargs)
            self.add_job(
                func, trigger=trigger, id=job_id, single_job=single_job, args=args, kwargs=kwargs, **job_kwargs
            )
            return func

        return inner

    def _heartbeat(self, lock_key):
        """心跳线程，定期刷新锁的过期时间。"""
        while lock_key and self.scheduler.running and self.redis_client.get(lock_key):
            self.sleep(self.lock_timeout / 2)
            try:
                if self.redis_client.get(lock_key):
                    self.redis_client.expire(lock_key, time=self.lock_timeout)

            except Exception as e:  # pylint: disable=broad-except
                self.logger.warning(f"心跳线程刷新锁失败: {e}")
                break

        # 退出时清理锁
        if self.redis_client.get(lock_key):
            self.redis_client.delete(lock_key)

    async def _lock_wrapper_async(self, func, job_id, args, kwargs):
        """异步任务的锁包装器"""
        if not self.redis_client:
            return await func(*args, **kwargs)

        lock = self.redis_client.lock(job_id, timeout=self.lock_timeout)
        if await lock.acquire(blocking=False):
            self.logger.debug(f"尝试获取任务锁: {job_id}")
            try:
                self.executor.submit(self._heartbeat, job_id)
                return await func(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"任务执行失败: {e}")
                raise  # 重新抛出异常
            finally:
                await lock.release()
                self.logger.debug(f"任务执行完成，释放分布式锁: {job_id}")
        else:
            self.logger.debug(f"获取分布式锁失败，任务 {func.__name__} 可能在其他节点运行了")

    def _lock_wrapper_sync(self, func, job_id, args, kwargs):
        """同步任务的锁包装器"""
        if not self.redis_client:
            return func(*args, **kwargs)

        lock = self.redis_client.lock(job_id, timeout=self.lock_timeout)
        if lock.acquire(blocking=False):
            self.logger.debug(f"尝试获取任务锁: {job_id}")
            try:
                self.executor.submit(self._heartbeat, job_id)
                return func(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"任务执行失败: {e}")
                raise  # 重新抛出异常
            finally:
                lock.release()
                self.logger.debug(f"任务执行完成，释放分布式锁: {job_id}")
        else:
            self.logger.debug(f"获取分布式锁失败，任务 {func.__name__} 可能在其他节点运行了")

    def __getattr__(self, name):
        attr = getattr(self.scheduler, name)
        if callable(attr):
            return attr  # 直接返回方法
        return attr

    def shutdown(self, wait: bool = True, timeout: int = 20, on_timeout: callable = None):
        """关闭调度器

        :param wait: 是否等待所有任务完成
        :param timeout: 等待的最大时间（秒），如果为 None 则不设置超时
        :param on_timeout: 超时后执行的回调函数
        """
        self.interruptible_sleep.interrupt()
        self.executor.shutdown(wait=False)
        if self.scheduler.running:
            if wait:
                _executor = _ThreadPoolExecutor(max_workers=1)
                try:
                    # 等待调度器关闭，设置超时
                    futures = [_executor.submit(self.scheduler.shutdown, wait=True)]
                    wait_task(futures, timeout=timeout)
                except TimeoutError:
                    self.logger.warning("定时任务调度器关闭超时，强制关闭。")
                    if callable(on_timeout):
                        on_timeout()
                    self.scheduler.shutdown(wait=False)
                finally:
                    _executor.shutdown(wait=False)
            else:
                self.scheduler.shutdown(wait=False)
