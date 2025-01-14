"""线程池管理
"""

import time
import traceback
from concurrent.futures import ThreadPoolExecutor as _ThreadPoolExecutor
from concurrent.futures import wait as wait_task
from queue import Empty, Queue
from threading import Event

from fastkit.cache import get_redis_pool
from fastkit.logging import get_logger

from .base import InterruptibleSleep, get_func_id


class ThreadPoolExecutor:
    """线程池包装类，支持任务队列和 Redis 锁。"""

    def __init__(self, max_workers=10, redis_config: dict = None):
        """初始化线程池。

        Args:
            max_workers (int): 最大工作线程数。
            redis_config (dict): Redis 配置字典。
        """
        self.task_queue = Queue()  # 任务队列
        self.logger = get_logger(logger_name="console")
        self.redis_client = get_redis_pool(**redis_config) if redis_config else None
        self.stop_event = Event()  # 用于控制任务停止
        self.lock_timeout = 10  # 锁的超时时间
        self.executor = _ThreadPoolExecutor(max_workers=max_workers)
        self.interruptible_sleep = InterruptibleSleep()
        self.sleep = self.interruptible_sleep.sleep
        self.futures = []
        future = self.executor.submit(self._consume_tasks)
        self.futures.append(future)

    def submit(self, single_job=True):
        """装饰器，用于提交任务到队列。

        Args:
            single_job (bool): 是否使用 Redis 锁。

        Returns:
            function: 内部函数，用于提交任务。
        """

        def inner(func, *args, **kwargs):
            self.task_queue.put((func, single_job, args, kwargs))
            self.logger.info(f"线程任务 {func.__name__} 已成功提交到任务队列。")

        return inner

    def submit_task(self, func, single_job=True, *args, **kwargs):
        """显式添加任务到队列。

        Args:
            func (callable): 要执行的函数。
            single_job (bool): 是否是单任务（使用 Redis 分布式锁）。
            *args: 传递给函数的位置参数。
            **kwargs: 传递给函数的关键字参数。
        """
        if not func:
            return
        self.task_queue.put((func, single_job, args, kwargs))
        self.logger.info(f"线程任务 {func.__name__} 已成功提交到任务队列。")

    def _consume_tasks(self):
        """消费任务的线程，持续从队列中获取任务并执行。"""
        while not self.stop_event.is_set():
            try:
                func, single_job, args, kwargs = self.task_queue.get(timeout=1)
                lock_key = get_func_id(func, "thread-task", args=args, kwargs=kwargs)

                get_lock = None
                lock = None
                if self.redis_client and single_job:
                    lock = self.redis_client.lock(lock_key, timeout=self.lock_timeout)
                    try:
                        get_lock = lock.acquire(blocking=True)
                    except Exception:  # pylint: disable=broad-except
                        self.logger.error(f"获取锁失败: {traceback.format_exc()}")

                if get_lock or not self.redis_client or not single_job:
                    future = self.executor.submit(self._execute_task, func, args, kwargs, lock if get_lock else None)
                    self.futures.append(future)
                else:
                    self.task_queue.put((func, single_job, args, kwargs))  # 重新放回队列
                    if lock:
                        lock.timeout = self.lock_timeout  # 重新设置锁的超时时间

            except Empty:
                time.sleep(0.5)  # 如果队列为空，稍等后继续
                continue
            except Exception as e:  # pylint: disable=broad-except
                self.logger.error(f"线程任务消费错误: {e}")

    def _execute_task(self, func, args, kwargs, lock):
        """执行任务包装方法，处理任务的执行和锁的管理。

        Args:
            func (callable): 要执行的函数。
            args (tuple): 传递给函数的位置参数。
            kwargs (dict): 传递给函数的关键字参数。
            lock: Redis 锁对象。
        """
        try:
            # 如果配置了redis，则加上心跳刷新
            if self.redis_client:
                lock_key = get_func_id(func, "thread-task", args=args, kwargs=kwargs)
                future = self.executor.submit(self._heartbeat, lock_key)
                self.futures.append(future)

            result = func(*args, **kwargs)
            self.logger.info(f"任务 {func.__name__} 执行成功，返回: {result}")
        except Exception:  # pylint: disable=broad-except
            self.logger.error(f"任务 {func.__name__} 执行失败: {traceback.format_exc()}")
        finally:
            if lock:
                lock.release()
            if self.redis_client:
                self.redis_client.delete(lock_key)

    def _heartbeat(self, lock_key):
        """心跳线程，定期刷新锁的过期时间。

        Args:
            lock_key (str): Redis 锁的键。
        """
        while lock_key and not self.stop_event.is_set():
            self.sleep(self.lock_timeout / 2)
            try:
                if self.redis_client.get(lock_key):
                    self.redis_client.expire(lock_key, time=self.lock_timeout)
            except Exception:  # pylint: disable=broad-except
                self.logger.warning(f"心跳线程刷新锁失败: {traceback.format_exc()}")
                break

    def shutdown(self, wait: bool = True, timeout: int = 20, show_log: bool = True, on_timeout: callable = None):
        """优雅地关闭线程池，等待所有任务完成，支持超时。

        Args:
            wait (bool): 是否等待所有任务完成。
            timeout (int): 超时时间。
            show_log (bool): 是否显示日志。
            on_timeout (callable): 超时回调函数。
        """
        if show_log:
            self.logger.info("正在关闭线程池...")
        self.stop_event.set()  # 设置停止事件
        self.interruptible_sleep.interrupt()  # 停止刷新线程
        # 等待所有任务完成
        if wait:
            if show_log:
                self.logger.info("正在等待线程池任务完成...")
            try:
                wait_task(self.futures, timeout=timeout)
                if show_log:
                    self.logger.info("所有线程池任务已完成。")
            except TimeoutError:
                if show_log:
                    self.logger.warning(f"线程池关闭超时，经过 {timeout} 秒后仍有任务在运行，强制关闭中。")
                if callable(on_timeout):
                    on_timeout()  # 调用用户提供的回调函数

        self.executor.shutdown(wait=False)
        if show_log:
            self.logger.info("线程池已关闭。")

    def is_stopped(self):
        """判断线程池是否已停止。

        Returns:
            bool: 如果线程池已停止，返回 True；否则返回 False。
        """
        return self.stop_event.is_set()
