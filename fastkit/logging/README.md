# 日志打印

```python
from fastkit.logging import logger # 默认做过实例化，可直接使用

# 打印文本
logger.debug("DEBUG级别")
logger.info("INFO级别")
logger.warning("WARN级别")
logger.error("ERROR级别")

#  远程日志：TODO
