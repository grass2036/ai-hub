"""AI Hub SDK 异常类定���"""


class AIHubError(Exception):
    """AI Hub SDK 基础异常类"""

    def __init__(self, message: str, error_code: str = None, status_code: int = None):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)


class APIError(AIHubError):
    """API请求错误"""

    def __init__(self, message: str, error_code: str = None, status_code: int = None, response=None):
        self.response = response
        super().__init__(message, error_code, status_code)


class AuthenticationError(AIHubError):
    """认证错误"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "authentication_error", 401)


class RateLimitError(AIHubError):
    """速率限制错误"""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(message, "rate_limit_exceeded", 429)


class InvalidRequestError(AIHubError):
    """无效请求错误"""

    def __init__(self, message: str, param: str = None):
        self.param = param
        super().__init__(message, "invalid_request_error", 400)


class InsufficientQuotaError(AIHubError):
    """配额不足错误"""

    def __init__(self, message: str = "Insufficient quota"):
        super().__init__(message, "insufficient_quota", 403)


class ModelNotFoundError(AIHubError):
    """模型未找到错误"""

    def __init__(self, model: str):
        message = f"Model '{model}' not found"
        super().__init__(message, "model_not_found", 404)


class ConnectionError(AIHubError):
    """连接错误"""

    def __init__(self, message: str = "Failed to connect to AI Hub API"):
        super().__init__(message, "connection_error")


class TimeoutError(AIHubError):
    """超时错误"""

    def __init__(self, message: str = "Request timed out"):
        super().__init__(message, "timeout_error")