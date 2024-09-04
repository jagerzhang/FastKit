import time
import json
from inspect import signature
from uuid import uuid4
from httpx import (Client as HttpxClient, AsyncClient as HttpxAsyncClient,
                   Response, __version__ as httpx_version, ConnectError,
                   ReadError, WriteError, NetworkError)
from tenacity import (retry, RetryError, stop_any, stop_after_delay,
                      stop_after_attempt, wait_exponential, retry_if_result,
                      retry_if_exception_type, retry_any)
from fastkit.logging import logger
from fastkit.__info__ import __version__ as fastkit_version
from .status import (HTTP_200_OK, HTTP_600_THIRD_PARTY_ERROR,
                     HTTP_605_THIRD_PARTY_NEWORK_ERROR,
                     HTTP_606_THIRD_PARTY_RETRY_ERROR)


def default_retry_by_result(response: Response) -> bool:
    """根据响应内容判断是否重试

    Args:
        response (Response): 响应对象

    Returns:
        bool: True Or False
    """
    if response is None:
        logger.warning("请求失败，返回结果为空, 重试中...")
        return True

    if response.status_code in [429, 500, 502, 503, 504]:
        logger.warning(f"请求异常，状态码：{response.status_code}, \
日志ID： {response.headers.get('x-request-id', 'null')}，响应内容：{response.text}, 开始重试..."
                       )
        return True

    return False

    # ================ HTTPx 配置 ================


def get_default_client_config():
    """
    获取默认客户端配置
    """
    return {
        "follow_redirects": True,
        "verify": False,
        "headers": {
            "user-agent":
            f"FastKit-{fastkit_version}/Httpx-Client-{httpx_version}",
            "x-request-id": str(uuid4()),
        },
        "timeout": 60
    }


def get_retry_config(**kwargs):
    """初始化重试配置
    """
    # 最大重试耗时为60s
    stop_max_delay = int(kwargs.get("stop_max_delay", 60))
    # 最多重试3次
    stop_max_attempt_number = kwargs.get("stop_after_attempt", 3)
    # 重试间隔时间倍数，默认为2，即2、4、8、16指数增长
    wait_multiplier = int(kwargs.get("wait_exponential_multiplier", 2))
    # 重试间隔时间的最大值为10s
    wait_max = int(kwargs.get("wait_exponential_max", 10))
    retry_by_result = kwargs.get("retry_by_result", default_retry_by_result)
    retry_by_except = kwargs.get(
        "retry_by_except", (ConnectError, ReadError, WriteError, NetworkError))

    # 默认重试机制
    retry_config = {
        "wait":
        wait_exponential(multiplier=wait_multiplier, max=wait_max),
        "stop":
        stop_any(
            (stop_after_delay(stop_max_delay)),
            stop_after_attempt(stop_max_attempt_number),
        ),
        "retry":
        retry_any(
            retry_if_result(retry_by_result),
            retry_if_exception_type(retry_by_except),
        )
    }
    # 重试 参数自适应
    retry_kwargs = {
        key: value
        for key, value in kwargs.items()
        if key in signature(retry).parameters.keys()
    }
    retry_config.update(retry_kwargs)
    return retry_config


class Client(HttpxClient):
    """
    HTTP 请求增强方法
    """

    def __init__(self, report_log: bool = True, **kwargs) -> HttpxClient:
        """
        report_log: 是否上报或打印日志
        retry_config 支持 tenacity 重试参数，说明如下：
        tenacity 库提供了非常丰富的重试（retry）配置选项，下面将列出 retry 装饰器中所有可选参数并进行简要说明：
            stop: 定义应何时停止重试的策略。可以使用内置的 stop_* 函数，也可以使用自定义的 callable 对象。例如，使用
            stop_after_attempt(3) 可以定义最多尝试 3 次请求后停止重试。默认情况下，stop 选项设置为 stop_never，表示无限重试。

            wait: 定义重试之间的等待时间。可以使用内置的 wait_* 函数，也可以使用自定义的 callable 对象。

            before: 可选的回调函数，在每次进行重试之前执行。回调函数的参数是 RetryCallState 对象。

            after: 可选的回调函数，在每次重试之后执行。回调函数的参数是 RetryCallState 对象。

            retry: 可选的回调函数，在每次重试之前执行。如果返回的结果是 False，则终止重试。
            回调函数的参数是 RetryCallState 对
            象。

            before_sleep: 在等待重试次数之前执行的可选回调函数。在等待发生之前，每次迭代周期都会执行此回调。
            回调函数的参数是 RetryCallState 对象。可以使用它来加入自定义日志记录、指令或测试传递信息。

            after_retry: 可选的回调函数，在每次重试时执行。回调函数的参数是 RetryCallState 对象。

            retry_error_callback: 可选的回调函数，在重试策略发生故障时执行（例如，无法在规定时间内停止)，
            回调函数的参数是 RetryCallState 对象。

            reraise: 如果在 retry 过程中遇到了未处理的异常，则该选项指定是否 reraise 异常。默认值为 True，即立即 reraise。

            before_retry: “只要在 retry 发生时，无论是通过异常还是通过指数退避，都将在 retry 前调用”。
            将在 retry=retry 的类型中添加此回调。

            retry_error_cls: 指定应当被 classified（分类）字符串的想弄死。当在 retry 中间产生一个重试错误时，
            应当将它识别为这些字符串之一。
        """
        # HTTPx 参数自适应
        client_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key in signature(HttpxClient.__init__).parameters.keys()
        }
        client_config = get_default_client_config()
        client_config.update(client_kwargs)
        self.client = HttpxClient(**client_config)
        self.headers = self.client.headers

        # 重试 参数自适应
        retry_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key in signature(retry).parameters.keys()
        }
        self.retry_config = get_retry_config(**retry_kwargs)
        self.report_log = report_log

    def get(self, url, params=None, **kwargs) -> Response:
        """
        发送一个 GET 请求。

        Args:
            url: 请求的 URL。
            params: （可选）查询字符串的参数，可以是字典、元组列表或字节。
            **kwargs: ``request`` 方法可接受的可选参数。

        Returns:
            :class:`Response <Response>` 对象
        """
        return self.request("get", url, params=params, **kwargs)

    def options(self, url, **kwargs):
        """
        发送一个 OPTIONS 请求。

        Args:
            url: 请求的 URL。
            **kwargs: ``request`` 方法可接受的可选参数。

        Returns:
            :class:`Response <Response>` 对象
        """
        return self.request("options", url, **kwargs)

    def head(self, url, **kwargs) -> Response:
        """
        发送一个 HEAD 请求。

        Args:
            url: 请求的 URL。
            **kwargs: ``request`` 方法可接受的可选参数。如果未提供 `allow_redirects`，将设置为 `False`
            （与默认的 :meth:`request` 行为相反）。

        Returns:
            :class:`Response <Response>` 对象
        """
        kwargs.setdefault("follow_redirects", False)
        return self.request("head", url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs) -> Response:
        """
        发送一个 POST 请求。

        Args:
            url: 请求的 URL。
            data: （可选）请求体的数据，可以是字典、元组列表、字节或类文件对象。
            json: （可选）要在请求体中发送的可序列化为 JSON 的 Python 对象。
            **kwargs: ``request`` 方法可接受的可选参数。

        Returns:
            :class:`Response <Response>` 对象
        """
        return self.request("post", url, data=data, json=json, **kwargs)

    def put(self, url, data=None, **kwargs) -> Response:
        """
        发送一个 PUT 请求。

        Args:
            url: 请求的 URL。
            data: （可选）请求体的数据，可以是字典、元组列表、字节或类文件对象。
            **kwargs: ``request`` 方法可接受的可选参数。

        Returns:
            :class:`Response <Response>` 对象
        """
        return self.request("put", url, data=data, **kwargs)

    def patch(self, url, data=None, **kwargs) -> Response:
        """
        发送一个 PATCH 请求。

        Args:
            url: 请求的 URL。
            data: （可选）请求体的数据，可以是字典、元组列表、字节或类文件对象。
            **kwargs: ``request`` 方法可接受的可选参数。

        Returns:
            :class:`Response <Response>` 对象
        """
        return self.request("patch", url, data=data, **kwargs)

    def delete(self, url, **kwargs) -> Response:
        """
        发送一个 DELETE 请求。

        Args:
            url: 请求的 URL。
            **kwargs: ``request`` 方法可接受的可选参数。

        Returns:
            :class:`Response <Response>` 对象
        """
        return self.request("delete", url, **kwargs)

    def request(self, method: str, url: str, *args, **kwargs) -> Response:
        """发送请求

        Args:
            method: 请求的方法，可以是 ``GET``、``OPTIONS``、``HEAD``、``POST``、``PUT``、``PATCH`` 或 ``DELETE``。
            url: 请求的 URL。
            params: （可选）查询字符串的参数，可以是字典、元组列表或字节。
            data: （可选）请求体的数据，可以是字典、元组列表、字节或类文件对象。
            json: （可选）要在请求体中发送的可序列化为 JSON 的 Python 对象。
            headers: （可选）要与请求一起发送的 HTTP 头的字典。
            cookies: （可选）要与请求一起发送的 Cookie 的字典或 CookieJar 对象。
            files: （可选）用于多部分编码上传的 ``'name': file-like-objects``（或 ``{'name': file-tuple}``）的字典。
                ``file-tuple`` 可以是 2 元组 ``('filename', fileobj)``、3 元组 ``('filename', fileobj, 'content_type')``
                或者 4 元组 ``('filename', fileobj, 'content_type', custom_headers)``。
                其中，``'content-type'`` 是给定文件的内容类型的字符串，``custom_headers`` 是一个类似字典的对象，包含额外的文件
                头。
            auth: （可选）启用基本/摘要/自定义 HTTP 身份验证的元组。
            timeout: （可选）在放弃之前，等待服务器发送数据的秒数，可以是浮点数或者包含连接超时和读取超时的元组。
            allow_redirects: （可选）布尔值。启用/禁用 GET/OPTIONS/POST/PUT/PATCH/DELETE/HEAD 重定向。默认为 ``True``。
            proxies: （可选）将协议映射到代理 URL 的字典。
            verify: （可选）要么是布尔值，控制是否验证服务器的 TLS 证书；要么是字符串，必须是要使用的 CA bundle 的路径。默认为
            ``True``。
            stream: （可选）如果为 ``False``，则立即下载响应内容。
            cert: （可选）如果是字符串，则为 SSL 客户端证书文件的路径（.pem）。如果是元组，则为（'cert'，'key'）对。

        Returns:
            :class:`Response <Response>` 对象
        """

        @retry(**self.retry_config)
        def _request(method: str, *args, **kwargs) -> Response:
            """
            注入重试机制的HTTP请求
            """
            return self.client.request(method.upper(), *args, **kwargs)

        request_start = time.perf_counter()
        body = kwargs.get("json") or kwargs.get("params") or kwargs.get(
            "data", "")
        out_body = json.dumps(body) if isinstance(body, dict) else str(body)

        headers = {**self.headers, **kwargs.get("headers", {})}
        kwargs["headers"] = headers

        req_log = {
            "direction": "out",
            "logId": headers.get("x-request-id", str(uuid4())),
            "response": {},
            "request": {
                "body": out_body[0:4096],
                "url": url,
                "method": method,
                "headers": json.dumps(headers)
            }
        }

        response = Response(status_code=HTTP_200_OK)
        response._content = {}

        try:
            response = _request(method, url, *args, **kwargs)

        except RetryError as err:
            response._content = f"请求第三方服务异常, 经过多次重复仍然无法成功，错误信息：{err}".encode()
            response.status_code = HTTP_606_THIRD_PARTY_RETRY_ERROR

        except ConnectionResetError as err:
            response._content = f"网络连接错误: {err}".encode()
            response.status_code = HTTP_605_THIRD_PARTY_NEWORK_ERROR

        except Exception as err:  # pylint: disable=broad-except
            response._content = f"请求第三方服务异常, 错误信息：{err}".encode()
            response.status_code = HTTP_600_THIRD_PARTY_ERROR

        finally:
            req_log["response"]["status_code"] = response.status_code
            req_log["response"]["headers"] = json.dumps(
                dict(response.headers.items()))
            # 图片类型忽略内容记录
            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image") and content_type:
                req_log["response"]["body"] = response.text[0:4096]

            request_end = time.perf_counter()
            req_log["latency"] = int((request_end - request_start) * 1000)

            if response:
                response.close()

        if self.report_log:
            logger.info(json.dumps(req_log))

        return response


class AsyncClient(HttpxAsyncClient):
    """
    HTTP 请求增强方法
    """

    def __init__(self, report_log: bool = True, **kwargs):
        """
        retry_config 支持 tenacity 重试参数，说明如下：
        tenacity 库提供了非常丰富的重试（retry）配置选项，下面将列出 retry 装饰器中所有可选参数并进行简要说明：
            stop: 定义应何时停止重试的策略。可以使用内置的 stop_* 函数，也可以使用自定义的 callable 对象。例如，使用
            stop_after_attempt(3) 可以定义最多尝试 3 次请求后停止重试。默认情况下，stop 选项设置为 stop_never，表示无限重试。

            wait: 定义重试之间的等待时间。可以使用内置的 wait_* 函数，也可以使用自定义的 callable 对象。

            before: 可选的回调函数，在每次进行重试之前执行。回调函数的参数是 RetryCallState 对象。

            after: 可选的回调函数，在每次重试之后执行。回调函数的参数是 RetryCallState 对象。

            retry: 可选的回调函数，在每次重试之前执行。如果返回的结果是 False，则终止重试。
            回调函数的参数是 RetryCallState 对
            象。

            before_sleep: 在等待重试次数之前执行的可选回调函数。在等待发生之前，每次迭代周期都会执行此回调。
            回调函数的参数是 RetryCallState 对象。可以使用它来加入自定义日志记录、指令或测试传递信息。

            after_retry: 可选的回调函数，在每次重试时执行。回调函数的参数是 RetryCallState 对象。

            retry_error_callback: 可选的回调函数，在重试策略发生故障时执行（例如，无法在规定时间内停止)，
            回调函数的参数是 RetryCallState 对象。

            reraise: 如果在 retry 过程中遇到了未处理的异常，则该选项指定是否 reraise 异常。默认值为 True，即立即 reraise。

            before_retry: “只要在 retry 发生时，无论是通过异常还是通过指数退避，都将在 retry 前调用”。
            将在 retry=retry 的类型中添加此回调。

            retry_error_cls: 指定应当被 classified（分类）字符串的想弄死。当在 retry 中间产生一个重试错误时，
            应当将它识别为这些字符串之一。
        """
        # HTTPx 参数自适应
        client_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key in signature(HttpxAsyncClient.__init__).parameters.keys()
        }
        client_config = get_default_client_config()
        client_config.update(client_kwargs)
        self.client = HttpxAsyncClient(**client_config)
        self.headers = self.client.headers

        # 重试 参数自适应
        retry_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key in signature(retry).parameters.keys()
        }
        self.retry_config = get_retry_config(**retry_kwargs)
        self.report_log = report_log

    async def get(self, url, params=None, **kwargs) -> Response:
        """
        发送一个 GET 请求。

        Args:
            url: 请求的 URL。
            params: （可选）查询字符串的参数，可以是字典、元组列表或字节。
            **kwargs: ``request`` 方法可接受的可选参数。

        Returns:
            :class:`Response <Response>` 对象
        """

        return await self.request("get", url, params=params, **kwargs)

    async def options(self, url, **kwargs) -> Response:
        """
        发送一个 OPTIONS 请求。

        Args:
            url: 请求的 URL。
            **kwargs: ``request`` 方法可接受的可选参数。

        Returns:
            :class:`Response <Response>` 对象
        """

        return await self.request("options", url, **kwargs)

    async def head(self, url, **kwargs) -> Response:
        """
        发送一个 HEAD 请求。

        Args:
            url: 请求的 URL。
            **kwargs: ``request`` 方法可接受的可选参数。如果未提供 `allow_redirects`，将设置为 `False`
            （与默认的 :meth:`request` 行为相反）。

        Returns:
            :class:`Response <Response>` 对象
        """

        kwargs.setdefault("follow_redirects", False)
        return await self.request("head", url, **kwargs)

    async def post(self, url, data=None, json=None, **kwargs) -> Response:
        """
        发送一个 POST 请求。

        Args:
            url: 请求的 URL。
            data: （可选）请求体的数据，可以是字典、元组列表、字节或类文件对象。
            json: （可选）要在请求体中发送的可序列化为 JSON 的 Python 对象。
            **kwargs: ``request`` 方法可接受的可选参数。

        Returns:
            :class:`Response <Response>` 对象
        """

        return await self.request("post", url, data=data, json=json, **kwargs)

    async def put(self, url, data=None, **kwargs) -> Response:
        """
        发送一个 PUT 请求。

        Args:
            url: 请求的 URL。
            data: （可选）请求体的数据，可以是字典、元组列表、字节或类文件对象。
            **kwargs: ``request`` 方法可接受的可选参数。

        Returns:
            :class:`Response <Response>` 对象
        """

        return await self.request("put", url, data=data, **kwargs)

    async def patch(self, url, data=None, **kwargs) -> Response:
        """
        发送一个 PATCH 请求。

        Args:
            url: 请求的 URL。
            data: （可选）请求体的数据，可以是字典、元组列表、字节或类文件对象。
            **kwargs: ``request`` 方法可接受的可选参数。

        Returns:
            :class:`Response <Response>` 对象
        """

        return await self.request("patch", url, data=data, **kwargs)

    async def delete(self, url, **kwargs) -> Response:
        """
        发送一个 DELETE 请求。

        Args:
            url: 请求的 URL。
            **kwargs: ``request`` 方法可接受的可选参数。

        Returns:
            :class:`Response <Response>` 对象
        """

        return await self.request("delete", url, **kwargs)

    async def request(self, method: str, url: str, *args,
                      **kwargs) -> Response:
        """发送请求

        Args:
            method: 请求的方法，可以是 ``GET``、``OPTIONS``、``HEAD``、``POST``、``PUT``、``PATCH`` 或 ``DELETE``。
            url: 请求的 URL。
            params: （可选）查询字符串的参数，可以是字典、元组列表或字节。
            data: （可选）请求体的数据，可以是字典、元组列表、字节或类文件对象。
            json: （可选）要在请求体中发送的可序列化为 JSON 的 Python 对象。
            headers: （可选）要与请求一起发送的 HTTP 头的字典。
            cookies: （可选）要与请求一起发送的 Cookie 的字典或 CookieJar 对象。
            files: （可选）用于多部分编码上传的 ``'name': file-like-objects``（或 ``{'name': file-tuple}``）的字典。
                ``file-tuple`` 可以是 2 元组 ``('filename', fileobj)``、3 元组 ``('filename', fileobj, 'content_type')``
                或者 4 元组 ``('filename', fileobj, 'content_type', custom_headers)``。
                其中，``'content-type'`` 是给定文件的内容类型的字符串，``custom_headers`` 是一个类似字典的对象，包含额外的文件
                头。
            auth: （可选）启用基本/摘要/自定义 HTTP 身份验证的元组。
            timeout: （可选）在放弃之前，等待服务器发送数据的秒数，可以是浮点数或者包含连接超时和读取超时的元组。
            allow_redirects: （可选）布尔值。启用/禁用 GET/OPTIONS/POST/PUT/PATCH/DELETE/HEAD 重定向。默认为 ``True``。
            proxies: （可选）将协议映射到代理 URL 的字典。
            verify: （可选）要么是布尔值，控制是否验证服务器的 TLS 证书；要么是字符串，必须是要使用的 CA bundle 的路径。默认为
                    ``True``。
            stream: （可选）如果为 ``False``，则立即下载响应内容。
            cert: （可选）如果是字符串，则为 SSL 客户端证书文件的路径（.pem）。如果是元组，则为（'cert'，'key'）对。

        Returns:
            :class:`Response <Response>` 对象
        """

        @retry(**self.retry_config)
        async def _request(method: str, *args, **kwargs) -> Response:
            """
            注入重试机制的HTTP请求
            """
            return await self.client.request(method.upper(), *args, **kwargs)

        request_start = time.perf_counter()
        body = kwargs.get("json") or kwargs.get("params") or kwargs.get(
            "data", "")
        out_body = json.dumps(body) if isinstance(body, dict) else str(body)

        headers = {**self.headers, **kwargs.get("headers", {})}
        kwargs["headers"] = headers

        req_log = {
            "direction": "out",
            "logId": headers.get("x-request-id", str(uuid4())),
            "response": {},
            "request": {
                "body": out_body[0:4096],
                "url": url,
                "method": method,
                "headers": json.dumps(headers)
            }
        }

        response = Response(status_code=HTTP_200_OK)
        response._content = {}

        try:
            response = await _request(method, url, *args, **kwargs)

        except RetryError as err:
            if hasattr(err.last_attempt, "result"):
                err = err.last_attempt.result()
            response._content = f"请求第三方服务异常, 经过多次重复仍然无法成功，错误信息：{err}".encode()
            response.status_code = HTTP_606_THIRD_PARTY_RETRY_ERROR

        except ConnectionResetError as err:
            response._content = f"网络连接错误: {err}".encode()
            response.status_code = HTTP_605_THIRD_PARTY_NEWORK_ERROR

        except Exception as err:  # pylint: disable=broad-except
            response._content = f"请求第三方服务异常, 错误信息：{err}".encode()
            response.status_code = HTTP_600_THIRD_PARTY_ERROR

        finally:
            req_log["response"]["status_code"] = response.status_code
            req_log["response"]["headers"] = json.dumps(
                dict(response.headers.items()))
            # 图片类型忽略内容记录
            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image") and content_type:
                req_log["response"]["body"] = response.text[0:4096]

            request_end = time.perf_counter()
            req_log["latency"] = int((request_end - request_start) * 1000)

        if self.report_log:
            logger.info(json.dumps(req_log))

        return response


if __name__ == "__main__":
    # 创建 request 实例
    request_instance = Client(report_log=True)

    # 发起 GET 请求示例
    GET = "https://httpbin.org/get"
    headers = {"User-Agent": "My User Agent"}
    params = {"param1": "value1", "param2": "value2"}
    response = request_instance.get(url=GET, headers=headers, params=params)
    print(response.status_code)
    print(response.text)

    # 发起 POST 请求示例
    POST = "https://httpbin.org/post"
    data = {"key": "value"}
    request_instance.headers.update({"User-Agent": "My User Agent3"})
    response = request_instance.post(url=POST, json=data)
    print(response.status_code)
    print(response.text)
    # exit()
    import asyncio

    async def test_requests():
        # 创建 Requests 实例
        requests_instance = AsyncClient(report_log=True)

        # # 发起 GET 请求示例
        # headers = {"User-Agent": "My User Agent"}
        # params = {"param1": "value1", "param2": "value2"}
        # response = await requests_instance.get(url=GET,
        #                                        headers=headers,
        #                                        params=params)
        # print(response.status_code)
        # print(response.text)

        # 发起 POST 请求示例
        data = {"key": "value"}
        requests_instance.headers.update({"a": "custom"})
        response = await requests_instance.post(url=POST, json=data)
        print(response.status_code)
        print(response.text)

    asyncio.run(test_requests())
