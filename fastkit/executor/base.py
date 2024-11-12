import time
import inspect
from threading import Event
from site import getsitepackages

site_path = getsitepackages()[0]


def get_func_id(func, prefix="interval", args=None, kwargs=None):
    """
    获取函数唯一 ID。

    Args:
        func (callable): 需要获取 ID 的函数对象。
        trigger (str): 触发器类型，默认为 "interval"。
        args (tuple, optional): 函数执行参数，默认为 None。
        kwargs (dict, optional): 函数执行关键字参数，默认为 None。

    Returns:
        str: 函数的唯一 ID。
    """
    source_info = inspect.getsourcefile(func).replace(f"{site_path}/", "")
    line_number = inspect.getsourcelines(func)[1]
    func_id = f"{prefix}>{func.__name__}@{source_info}:{line_number}"
    if args:
        func_id += f"#{args}"
    if kwargs:
        func_id += f"#{kwargs}"
    return func_id


class InterruptibleSleep:
    """可中断的 sleep 函数。
    """

    def __init__(self):
        self.stop_event = Event()

    def sleep(self, seconds):
        """可中断的 sleep 函数"""
        for _ in range(int(seconds * 2)):  # 每0.1秒检查一次
            if self.stop_event.is_set():
                return
            time.sleep(0.5)  # 每0.1秒休眠一次

    def interrupt(self):
        """中断 sleep"""
        self.stop_event.set()

    def reset(self):
        """重置事件标志"""
        self.stop_event.clear()
