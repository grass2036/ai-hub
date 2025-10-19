"""
AI Hub Platform Python SDK
企业级AI应用平台的Python开发工具包
"""

from .client import AIHubClient
from .exceptions import (
    AIHubError,
    APIError,
    AuthenticationError,
    RateLimitError,
    InvalidRequestError,
    InsufficientQuotaError
)
from .models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChunk,
    Model,
    Usage
)
from .version import __version__

__all__ = [
    # Main client
    "AIHubClient",

    # Exceptions
    "AIHubError",
    "APIError",
    "AuthenticationError",
    "RateLimitError",
    "InvalidRequestError",
    "InsufficientQuotaError",

    # Models
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatCompletionChunk",
    "Model",
    "Usage",

    # Version
    "__version__"
]