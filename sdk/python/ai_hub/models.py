"""AI Hub SDK 数据模型定义"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Usage:
    """Token使用统计"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    @property
    def cost(self) -> float:
        """计算使用成本（简化版本）"""
        # 这里可以根据模型定价计算实际成本
        return self.total_tokens * 0.00001  # 示例价格


@dataclass
class Choice:
    """对话选择"""
    index: int
    message: Optional[Dict[str, str]] = None
    delta: Optional[Dict[str, str]] = None
    finish_reason: Optional[str] = None

    def get_content(self) -> Optional[str]:
        """获取回复内容"""
        if self.message:
            return self.message.get("content")
        elif self.delta:
            return self.delta.get("content")
        return None


@dataclass
class ChatCompletionResponse:
    """对话完成响应"""
    id: str
    object: str = "chat.completion"
    created: Optional[int] = None
    model: Optional[str] = None
    choices: List[Choice] = None
    usage: Optional[Usage] = None
    cost: Optional[float] = None

    def __post_init__(self):
        if self.choices is None:
            self.choices = []

    @property
    def first_choice(self) -> Optional[Choice]:
        """获取第一个选择"""
        return self.choices[0] if self.choices else None

    @property
    def content(self) -> Optional[str]:
        """获取回复内容"""
        return self.first_choice.get_content() if self.first_choice else None


@dataclass
class ChatCompletionChunk:
    """流式对话响应块"""
    id: str
    object: str = "chat.completion.chunk"
    created: Optional[int] = None
    model: Optional[str] = None
    choices: List[Choice] = None

    def __post_init__(self):
        if self.choices is None:
            self.choices = []

    @property
    def first_choice(self) -> Optional[Choice]:
        """获取第一个选择"""
        return self.choices[0] if self.choices else None

    @property
    def content(self) -> Optional[str]:
        """获取当前内容块"""
        return self.first_choice.get_content() if self.first_choice else None


@dataclass
class Model:
    """模型信息"""
    id: str
    object: str = "model"
    created: Optional[int] = None
    owned_by: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    pricing: Optional[str] = None
    category: Optional[str] = None


@dataclass
class ChatCompletionRequest:
    """对话完成请求"""
    model: str
    messages: List[Dict[str, str]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    stop: Optional[Union[str, List[str]]] = None
    stream: Optional[bool] = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "model": self.model,
            "messages": self.messages
        }

        # 只添加非None的参数
        optional_params = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "stop": self.stop,
            "stream": self.stream
        }

        for key, value in optional_params.items():
            if value is not None:
                result[key] = value

        return result


@dataclass
class APIKey:
    """API密钥信息"""
    id: str
    name: str
    key_prefix: str
    permissions: List[str]
    rate_limit: int
    allowed_models: List[str]
    is_active: bool
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    total_tokens_used: int = 0
    created_at: Optional[datetime] = None


@dataclass
class QuotaInfo:
    """配额信息"""
    monthly_quota: int
    monthly_used: int
    monthly_remaining: int
    monthly_usage_percent: float
    monthly_cost: float
    active_api_keys: int
    max_api_keys: int
    reset_date: str


@dataclass
class UsageStats:
    """使用统计"""
    period_days: int
    total_requests: int
    total_tokens: int
    total_cost: float
    avg_response_time: float
    success_rate: float
    model_usage: Dict[str, Dict[str, Any]]
    daily_usage: Dict[str, Dict[str, Any]]


@dataclass
class Plan:
    """订阅计划"""
    id: str
    name: str
    slug: str
    description: str
    price: float
    currency: str
    billing_cycle: str
    features: Dict[str, Any]
    api_quota: int
    rate_limit: int
    max_teams: int
    max_users: int
    is_active: bool
    is_popular: bool
    sort_order: int


@dataclass
class Subscription:
    """订阅信息"""
    id: str
    organization_id: str
    plan_id: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    cancel_at_period_end: bool = False