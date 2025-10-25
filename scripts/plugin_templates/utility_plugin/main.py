"""
Utility Plugin Template
基础工具插件模板
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from backend.core.plugin_system.plugin_interface import (
    PluginInterface,
    PluginMetadata,
    PluginContext,
    PluginStatus,
    Event,
    EventType
)

logger = logging.getLogger(__name__)


class UtilityPlugin(PluginInterface):
    """Utility Plugin Template"""

    def __init__(self):
        super().__init__()
        self._running = False

    @property
    def metadata(self) -> PluginMetadata:
        """插件元数据"""
        from backend.core.plugin_system.plugin_interface import PluginMetadata, PluginType
        return PluginMetadata(
            id="utility_plugin",
            name="Utility Plugin",
            version="1.0.0",
            description="A utility plugin for AI Hub",
            author="AI Hub Developer",
            email="developer@ai-hub.com",
            license="MIT",
            homepage="",
            repository="",
            tags=["utility", "tools"],
            category="utility",
            plugin_type=PluginType.UTILITY,
            dependencies={},
            min_hub_version="1.0.0",
            max_hub_version=None,
            permissions=[],
            resources={},
            config_schema=None,
            default_config={}
        )

    async def initialize(self, context: PluginContext) -> bool:
        """
        初始化插件
        """
        try:
            self._context = context
            self._status = PluginStatus.LOADING

            logger.info("Initializing Utility plugin")

            # 读取配置
            config = context.config
            logger.info(f"Plugin config: {config}")

            # 订阅事件
            context.event_bus.subscribe(EventType.USER_ACTION, self.handle_event)

            self._status = PluginStatus.INACTIVE
            return True

        except Exception as e:
            logger.error(f"Failed to initialize plugin: {e}")
            self._status = PluginStatus.ERROR
            return False

    async def activate(self) -> bool:
        """
        激活插件
        """
        try:
            if self._status != PluginStatus.INACTIVE:
                return False

            logger.info("Activating Utility plugin")

            # 启动后台任务
            self._running = True
            asyncio.create_task(self._background_task())

            self._status = PluginStatus.ACTIVE
            return True

        except Exception as e:
            logger.error(f"Failed to activate plugin: {e}")
            self._status = PluginStatus.ERROR
            return False

    async def deactivate(self) -> bool:
        """
        停用插件
        """
        try:
            if self._status != PluginStatus.ACTIVE:
                return False

            logger.info("Deactivating Utility plugin")

            # 停止后台任务
            self._running = False

            self._status = PluginStatus.INACTIVE
            return True

        except Exception as e:
            logger.error(f"Failed to deactivate plugin: {e}")
            return False

    async def cleanup(self) -> bool:
        """
        清理插件资源
        """
        try:
            logger.info("Cleaning up Utility plugin")
            self._running = False
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup plugin: {e}")
            return False

    async def handle_event(self, event: Event) -> None:
        """
        处理事件
        """
        try:
            logger.debug(f"Handling event: {event.type} from {event.source}")

        except Exception as e:
            logger.error(f"Error handling event: {e}")

    async def _background_task(self):
        """
        后台任务示例
        """
        while self._running:
            try:
                # 实现后台逻辑
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Error in background task: {e}")
                await asyncio.sleep(30)

    def get_health_check(self) -> Dict[str, Any]:
        """
        健康检查
        """
        return {
            "status": "healthy" if self._status == PluginStatus.ACTIVE else "unhealthy",
            "timestamp": asyncio.get_event_loop().time(),
            "running": self._running,
            "checks": {
                "background_task": self._running,
                "configuration": bool(self._context),
                "event_subscription": True
            }
        }


# 插件工厂函数
def create_plugin():
    return UtilityPlugin()


if __name__ == "__main__":
    plugin = create_plugin()
    print(f"Plugin {plugin.metadata.name} created successfully")