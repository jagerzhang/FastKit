#!/usr/bin/env  python
# -*- coding: utf-8 -*-

import socket


def get_host_ip():
    """
    获取实例IP地址
    """
    try:
        socket_fd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_fd.connect(("www.qq.com", 80))
        host_ip = socket_fd.getsockname()[0]
        socket_fd.close()
    except Exception:  # pylint: disable=broad-except
        host_ip = "0.0.0.0"

    return host_ip
