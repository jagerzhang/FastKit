# MySQL操作

- SQLAlchemy

```python
from fastkit.database import MySQL

# 初始化mysql连接对象
mysql_pool = MySQL(
    db_host, 
    db_port,
    db_database,
    db_user,
    db_pass,
    db_charset
)

# 获取session连接对象
session = mysql_pool.get_session()

# 获取table对象
table = mysql_pool.get_table(table_name)

# 可以进行相关的ORM操作，示例如下
data = session.query(table.c.id, table.c.name).filter(table.c.city == "shenzhen").all()

# 回收session会话
session.close()

# 关闭所有的链接，关闭连接池
mysql_pool.close(session)
```

- DataSet

官方文档：[https://dataset.readthedocs.io/en/latest/](https://dataset.readthedocs.io/en/latest/)

简单进行了封装，加入了重连、重试等机制（官方版本的`mysql_ping`未达预期），用法如下：

```python
# 在 项目 settings.py 初始化 DataBase（需要在七彩石或环境变量中配置初始化相关变量）
from fastkit.database import get_dataset_pool 
# 初始化 dataset 

class DataBase:
    # 如果启用 MySQL 请取消注释
    db_user = getenv("flyer_db_user", "root")
    db_pass = getenv("flyer_db_pass", "")
    db_host = getenv("flyer_db_host", "localhost")
    db_port = getenv("flyer_db_port", 3306)
    db_name = getenv("flyer_db_name", "flyer")
    db_chartset = getenv("flyer_db_chartset", "utf8")
    db_recycle_rate = int(getenv("flyer_db_recycle_rate", 900))
    db_pool_size = int(getenv("flyer_db_pool_size", 32))

    data_set = get_dataset_pool(db_host, db_port, db_name, db_user, db_pass,
                                db_recycle_rate, db_pool_size)

data_set = get_dataset_pool(db_user, db_pass, db_host, db_port, db_name)
table = data_set["表名"]

# 增删改查代码示例：
from dataset import Table
from <app>.settings import DataBase


class DemoClass:
    """
    演示代码
    """
    def __init__(self) -> None:
        # 定义为 Table，让IDE可以自动提示函数
        self.db_set: Table = DataBase.data_set["表名"]

    def upsert(self):
        """
        插入或更新数据
        """
        row = {"key_item": 0, "item1": 1, "item2": 2}
        self.db_set.upsert(row, keys=["key_item"])

    def upsert_many(self):
        """
        批量插入或更新数据
        """
        row = [{"key_item": 0, "item1": 1, "item2": 2}, {"key_item": 1, "item1": 2, "item2": 3}]
        self.db_set.upsert_many(row, keys=["key_item"])

    def select(self):
        """
        查询数据
        """
        row = {"key_item": 0, "item1": 1, "item2": 2}
        row["_limit"] = 100
        row["_offset"] = 0
        row["order_by"] = "key_item"
        result = self.db_set.find(**row)
        data = [item for item in result]
        print(data)

    def select_one(self):
        """
        查询1条数据
        """
        row = {"key_item": 0, "item1": 1, "item2": 2}
        row["order_by"] = "key_item"
        result = self.db_set.find_one(**row)
        print(result)

    def delete(self):
        """
        删除数据
        """
        row = {"key": "value"}
        result = self.db_set.delete(**row)

        if result == 0:
            print("未匹配到数据")
        
        print(result)
```
