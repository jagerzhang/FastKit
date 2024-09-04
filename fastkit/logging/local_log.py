# -*- coding: utf-8 -*-
"""
本地日志
"""

from os import path, makedirs
import logging
from logging import Logger, StreamHandler, FileHandler, Formatter, warning

# 本地默认日志格式
LOG_FORMAT = "%(asctime)s.%(msecs)03d | %(levelname)s | %(module)s:%(lineno)d | %(message)s"
LOCAL_LOGGER_INST = {}


def get_logger(logger_name: str = "default",
               file_log_level=None,
               console_log_level=None,
               log_path: str = "",
               log_color: bool = True,
               log_format: str = LOG_FORMAT) -> Logger:
    global LOCAL_LOGGER_INST
    if logger_name in LOCAL_LOGGER_INST:
        return LOCAL_LOGGER_INST[logger_name]

    console_log_level = console_log_level or "INFO"
    file_log_level = file_log_level or "INFO"

    # 创建logger
    logger = logging.getLogger(logger_name)
    if not logger.handlers:  # 检查是否已经存在处理器
        logger.setLevel(logging.DEBUG)  # 设置logger的最低级别

        # 创建控制台处理器
        console_handler = StreamHandler()
        console_handler.setLevel(
            getattr(logging, console_log_level.upper(), logging.INFO))
        console_formatter = Formatter(log_format)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # 如果指定了日志路径，则创建文件处理器
        if log_path:
            try:
                makedirs(log_path, exist_ok=True)
            except Exception as err:  # pylint: disable=broad-except
                warning(f"日志目录创建失败：{err}，已重置为当前目录")
                log_path = ""

        if log_path:
            log_file = path.join(log_path, "error.log")
            file_handler = FileHandler(log_file)
            file_handler.setLevel(
                getattr(logging, file_log_level.upper(), logging.INFO))
            file_formatter = Formatter(log_format)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

    LOCAL_LOGGER_INST[logger_name] = logger
    return logger
