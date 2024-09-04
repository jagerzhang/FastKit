# HTTP 工具包

- 基于 HTTPx 构建同步或异步 HTTP 请求，支持失败重试和日志记录，功能特性和使用习惯和 requests 基本保持一致。
- 提供 HTTP 状态码定义

[TOC]

## HTTP 客户端

### 快速使用

直接使用引用默认初始化的客户端对象，无需执行初始化。

#### 同步请求
在线程开发模式中，推荐使用同步请求。

```python
from fastkit.logging import logger
from fastkit.httpx import requests

# 变量定义略
resp = requests.get(url=url, json=payload, headers=headers)
if resp.status_code != 200:
    logger.error("请求失败")
# 其他内容略
```

#### 异步请求

在协程开发模式中，须使用异步请求。
```python
from fastkit.logging import logger
from fastkit.httpx import aiorequests

# 变量定义略
async def test():
  resp = await aiorequests.get(url=url, json=payload, headers=headers)
  if resp.status_code != 200:
      logger.error("请求失败")
  # 其他内容略
```

### 进阶使用

#### 同步请求
```python
from fastkit.httpx import Client

# 自定义参数
custom_config = {
    "stop_max_attempt_number": 3,  # 最大重试 3 次
    "stop_max_delay": 60,  # 最大重试耗时 60 s
    "wait_exponential_multiplier": 2,  # 重试间隔时间倍数 2s、4s、8s...
    "wait_exponential_max": 10  # 最大重试间隔时间 10s
}

client = Client(**custom_config)
# 发起 GET 请求示例
url = "https://httpbin.org/get"
headers = {"User-Agent": "My User Agent"}
params = {"param1": "value1", "param2": "value2"}
response = client.get(url, headers=headers, params=params)
print(response.status_code)
print(response.text)
```

#### 异步请求
```python
import asyncio
from fastkit.httpx import AsyncClient

# 可选重试参数
custom_config = {
    "stop_max_attempt_number": 3,  # 最大重试 3 次
    "stop_max_delay": 60,  # 最大重试耗时 60 s
    "wait_exponential_multiplier": 2,  # 重试间隔时间倍数 2s、4s、8s...
    "wait_exponential_max": 10  # 最大重试间隔时间 10s
}

async def test_requests():
    # 创建 Requests 实例
    requests_instance = AsyncClient(**custom_config)

    # 发起 GET 请求示例
    url = "https://httpbin.org/get"
    headers = {"User-Agent": "My User Agent"}
    params = {"param1": "value1", "param2": "value2"}
    response = await requests_instance.get(url,
                                            headers=headers,
                                            params=params)
    print(response.status_code)
    print(response.text)

    # 发起 POST 请求示例
    url = "https://httpbin.org/post"
    data = {"key": "value"}
    response = await requests_instance.post(url, json=data)
    print(response.status_code)
    print(response.text)

asyncio.run(test_requests())
```

#### 自定义重试

除了上述可以设置重试次数、间隔等机制之外，还可以继续自定义发起重试的条件。

```python
from urllib3.exceptions import HTTPError, ResponseError, NewConnectionError
from fastkit.httpx import Client

def retry_by_result(response: Response) -> bool:
    """根据响应内容判断是否重试

    Args:
        response (Response): 响应对象
    
    Returns:
        bool: True Or False
    """
    if response is None:
        logger.warning(f"请求失败，返回结果为空, 重试中...")
        return True

    if response.status_code in [429, 500, 502, 503, 504]:
        logger.warning(f"请求异常，状态码：{response.status_code}, \
日志ID： {response.headers.get('x-request-id', 'null')}，响应内容：{response.text}, 开始重试..."
                       )
        return True

    return False

# 自定义重试策略
retry_config = {
    "stop_max_attempt_number": 3,  # 最大重试 3 次
    "stop_max_delay": 60,  # 最大重试耗时 60 s
    "wait_exponential_multiplier": 2,  # 重试间隔时间倍数 2s、4s、8s...
    "wait_exponential_max": 10,  # 最大重试间隔时间 10s
    "retry_by_result": retry_by_result, # 根据结果重试函数
    "retry_by_except": (HTTPError, ResponseError, NewConnectionError) # 根据异常重试函数
}
client = Client(**retry_config)
```
**预埋自定义设置**

可以在初始化Client的时候传入任意符合HTTPx插件的请求参数，包括请求超时、自定义头部等：

```python
from fastkit.httpx import Client
client = Client(timeout=60, headers={"content-type": "application/json"})
```

## HTTP 状态码
基于 starlette ，用于 HTTP 服务框架中返回给客户端的 Body 状态码。

### 正常类返回码：20x

| 状态码   | 变量名                  | 说明                     |
|----------|-------------------------|--------------------------|
| 200      | HTTP_200_OK            | 请求成功                 |
| 201      | HTTP_201_CREATED       | 资源创建成功             |
| 202      | HTTP_202_ACCEPTED      | 请求已接受               |
| 203      | HTTP_203_NON_AUTHORITATIVE_INFORMATION | 非权威信息     |
| 204      | HTTP_204_NO_CONTENT    | 无内容返回               |
| 205      | HTTP_205_RESET_CONTENT | 重置内容                 |
| 206      | HTTP_206_PARTIAL_CONTENT | 部分内容返回           |
| 207      | HTTP_207_MULTI_STATUS  | 多状态                   |
| 208      | HTTP_208_ALREADY_REPORTED | 已报告                 |
| 226      | HTTP_226_IM_USED       | IM已使用                 |

### 跳转类返回码：30x

| 状态码   | 变量名                  | 说明                     |
|----------|-------------------------|--------------------------|
| 300      | HTTP_300_MULTIPLE_CHOICES | 多种选择               |
| 301      | HTTP_301_MOVED_PERMANENTLY | 资源永久重定向         |
| 302      | HTTP_302_FOUND          | 资源临时重定向           |
| 303      | HTTP_303_SEE_OTHER      | 查看其他                 |
| 304      | HTTP_304_NOT_MODIFIED   | 资源未修改               |
| 305      | HTTP_305_USE_PROXY      | 使用代理访问             |
| 306      | HTTP_306_RESERVED       | 保留                     |
| 307      | HTTP_307_TEMPORARY_REDIRECT | 临时重定向             |
| 308      | HTTP_308_PERMANENT_REDIRECT | 永久重定向             |

### 客户端错误返回码：40x

| 状态码   | 变量名                  | 说明                     |
|----------|-------------------------|--------------------------|
| 400      | HTTP_400_BAD_REQUEST    | 请求错误                 |
| 401      | HTTP_401_UNAUTHORIZED   | 未授权                   |
| 402      | HTTP_402_PAYMENT_REQUIRED | 需要付款               |
| 403      | HTTP_403_FORBIDDEN      | 禁止访问                 |
| 404      | HTTP_404_NOT_FOUND      | 资源未找到               |
| 405      | HTTP_405_METHOD_NOT_ALLOWED | 方法不允许             |
| 406      | HTTP_406_NOT_ACCEPTABLE | 不可接受的内容           |
| 407      | HTTP_407_PROXY_AUTHENTICATION_REQUIRED | 需要代理认证 |
| 408      | HTTP_408_REQUEST_TIMEOUT | 请求超时                 |
| 409      | HTTP_409_CONFLICT       | 冲突                     |
| 410      | HTTP_410_GONE           | 资源不可用               |
| 411      | HTTP_411_LENGTH_REQUIRED | 需要内容长度             |
| 412      | HTTP_412_PRECONDITION_FAILED | 前提条件失败         |
| 413      | HTTP_413_PAYLOAD_TOO_LARGE | 负载过大               |
| 414      | HTTP_414_URI_TOO_LONG   | URI过长                 |
| 415      | HTTP_415_UNSUPPORTED_MEDIA_TYPE | 不支持的媒体类型     |
| 416      | HTTP_416_RANGE_NOT_SATISFIABLE | 范围不符合要求       |
| 417      | HTTP_417_EXPECTATION_FAILED | 预期失败               |
| 418      | HTTP_418_I_AM_A_TEAPOT  | 我是茶壶（服务器拒绝冲泡咖啡)  |
| 421      | HTTP_421_MISDIRECTED_REQUEST | 误导的请求             |
| 422      | HTTP_422_UNPROCESSABLE_ENTITY | 无法处理的实体         |
| 423      | HTTP_423_LOCKED         | 已锁定                   |
| 424      | HTTP_424_FAILED_DEPENDENCY | 依赖关系失败           |
| 425      | HTTP_425_TOO_EARLY      | 太早                     |
| 426      | HTTP_426_UPGRADE_REQUIRED | 需要升级协议           |
| 428      | HTTP_428_PRECONDITION_REQUIRED | 需要前提条件         |
| 429      | HTTP_429_TOO_MANY_REQUESTS | 请求过多               |
| 431      | HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE | 请求头字段过大  |
| 451      | HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS | 由于法律原因不可用 |

### 服务端错误返回码：50x

| 状态码   | 变量名                  | 说明                     |
|----------|-------------------------|--------------------------|
| 500      | HTTP_500_INTERNAL_SERVER_ERROR | 服务器内部错误       |
| 501      | HTTP_501_NOT_IMPLEMENTED | 功能未实现               |
| 502      | HTTP_502_BAD_GATEWAY    | 网关错误                 |
| 503      | HTTP_503_SERVICE_UNAVAILABLE | 服务不可用             |
| 504      | HTTP_504_GATEWAY_TIMEOUT | 网关超时                 |
| 505      | HTTP_505_HTTP_VERSION_NOT_SUPPORTED | 不支持的HTTP版本   |
| 506      | HTTP_506_VARIANT_ALSO_NEGOTIATES | 可协商的变体       |
| 507      | HTTP_507_INSUFFICIENT_STORAGE | 存储空间不足         |
| 508      | HTTP_508_LOOP_DETECTED  | 检测到循环               |
| 510      | HTTP_510_NOT_EXTENDED   | 未扩展                   |
| 511      | HTTP_511_NETWORK_AUTHENTICATION_REQUIRED | 需要网络认证     |

### 第三方服务错误返回码：60x

| 状态码   | 变量名                          | 说明                           |
|----------|---------------------------------|--------------------------------|
| 600      | HTTP_600_THIRD_PARTY_ERROR      | 请求第三方服务错误              |
| 601      | HTTP_601_THIRD_PARTY_STATUS_ERROR | 请求第三方服务返回状态码异常   |
| 602      | HTTP_602_THIRD_PARTY_DATA_ERROR | 请求第三方服务返回数据异常       |
| 603      | HTTP_603_THIRD_PARTY_UNAVAILABLE_ERROR | 请求第三方服务不可用异常    |
| 604      | HTTP_604_THIRD_PARTY_TIMEOUT_ERROR | 请求第三方服务超时异常         |
| 605      | HTTP_605_THIRD_PARTY_NEWORK_ERROR | 请求第三方服务网络异常          |
| 606      | HTTP_606_THIRD_PARTY_RETRY_ERROR | 第三方服务返回不符合预期重试多次还是失败 |


### WebSocket状态码

| 状态码   | 变量名                              | 说明                     |
|----------|-------------------------------------|--------------------------|
| 1000     | WS_1000_NORMAL_CLOSURE              | 正常关闭                 |
| 1001     | WS_1001_GOING_AWAY                  | 正在离开                 |
| 1002     | WS_1002_PROTOCOL_ERROR              | 协议错误                 |
| 1003     | WS_1003_UNSUPPORTED_DATA            | 不支持的数据             |
| 1005     | WS_1005_NO_STATUS_RCVD              | 未收到状态               |
| 1006     | WS_1006_ABNORMAL_CLOSURE            | 异常关闭                 |
| 1007     | WS_1007_INVALID_FRAME_PAYLOAD_DATA  | 无效的帧载荷数据         |
| 1008     | WS_1008_POLICY_VIOLATION            | 策略违规                 |
| 1009     | WS_1009_MESSAGE_TOO_BIG             | 消息过大                 |
| 1010     | WS_1010_MANDATORY_EXT               | 强制扩展                 |
| 1011     | WS_1011_INTERNAL_ERROR              | 内部错误                 |
| 1012     | WS_1012_SERVICE_RESTART             | 服务重启                 |
| 1013     | WS_1013_TRY_AGAIN_LATER             | 请稍后重试               |
| 1014     | WS_1014_BAD_GATEWAY                 | 网关错误                 |
| 1015     | WS_1015_TLS_HANDSHAKE               | TLS握手                 |
