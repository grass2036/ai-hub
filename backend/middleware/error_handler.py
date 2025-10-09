"""
统一错误处理中间件
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.base import BaseHTTPMiddleware
from typing import Union
import logging
import time
import traceback

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """统一错误处理中间件"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        try:
            response = await call_next(request)

            # 记录请求处理时间
            process_time = time.time() - start_time
            if process_time > 1.0:  # 超过1秒的请求记录警告
                logger.warning(
                    f"Slow request: {request.method} {request.url.path} "
                    f"took {process_time:.2f}s"
                )

            # 添加响应头
            response.headers["X-Process-Time"] = str(process_time)
            return response

        except HTTPException as e:
            # HTTP异常直接返回
            logger.warning(f"HTTP Exception: {e.status_code} - {e.detail}")
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": True,
                    "message": e.detail,
                    "type": "http_error",
                    "status_code": e.status_code
                }
            )

        except ValueError as e:
            # 参数验证错误
            logger.error(f"Validation Error: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": True,
                    "message": f"参数错误: {str(e)}",
                    "type": "validation_error"
                }
            )

        except PermissionError as e:
            # 权限错误
            logger.error(f"Permission Error: {str(e)}")
            return JSONResponse(
                status_code=403,
                content={
                    "error": True,
                    "message": "权限不足",
                    "type": "permission_error"
                }
            )

        except FileNotFoundError as e:
            # 文件未找到
            logger.error(f"File Not Found: {str(e)}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": True,
                    "message": "资源未找到",
                    "type": "not_found_error"
                }
            )

        except Exception as e:
            # 其他未捕获的异常
            logger.error(f"Unhandled Exception: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")

            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "message": "服务器内部错误",
                    "type": "internal_error",
                    "detail": str(e) if logger.isEnabledFor(logging.DEBUG) else None
                }
            )


class PerformanceMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # 记录请求开始
        logger.info(f"Request started: {request.method} {request.url.path}")

        try:
            response = await call_next(request)

            # 计算处理时间
            process_time = time.time() - start_time

            # 记录性能数据
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"- Status: {response.status_code} - Time: {process_time:.3f}s"
            )

            # 添加性能头
            response.headers["X-Process-Time"] = f"{process_time:.3f}s"
            response.headers["X-Request-ID"] = str(id(request))

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"- Time: {process_time:.3f}s - Error: {str(e)}"
            )
            raise


def setup_error_handlers(app):
    """设置错误处理器"""

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """全局异常处理器"""
        logger.error(f"Global exception: {type(exc).__name__}: {str(exc)}")
        logger.error(f"Request URL: {request.url}")

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "服务器内部错误",
                "type": type(exc).__name__,
                "path": str(request.url.path)
            }
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """HTTP异常处理器"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail,
                "type": "http_error",
                "status_code": exc.status_code,
                "path": str(request.url.path)
            }
        )