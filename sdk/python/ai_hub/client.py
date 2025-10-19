"""
AI Hub Platform Python SDK 客户端
提供与AI Hub API的完整交互功能
"""

import json
import time
from typing import Iterator, Optional, Dict, Any, List, Union
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import (
    AIHubError, APIError, AuthenticationError, RateLimitError,
    InvalidRequestError, InsufficientQuotaError, ModelNotFoundError,
    ConnectionError, TimeoutError
)
from .models import (
    ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChunk,
    Model, Usage, APIKey, QuotaInfo, UsageStats, Plan, Subscription
)


class AIHubClient:
    """AI Hub API 客户端"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.aihub.com/api/v1",
        timeout: int = 60,
        max_retries: int = 3,
        user_agent: str = None
    ):
        """
        初始化AI Hub客户端

        Args:
            api_key: API密钥
            base_url: API基础URL
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            user_agent: ��户代理字符串
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

        # 设置请求会话
        self.session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 设置默认请求头
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": user_agent or f"ai-hub-python/1.0.0"
        })

        # 子API客户端
        self.chat = ChatAPI(self)
        self.models = ModelsAPI(self)
        self.usage = UsageAPI(self)
        self.keys = KeysAPI(self)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Union[requests.Response, Iterator[bytes]]:
        """
        发送HTTP请求

        Args:
            method: HTTP方法
            endpoint: API端点
            json_data: JSON数据
            params: 查询参数
            stream: 是否流式响应

        Returns:
            响应对象或流式迭代器

        Raises:
            AIHubError: API相关错误
        """
        url = urljoin(self.base_url + "/", endpoint.lstrip('/'))

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                timeout=self.timeout,
                stream=stream
            )

            # 检查HTTP状态码
            if response.status_code == 401:
                raise AuthenticationError()
            elif response.status_code == 403:
                raise InsufficientQuotaError()
            elif response.status_code == 429:
                retry_after = response.headers.get('Retry-After')
                raise RateLimitError(retry_after=int(retry_after) if retry_after else None)
            elif response.status_code == 404:
                raise ModelNotFoundError(json_data.get('model', 'Unknown') if json_data else 'Unknown')
            elif not response.ok:
                self._handle_api_error(response)

            if stream:
                return response.iter_lines()
            else:
                return response

        except requests.exceptions.Timeout:
            raise TimeoutError()
        except requests.exceptions.ConnectionError:
            raise ConnectionError()
        except requests.exceptions.RequestException as e:
            raise AIHubError(f"Request failed: {str(e)}")

    def _handle_api_error(self, response: requests.Response):
        """处理API错误响应"""
        try:
            error_data = response.json()
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
            error_code = error_data.get('error', {}).get('code', 'unknown_error')
        except (json.JSONDecodeError, ValueError):
            error_message = response.text or 'Unknown error'
            error_code = 'unknown_error'

        raise APIError(
            message=error_message,
            error_code=error_code,
            status_code=response.status_code,
            response=response
        )

    def _parse_response(self, response: requests.Response, model_class):
        """解析响应数据"""
        try:
            data = response.json()

            # 处理不同的响应格式
            if 'data' in data:
                data = data['data']

            return model_class(**data)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            raise APIError(f"Failed to parse response: {str(e)}")

    def _parse_stream_chunk(self, line: bytes) -> Optional[ChatCompletionChunk]:
        """解析流式响应块"""
        if not line:
            return None

        try:
            line_str = line.decode('utf-8').strip()

            if line_str == 'data: [DONE]':
                return None

            if line_str.startswith('data: '):
                data_str = line_str[6:]  # 移除 'data: ' 前缀
                data = json.loads(data_str)

                # 处理不同的响应格式
                if 'data' in data:
                    data = data['data']

                return ChatCompletionChunk(**data)
        except (json.JSONDecodeError, ValueError, TypeError):
            # 忽略解析错误的行
            pass

        return None

    def close(self):
        """关闭客户端会话"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class ChatAPI:
    """对话API"""

    def __init__(self, client: AIHubClient):
        self.client = client

    def create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs
    ) -> ChatCompletionResponse:
        """
        创建对话完成

        Args:
            model: 模型名称
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            top_p: 核采样参数
            frequency_penalty: 频率惩罚
            presence_penalty: 存在惩罚
            stop: 停止词
            **kwargs: 其他参数

        Returns:
            对话完成响应
        """
        request = ChatCompletionRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            stream=False,
            **kwargs
        )

        response = self.client._make_request(
            method="POST",
            endpoint="/chat/completions",
            json_data=request.to_dict()
        )

        return self.client._parse_response(response, ChatCompletionResponse)

    def stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs
    ) -> Iterator[ChatCompletionChunk]:
        """
        流式对话完成

        Args:
            model: 模型名称
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            top_p: 核采样参数
            frequency_penalty: 频率惩罚
            presence_penalty: 存在惩罚
            stop: 停止词
            **kwargs: 其他参数

        Yields:
            流式响应块
        """
        request = ChatCompletionRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            stream=True,
            **kwargs
        )

        lines = self.client._make_request(
            method="POST",
            endpoint="/chat/stream",
            json_data=request.to_dict(),
            stream=True
        )

        for line in lines:
            chunk = self.client._parse_stream_chunk(line)
            if chunk:
                yield chunk
            elif line is not None and line.decode('utf-8').strip() == 'data: [DONE]':
                break


class ModelsAPI:
    """模型API"""

    def __init__(self, client: AIHubClient):
        self.client = client

    def list(self) -> List[Model]:
        """
        获取可用模型列表

        Returns:
            模型列表
        """
        response = self.client._make_request("GET", "/models")
        try:
            data = response.json()

            # 处理不同的响应格式
            if 'data' in data:
                models_data = data['data']
            elif 'models' in data:
                models_data = data['models']
            else:
                models_data = data

            return [Model(**model_data) for model_data in models_data]
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            raise APIError(f"Failed to parse models response: {str(e)}")

    def retrieve(self, model_id: str) -> Model:
        """
        获取特定模型信息

        Args:
            model_id: 模型ID

        Returns:
            模型信息
        """
        response = self.client._make_request("GET", f"/models/{model_id}")
        return self.client._parse_response(response, Model)


class UsageAPI:
    """使用统计API"""

    def __init__(self, client: AIHubClient):
        self.client = client

    def quota(self) -> QuotaInfo:
        """
        获取配额信息

        Returns:
            配额信息
        """
        response = self.client._make_request("GET", "/developer/keys/quota")
        return self.client._parse_response(response, QuotaInfo)

    def stats(self, days: int = 30) -> UsageStats:
        """
        获取使用统计

        Args:
            days: 统计天数

        Returns:
            使用统计
        """
        response = self.client._make_request(
            "GET",
            "/developer/usage",
            params={"days": days}
        )
        return self.client._parse_response(response, UsageStats)


class KeysAPI:
    """API密钥管理API"""

    def __init__(self, client: AIHubClient):
        self.client = client

    def list(self, include_inactive: bool = False) -> List[APIKey]:
        """
        获取API密钥列表

        Args:
            include_inactive: 是否包含非活跃密钥

        Returns:
            API密钥列表
        """
        response = self.client._make_request(
            "GET",
            "/developer/keys/keys",
            params={"include_inactive": include_inactive}
        )
        try:
            data = response.json()
            keys_data = data.get('data', {}).get('api_keys', [])
            return [APIKey(**key_data) for key_data in keys_data]
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            raise APIError(f"Failed to parse API keys response: {str(e)}")

    def create(
        self,
        name: str,
        permissions: Optional[List[str]] = None,
        rate_limit: Optional[int] = None,
        allowed_models: Optional[List[str]] = None,
        expires_days: Optional[int] = None
    ) -> APIKey:
        """
        创建API密钥

        Args:
            name: 密钥名称
            permissions: 权限列表
            rate_limit: 速率限制
            allowed_models: 允许的模型
            expires_days: 过期天数

        Returns:
            创建的API密钥
        """
        data = {
            "name": name
        }

        if permissions:
            data["permissions"] = permissions
        if rate_limit:
            data["rate_limit"] = rate_limit
        if allowed_models:
            data["allowed_models"] = allowed_models
        if expires_days:
            data["expires_days"] = expires_days

        response = self.client._make_request(
            "POST",
            "/developer/keys/keys",
            json_data=data
        )
        try:
            response_data = response.json()
            key_data = response_data.get('data', {})
            return APIKey(**key_data)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            raise APIError(f"Failed to parse API key response: {str(e)}")

    def delete(self, key_id: str) -> bool:
        """
        删除API密钥

        Args:
            key_id: 密钥ID

        Returns:
            是否删除成功
        """
        try:
            self.client._make_request("DELETE", f"/developer/keys/keys/{key_id}")
            return True
        except APIError:
            return False