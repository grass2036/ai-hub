"""
插件系统接口规范
Week 7 Day 4: 生态系统建设

定义插件的标准接口、生命周期和通信协议
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PluginType(str, Enum):
    """插件类型"""
    AI_MODEL = "ai_model"          # AI模型插件
    DATA_PROCESSOR = "data_processor"  # 数据处理插件
    AUTHENTICATION = "authentication"  # 认证插件
    NOTIFICATION = "notification"    # 通知插件
    ANALYTICS = "analytics"         # 分析插件
    STORAGE = "storage"            # 存储插件
    WORKFLOW = "workflow"          # 工作流插件
    UI_COMPONENT = "ui_component"   # UI组件插件
    INTEGRATION = "integration"     # 第三方集成插件
    UTILITY = "utility"            # 工具插件


class PluginStatus(str, Enum):
    """插件状态"""
    INACTIVE = "inactive"    # 未激活
    ACTIVE = "active"        # 激活
    ERROR = "error"          # 错误
    LOADING = "loading"      # 加载中
    DISABLED = "disabled"    # 已禁用


class EventType(str, Enum):
    """事件类型"""
    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_UNLOADED = "plugin_unloaded"
    PLUGIN_ERROR = "plugin_error"
    API_REQUEST = "api_request"
    DATA_PROCESSED = "data_processed"
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"


@dataclass
class PluginMetadata:
    """插件元数据"""
    id: str
    name: str
    version: str
    description: str
    author: str
    email: str
    license: str
    homepage: str
    repository: str
    tags: List[str] = field(default_factory=list)
    category: str = ""
    plugin_type: PluginType = PluginType.UTILITY

    # 依赖和兼容性
    dependencies: Dict[str, str] = field(default_factory=dict)
    min_hub_version: str = "1.0.0"
    max_hub_version: Optional[str] = None

    # 权限要求
    permissions: List[str] = field(default_factory=list)
    resources: Dict[str, Any] = field(default_factory=dict)

    # 配置模式
    config_schema: Optional[Dict[str, Any]] = None
    default_config: Dict[str, Any] = field(default_factory=dict)

    # 安装信息
    installed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    install_path: Optional[str] = None


@dataclass
class PluginContext:
    """插件上下文"""
    plugin_id: str
    hub_version: str
    config: Dict[str, Any]
    data_dir: str
    temp_dir: str
    log_dir: str

    # 系统服务接口
    event_bus: 'EventBus'
    storage_manager: 'StorageManager'
    api_client: 'APIClient'
    logger: logging.Logger

    # 运行时信息
    permissions: List[str]
    resources: Dict[str, Any]


@dataclass
class Event:
    """事件对象"""
    type: EventType
    source: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None


class PluginInterface(ABC):
    """插件基础接口"""

    def __init__(self):
        self._context: Optional[PluginContext] = None
        self._metadata: Optional[PluginMetadata] = None
        self._status = PluginStatus.INACTIVE

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """插件元数据"""
        pass

    @property
    def context(self) -> Optional[PluginContext]:
        """插件上下文"""
        return self._context

    @property
    def status(self) -> PluginStatus:
        """插件状态"""
        return self._status

    @abstractmethod
    async def initialize(self, context: PluginContext) -> bool:
        """
        初始化插件

        Args:
            context: 插件上下文

        Returns:
            bool: 初始化是否成功
        """
        pass

    @abstractmethod
    async def activate(self) -> bool:
        """
        激活插件

        Returns:
            bool: 激活是否成功
        """
        pass

    @abstractmethod
    async def deactivate(self) -> bool:
        """
        停用插件

        Returns:
            bool: 停用是否成功
        """
        pass

    @abstractmethod
    async def cleanup(self) -> bool:
        """
        清理插件资源

        Returns:
            bool: 清理是否成功
        """
        pass

    async def handle_event(self, event: Event) -> None:
        """
        处理事件（可选实现）

        Args:
            event: 事件对象
        """
        pass

    async def get_config_schema(self) -> Optional[Dict[str, Any]]:
        """
        获取配置模式（可选实现）

        Returns:
            Dict: 配置模式
        """
        return self.metadata.config_schema

    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        验证配置（可选实现）

        Args:
            config: 配置数据

        Returns:
            bool: 配置是否有效
        """
        return True

    def get_health_check(self) -> Dict[str, Any]:
        """
        健康检查（可选实现）

        Returns:
            Dict: 健康状态信息
        """
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }


class AIModelPlugin(PluginInterface):
    """AI模型插件接口"""

    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        pass

    @abstractmethod
    async def generate_image(self, prompt: str, **kwargs) -> bytes:
        """生成图像"""
        pass

    @abstractmethod
    async def analyze_text(self, text: str, **kwargs) -> Dict[str, Any]:
        """分析文本"""
        pass

    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """获取支持的模型列表"""
        pass


class DataProcessorPlugin(PluginInterface):
    """数据处理插件接口"""

    @abstractmethod
    async def process_data(self, data: Any, format_type: str) -> Any:
        """处理数据"""
        pass

    @abstractmethod
    async def transform_format(self, data: Any, from_format: str, to_format: str) -> Any:
        """转换格式"""
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """获取支持的格式"""
        pass


class AuthenticationPlugin(PluginInterface):
    """认证插件接口"""

    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """认证用户"""
        pass

    @abstractmethod
    async def authorize(self, token: str, permissions: List[str]) -> bool:
        """授权检查"""
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """刷新令牌"""
        pass


class NotificationPlugin(PluginInterface):
    """通知插件接口"""

    @abstractmethod
    async def send_notification(self, message: str, recipients: List[str], **kwargs) -> bool:
        """发送通知"""
        pass

    @abstractmethod
    async def get_notification_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取通知历史"""
        pass


class AnalyticsPlugin(PluginInterface):
    """分析插件接口"""

    @abstractmethod
    async def track_event(self, event_name: str, properties: Dict[str, Any]) -> None:
        """跟踪事件"""
        pass

    @abstractmethod
    async def generate_report(self, report_type: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """生成报告"""
        pass

    @abstractmethod
    async def get_metrics(self, metric_names: List[str], time_range: Dict[str, Any]) -> Dict[str, Any]:
        """获取指标"""
        pass


class StoragePlugin(PluginInterface):
    """存储插件接口"""

    @abstractmethod
    async def store_data(self, key: str, data: Any, **kwargs) -> bool:
        """存储数据"""
        pass

    @abstractmethod
    async def retrieve_data(self, key: str, **kwargs) -> Any:
        """检索数据"""
        pass

    @abstractmethod
    async def delete_data(self, key: str, **kwargs) -> bool:
        """删除数据"""
        pass

    @abstractmethod
    async def list_data(self, prefix: str = "", **kwargs) -> List[str]:
        """列出数据键"""
        pass


class WorkflowPlugin(PluginInterface):
    """工作流插件接口"""

    @abstractmethod
    async def execute_workflow(self, workflow_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行工作流"""
        pass

    @abstractmethod
    async def create_workflow(self, definition: Dict[str, Any]) -> str:
        """创建工作流"""
        pass

    @abstractmethod
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """获取工作流状态"""
        pass


class UIComponentPlugin(PluginInterface):
    """UI组件插件接口"""

    @abstractmethod
    async def render_component(self, component_id: str, props: Dict[str, Any]) -> str:
        """渲染组件"""
        pass

    @abstractmethod
    async def get_component_schema(self, component_id: str) -> Dict[str, Any]:
        """获取组件模式"""
        pass

    @abstractmethod
    def get_component_list(self) -> List[Dict[str, Any]]:
        """获取组件列表"""
        pass


class IntegrationPlugin(PluginInterface):
    """集成插件接口"""

    @abstractmethod
    async def connect_to_service(self, config: Dict[str, Any]) -> bool:
        """连接到外部服务"""
        pass

    @abstractmethod
    async def sync_data(self, sync_type: str, **kwargs) -> Dict[str, Any]:
        """同步数据"""
        pass

    @abstractmethod
    async def test_connection(self, config: Dict[str, Any]) -> bool:
        """测试连接"""
        pass


# 插件工厂函数
def create_plugin(plugin_type: PluginType) -> PluginInterface:
    """创建插件实例"""
    plugin_classes = {
        PluginType.AI_MODEL: AIModelPlugin,
        PluginType.DATA_PROCESSOR: DataProcessorPlugin,
        PluginType.AUTHENTICATION: AuthenticationPlugin,
        PluginType.NOTIFICATION: NotificationPlugin,
        PluginType.ANALYTICS: AnalyticsPlugin,
        PluginType.STORAGE: StoragePlugin,
        PluginType.WORKFLOW: WorkflowPlugin,
        PluginType.UI_COMPONENT: UIComponentPlugin,
        PluginType.INTEGRATION: IntegrationPlugin,
    }

    plugin_class = plugin_classes.get(plugin_type, PluginInterface)
    return plugin_class()


# 插件验证函数
def validate_plugin_metadata(metadata: PluginMetadata) -> List[str]:
    """验证插件元数据"""
    errors = []

    if not metadata.id:
        errors.append("Plugin ID is required")

    if not metadata.name:
        errors.append("Plugin name is required")

    if not metadata.version:
        errors.append("Plugin version is required")

    if not metadata.author:
        errors.append("Plugin author is required")

    # 验证版本格式
    try:
        version_parts = metadata.version.split('.')
        if len(version_parts) != 3:
            errors.append("Version must be in format x.y.z")
    except:
        errors.append("Invalid version format")

    # 验证ID格式
    import re
    if not re.match(r'^[a-z0-9_-]+$', metadata.id):
        errors.append("Plugin ID must contain only lowercase letters, numbers, underscores, and hyphens")

    return errors


def export_plugin_interface():
    """导出插件接口信息"""
    return {
        "plugin_types": [t.value for t in PluginType],
        "plugin_status": [s.value for s in PluginStatus],
        "event_types": [e.value for e in EventType],
        "interfaces": {
            "base": "PluginInterface",
            "ai_model": "AIModelPlugin",
            "data_processor": "DataProcessorPlugin",
            "authentication": "AuthenticationPlugin",
            "notification": "NotificationPlugin",
            "analytics": "AnalyticsPlugin",
            "storage": "StoragePlugin",
            "workflow": "WorkflowPlugin",
            "ui_component": "UIComponentPlugin",
            "integration": "IntegrationPlugin"
        }
    }