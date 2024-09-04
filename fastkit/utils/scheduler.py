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
    """获取任务调度器
    注：同名调度器将被复用
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
