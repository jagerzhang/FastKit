"""不便分类的公共功能
"""
import random
import hashlib


def get_md5(content):
    """ 计算MD5
    """
    m = hashlib.md5()
    m.update(content.encode("UTF-8"))
    return m.hexdigest()


def get_random_str(randomlength=16):
    """
    生成一个指定长度的随机字符串
    """
    digits = "0123456789"
    ascii_letters = "abcdefghigklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    str_list = [
        random.choice(digits + ascii_letters) for i in range(randomlength)
    ]
    random_str = ''.join(str_list)
    return random_str
