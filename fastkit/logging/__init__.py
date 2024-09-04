# -*- coding: utf-8 -*-
from os import getenv
from .local_log import get_logger

console_log_level = getenv("flyer_console_log_level", "info")
file_log_level = getenv("flyer_file_log_level", "warning")
log_path = getenv("flyer_log_path", "/var/log")

logger = get_logger(console_log_level=console_log_level,
                    file_log_level=file_log_level,
                    log_path=log_path)
