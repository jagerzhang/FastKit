# 任务管理

支持定时任务、后台线程任务，其中定时任务基于 APScheduler 实现。任务池已和框架绑定启动，可以实现快速在本地后台启动任务调度。

## 初始化
```python
from os import getenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastkit.executor import Scheduler, ThreadPoolExecutor

redis_host = getenv("flyer_redis_host")
REDIS_CONFIG = None
if redis_host:
    redis_port = int(getenv("flyer_redis_port", "6379"))
    redis_pass = getenv("flyer_redis_pass", "")
    redis_db = int(getenv("flyer_redis_db", "10"))
    REDIS_CONFIG = {
        "host": redis_host,
        "port": redis_port,
        "passwd": redis_pass,
        "database": redis_db
    }

max_threads = int(getenv("flyer_threads", "5"))
# 线程型后台任务调度
background_scheduler: BackgroundScheduler = Scheduler(
    redis_config=REDIS_CONFIG,
    name="fastflyer",
    scheduler_type="background",
    logger=logger,
    auto_start=False,
    executor_type="threadpool",
    pool_size=max_threads)

# 协程型后台任务调度
asyncio_scheduler: AsyncIOScheduler = Scheduler(redis_config=REDIS_CONFIG,
                                                name="fastflyer",
                                                scheduler_type="asyncio",
                                                logger=logger,
                                                auto_start=False,
                                                executor_type="threadpool",
                                                pool_size=max_threads)

# 线程池后台任务
threadpool = ThreadPoolExecutor(redis_config=REDIS_CONFIG)
```

## 定时调度同步方法

```python
def customfunc():
    print("hello world!")

# single_job 为 True 的时候将执行单实例单进程任务（需要设置redis配置，方能多实例/进程互斥）
background_scheduler.add_job(func=customfunc, "interval", seconds=5, single_job=True)
```

## 定时调度异步方法

```python
async def customfunc():
    print("hello world!")

# single_job 为 True 的时候将执行单实例单进程任务（需要设置redis配置，方能多实例/进程互斥）
asyncio_scheduler.add_job(func=customfunc, "interval", seconds=5, id="customjob")
```

## 启动后台线程任务

```python
"""示例任务
"""
# 方式1：采用装饰器方式添加任务
@threadpool.submit(single_job=True)  # single_job 为 True 的时候全局只会有一个任务执行，其他的将等待锁释放
def hello_world_thread():
    # 直到线程池停止才结束循环
    while not threadpool.is_stopped():
        print("hello world by threadpool every 5 senconds!")
        threadpool.sleep(5)


# 方式2：显式提交任务方式
threadpool.submit_task(hello_world_thread, single_job=True)
```
