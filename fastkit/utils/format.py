# -*- coding: utf-8 -*-
"""格式化类
"""
import base64
import re


def split_list(src_list, length=3, tmp_list=None):
    """列表按长度切分
    """
    if tmp_list is None:
        tmp_list = []

    if len(src_list) <= length:
        tmp_list.append(src_list)
        return tmp_list

    else:
        tmp_list.append(src_list[:length])
        return split_list(src_list[length:], length, tmp_list)


def is_base64(string):
    """
    判断是不是Base64加密
    """
    try:
        base64.b64decode(string)
        return True
    except Exception:  # pylint: disable=broad-except
        pass

    try:
        base64.b64decode(string[2:-1])
        return True

    except Exception:  # pylint: disable=broad-except
        pass

    return False


def base64decode(content):
    """Base64解码，兼容不同版本客户端
    """
    if not is_base64(content):
        return content

    # for Python3 Client
    if re.match(r"^b'", content):
        return base64.b64decode(content[2:-1])

    # for Python2 Client
    else:
        return base64.b64decode(content)


def string_to_list(content, length=2048, charact="utf-8"):
    """字符串按指定编码长度切分(默认UTF-8)
    """
    if charact:
        try:
            content = content.encode(charact, errors="ignore")
        except (AttributeError, UnicodeDecodeError):
            pass

    split_list = []
    for item in range(0, len(content), length):
        item_content = content[item:item + length]
        if charact:
            try:
                item_content = item_content.decode(charact, errors="ignore")
            except (AttributeError, UnicodeDecodeError):
                pass
        split_list.append(item_content)

    return split_list


def filter_none_item(src_list, verify=False):
    """去掉列表中的空元素和重复元素
    """
    if isinstance(src_list, list):
        try:
            new_list = list(set(src_list))
            new_list.sort(key=src_list.index)
            return list(filter(None, new_list))

        # 类型错误[["a","b"]]
        except TypeError:
            # 开启验证则返回错误
            if verify:
                return False

            return src_list

    elif not src_list and verify:
        return False

    return src_list
