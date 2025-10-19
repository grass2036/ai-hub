"""
基础抽象层 - 统一接口和抽象类
Week 6 Day 3: 代码重构和架构优化 - 核心模块重构
定义统一的抽象接口，提高代码的可维护性和扩展性
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Generic, TypeVar
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# 泛型类型变量
T = TypeVar('T')
ID = TypeVar('ID', int, str)

class Status(Enum):
    """通用状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ResponseStatus(Enum):
    """响��状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class BaseResponse(Generic[T]):
    """基础响应类"""
    status: ResponseStatus
    message: str
    data: Optional[T] = None
    code: int = 200
    timestamp: datetime = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class PaginationParams:
    """分页参数"""
    page: int = 1
    limit: int = 20
    sort_by: Optional[str] = None
    sort_order: str = "desc"

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit

    def validate(self):
        """验证分页参数"""
        if self.page < 1:
            raise ValueError("页码必须大于0")
        if self.limit < 1 or self.limit > 100:
            raise ValueError("每页数量必须在1-100之间")
        if self.sort_order not in ["asc", "desc"]:
            raise ValueError("排序方式必须是asc或desc")

@dataclass
class PaginatedResponse(Generic[T]):
    """分页响应"""
    items: List[T]
    total: int
    page: int
    limit: int
    pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(cls, items: List[T], total: int, params: PaginationParams) -> 'PaginatedResponse[T]':
        pages = (total + params.limit - 1) // params.limit
        return cls(
            items=items,
            total=total,
            page=params.page,
            limit=params.limit,
            pages=pages,
            has_next=params.page < pages,
            has_prev=params.page > 1
        )

class BaseRepository(ABC, Generic[T, ID]):
    """基础仓储抽象类"""

    @abstractmethod
    async def get_by_id(self, id: ID) -> Optional[T]:
        """根据ID获取实体"""
        pass

    @abstractmethod
    async def get_all(self, params: PaginationParams) -> PaginatedResponse[T]:
        """获取所有实体（分页）"""
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """创建实体"""
        pass

    @abstractmethod
    async def update(self, id: ID, entity: T) -> Optional[T]:
        """更新实体"""
        pass

    @abstractmethod
    async def delete(self, id: ID) -> bool:
        """删除实体"""
        pass

    @abstractmethod
    async def exists(self, id: ID) -> bool:
        """检查实体是否存在"""
        pass

class BaseService(ABC, Generic[T, ID]):
    """基础服务抽象类"""

    def __init__(self, repository: BaseRepository[T, ID]):
        self.repository = repository

    async def get_by_id(self, id: ID) -> BaseResponse[T]:
        """根据ID获取实体"""
        try:
            entity = await self.repository.get_by_id(id)
            if entity is None:
                return BaseResponse(
                    status=ResponseStatus.ERROR,
                    message="实体不存在",
                    code=404
                )
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                message="获取成功",
                data=entity
            )
        except Exception as e:
            logger.error(f"获取实体失败: {e}")
            return BaseResponse(
                status=ResponseStatus.ERROR,
                message="获取失败",
                code=500
            )

    async def get_all(self, params: PaginationParams) -> BaseResponse[PaginatedResponse[T]]:
        """获取所有实体"""
        try:
            params.validate()
            result = await self.repository.get_all(params)
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                message="获取成功",
                data=result
            )
        except ValueError as e:
            return BaseResponse(
                status=ResponseStatus.ERROR,
                message=f"参数错误: {str(e)}",
                code=400
            )
        except Exception as e:
            logger.error(f"获取实体列表失败: {e}")
            return BaseResponse(
                status=ResponseStatus.ERROR,
                message="获取失败",
                code=500
            )

    async def create(self, entity: T) -> BaseResponse[T]:
        """创建实体"""
        try:
            result = await self.repository.create(entity)
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                message="创建成功",
                data=result,
                code=201
            )
        except Exception as e:
            logger.error(f"创建实体失败: {e}")
            return BaseResponse(
                status=ResponseStatus.ERROR,
                message="创建失败",
                code=500
            )

    async def update(self, id: ID, entity: T) -> BaseResponse[T]:
        """更新实体"""
        try:
            result = await self.repository.update(id, entity)
            if result is None:
                return BaseResponse(
                    status=ResponseStatus.ERROR,
                    message="实体不存在",
                    code=404
                )
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                message="更新成功",
                data=result
            )
        except Exception as e:
            logger.error(f"更新实体失败: {e}")
            return BaseResponse(
                status=ResponseStatus.ERROR,
                message="更新失败",
                code=500
            )

    async def delete(self, id: ID) -> BaseResponse[None]:
        """删除实体"""
        try:
            success = await self.repository.delete(id)
            if not success:
                return BaseResponse(
                    status=ResponseStatus.ERROR,
                    message="实体不存在",
                    code=404
                )
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                message="删除成功"
            )
        except Exception as e:
            logger.error(f"删除实体失败: {e}")
            return BaseResponse(
                status=ResponseStatus.ERROR,
                message="删除失败",
                code=500
            )

class BaseEventHandler(ABC):
    """基础事件处理器抽象类"""

    @abstractmethod
    async def handle(self, event_data: Dict[str, Any]) -> None:
        """处理事件"""
        pass

    @abstractmethod
    def get_event_type(self) -> str:
        """获取事件类型"""
        pass

class EventBus:
    """简单的事件总线实现"""

    def __init__(self):
        self.handlers: Dict[str, List[BaseEventHandler]] = {}

    def subscribe(self, event_type: str, handler: BaseEventHandler):
        """订阅事件"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    async def publish(self, event_type: str, event_data: Dict[str, Any]):
        """发布事件"""
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                try:
                    await handler.handle(event_data)
                except Exception as e:
                    logger.error(f"事件处理失败 {event_type}: {e}")

class BaseValidator(ABC, Generic[T]):
    """基础验证器抽象类"""

    @abstractmethod
    async def validate(self, data: T) -> BaseResponse[None]:
        """验证数据"""
        pass

class BaseFilter(ABC, Generic[T]):
    """基础过滤器抽象类"""

    @abstractmethod
    def apply(self, items: List[T], filter_params: Dict[str, Any]) -> List[T]:
        """应用过滤器"""
        pass

class BaseMapper(ABC, Generic[T, U]):
    """基础映射器抽象类"""

    @abstractmethod
    def to_dto(self, entity: T) -> U:
        """实体转DTO"""
        pass

    @abstractmethod
    def to_entity(self, dto: U) -> T:
        """DTO转实体"""
        pass

class Configuration:
    """配置管理类"""

    def __init__(self, config_data: Dict[str, Any]):
        self._config = config_data

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """设置配置值"""
        self._config[key] = value

    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔值配置"""
        value = self.get(key, default)
        return str(value).lower() in ('true', '1', 'yes', 'on')

    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置"""
        try:
            return int(self.get(key, default))
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数配置"""
        try:
            return float(self.get(key, default))
        except (ValueError, TypeError):
            return default

    def get_list(self, key: str, default: List[Any] = None) -> List[Any]:
        """获取列表配置"""
        if default is None:
            default = []
        value = self.get(key, default)
        if isinstance(value, str):
            return [item.strip() for item in value.split(',') if item.strip()]
        elif isinstance(value, list):
            return value
        return default

class CacheInterface(ABC):
    """缓存接口"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """清空缓存"""
        pass

class LockInterface(ABC):
    """分布式锁接口"""

    @abstractmethod
    async def acquire(self, key: str, ttl: int = 30) -> bool:
        """获取锁"""
        pass

    @abstractmethod
    async def release(self, key: str) -> bool:
        """释放锁"""
        pass

    @abstractmethod
    async def is_locked(self, key: str) -> bool:
        """检查锁状态"""
        pass

# 全局事件总线实例
event_bus = EventBus()

# 装饰器函数
def validate_input(validator: BaseValidator):
    """输入验证装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 假设第一个参数是要验证的数据
            if args:
                validation_result = await validator.validate(args[0])
                if validation_result.status == ResponseStatus.ERROR:
                    return validation_result
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def cache_result(key_template: str, ttl: int = 300):
    """结果缓存装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 这里需要注入缓存实例
            # 简化实现，实际应该依赖注入
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def log_execution(log_level: str = "INFO"):
    """执行日志装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            logger.log(
                getattr(logging, log_level.upper()),
                f"开始执行 {func.__name__}"
            )

            try:
                result = await func(*args, **kwargs)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                logger.log(
                    getattr(logging, log_level.upper()),
                    f"完成执行 {func.__name__}, 耗时: {duration:.3f}秒"
                )
                return result
            except Exception as e:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                logger.error(f"执行失败 {func.__name__}, 耗时: {duration:.3f}秒, 错误: {e}")
                raise
        return wrapper
    return decorator

# 异常类
class BusinessException(Exception):
    """业务异常"""
    def __init__(self, message: str, code: int = 400, data: Any = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data

class ValidationException(BusinessException):
    """验证异常"""
    def __init__(self, message: str, field: str = None):
        super().__init__(message, 400)
        self.field = field

class ResourceNotFoundException(BusinessException):
    """资源不存在异常"""
    def __init__(self, resource: str, id: Any = None):
        message = f"{resource}不存在"
        if id is not None:
            message += f": {id}"
        super().__init__(message, 404)

class PermissionDeniedException(BusinessException):
    """权限拒绝异常"""
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, 403)

# 工具函数
def create_response(status: ResponseStatus, message: str, data: Any = None, code: int = 200) -> BaseResponse:
    """创建标准响应"""
    return BaseResponse(status=status, message=message, data=data, code=code)

def success_response(message: str = "操作成功", data: Any = None) -> BaseResponse:
    """创建成功响应"""
    return create_response(ResponseStatus.SUCCESS, message, data, 200)

def error_response(message: str, code: int = 400, data: Any = None) -> BaseResponse:
    """创建错误响应"""
    return create_response(ResponseStatus.ERROR, message, data, code)

def warning_response(message: str, data: Any = None) -> BaseResponse:
    """创建警告响应"""
    return create_response(ResponseStatus.WARNING, message, data, 200)

def info_response(message: str, data: Any = None) -> BaseResponse:
    """创建信息响应"""
    return create_response(ResponseStatus.INFO, message, data, 200)