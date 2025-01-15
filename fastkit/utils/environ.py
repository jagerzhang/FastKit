"""环境变量
"""

from os import getenv


class EnvObject:
    """
    环境变量对象
    """

    def __getattr__(self, name):
        # 返回一个 Env 对象，用于处理默认值
        return str(EnvProxy(name))

    def get(self, name, default=None):
        return getenv(name, default)


class EnvProxy:
    """
    环境变量代理
    """

    def __init__(self, name):
        self.name = name

    def __getitem__(self, default):
        # 获取环境变量的值，如果不存在则返回默认值
        return getenv(self.name, default)

    def __call__(self, default=None):
        # 获取环境变量的值，如果不存在则返回默认值
        return getenv(self.name, default)

    def __str__(self):
        # 直接返回环境变量的值
        return getenv(self.name, None)

    def get(self, default=None):
        """
        获取环境变量的值，如果不存在则返回默认值
        :param default: 默认值
        :return: 环境变量的值或默认值
        """
        return getenv(self.name, default)


if __name__ == "__main__":
    env = EnvObject()

    # 获取已存在的环境变量
    print(env.OLDPWD)  # 直接获取环境变量的值

    # 获取不存在的环境变量，使用小括号方式
    print(env.not_exist("小括号方式设置不存在的默认值"))  # 使用小括号方式获取默认值

    # 获取不存在的环境变量，使用中括号方式
    print(env.not_exist["中括号方式设置不存在的默认值"])  # 使用中括号方式获取默认值

    # 使用 get 方法获取不存在的环境变量
    print(env.get("not_exist", "get方法设置不存在的默认值"))  # 使用 get 方法获取默认值
