from os import getenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastkit.logging import get_logger

SCHEDULERS = {}


def get_scheduler(name: str = "default",
                  scheduler_type: str = "background",
                  logger: object = None,
                  auto_start: bool = True,
                  timezone: str = None) -> BackgroundScheduler:
    """
    生成APS任务调度实例

    Args:
        name (str, optional): 调度器名称. Defaults to "default".
        scheduler_type (str, optional): 调度器类型，默认 background 对应 BackgroundScheduler，asyncio 对应 AsyncIOScheduler.
        logger (object, optional): 自定义日志. Defaults to None.
        auto_start (bool, optional): 是否自动启动. Defaults to True.
        timezone (str, optional): 指定时区，默认未系统环境变量TZ，若未设置为为 Shanghai，. Defaults to None.

    Raises:
        ValueError: 类型错误

    Returns:
        BackgroundScheduler: Aps实例对象
    """
    global SCHEDULERS
    if scheduler_type not in SCHEDULERS:
        SCHEDULERS[scheduler_type] = {}

    if name not in SCHEDULERS.get(scheduler_type, {}):
        timezone = timezone or getenv.get("TZ", "Asia/Shanghai")
        logger = logger or get_logger(logger_name="console")
        if scheduler_type == "background":
            SCHEDULERS[scheduler_type][name] = BackgroundScheduler(
                timezone=timezone, logger=logger)
        elif scheduler_type == "asyncio":
            SCHEDULERS[scheduler_type][name] = AsyncIOScheduler(
                timezone=timezone logger=logger)
        else:
            raise ValueError("Unsupported scheduler type")

    scheduler: BackgroundScheduler = SCHEDULERS[scheduler_type][name]
    if not scheduler.running and auto_start:
        scheduler.start()

    return scheduler
