"""
插件管理器
Week 7 Day 4: 生态系统建设

实现插件的生命周期管理、加载、卸载和错误处理
"""

import asyncio
import importlib
import inspect
import json
import logging
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Type, Set
from datetime import datetime
import tempfile
import shutil
import hashlib

from .plugin_interface import (
    PluginInterface,
    PluginMetadata,
    PluginContext,
    PluginStatus,
    EventType,
    Event,
    validate_plugin_metadata
)

logger = logging.getLogger(__name__)


class PluginLoadError(Exception):
    """插件加载错误"""
    pass


class PluginValidationError(Exception):
    """插件验证错误"""
    pass


class EventBus:
    """事件总线"""

    def __init__(self):
        self._listeners: Dict[EventType, List[callable]] = {}

    def subscribe(self, event_type: EventType, listener: callable):
        """订阅事件"""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)

    def unsubscribe(self, event_type: EventType, listener: callable):
        """取消订阅"""
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(listener)
            except ValueError:
                pass

    async def publish(self, event: Event):
        """发布事件"""
        listeners = self._listeners.get(event.type, [])
        tasks = []
        for listener in listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    tasks.append(listener(event))
                else:
                    listener(event)
            except Exception as e:
                logger.error(f"Error in event listener: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


class StorageManager:
    """存储管理器"""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_plugin_dir(self, plugin_id: str) -> Path:
        """获取插件目录"""
        return self.base_dir / plugin_id

    def get_plugin_data_dir(self, plugin_id: str) -> Path:
        """获取插件数据目录"""
        data_dir = self.get_plugin_dir(plugin_id) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def get_plugin_temp_dir(self, plugin_id: str) -> Path:
        """获取插件临时目录"""
        temp_dir = self.get_plugin_dir(plugin_id) / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    def get_plugin_log_dir(self, plugin_id: str) -> Path:
        """获取插件日志目录"""
        log_dir = self.get_plugin_dir(plugin_id) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    def cleanup_plugin_data(self, plugin_id: str):
        """清理插件数据"""
        plugin_dir = self.get_plugin_dir(plugin_id)
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir, ignore_errors=True)


class SandboxManager:
    """沙箱管理器"""

    def __init__(self):
        self._restricted_modules = {
            'os', 'sys', 'subprocess', 'socket', 'threading',
            'multiprocessing', 'ctypes', 'importlib'
        }
        self._restricted_functions = {
            'open', 'exec', 'eval', 'compile', '__import__'
        }

    def create_plugin_globals(self, plugin_id: str) -> Dict[str, Any]:
        """创建插件全局命名空间"""
        # 创建安全的模块字典
        safe_modules = {
            'json', 'datetime', 'uuid', 'base64', 'hashlib',
            'math', 'random', 'itertools', 'functools',
            'collections', 'typing', 'dataclasses', 'enum'
        }

        globals_dict = {}
        for module_name in safe_modules:
            try:
                globals_dict[module_name] = __import__(module_name)
            except ImportError:
                pass

        # 添加受限的内置函数
        allowed_builtins = {
            'len', 'str', 'int', 'float', 'bool', 'list', 'dict',
            'set', 'tuple', 'range', 'enumerate', 'zip', 'map',
            'filter', 'isinstance', 'issubclass', 'type', 'hasattr',
            'getattr', 'setattr', 'delattr', 'callable', 'iter',
            'next', 'repr', 'format', 'sorted', 'reversed', 'slice',
            'min', 'max', 'sum', 'any', 'all', 'abs', 'round',
            'divmod', 'pow', 'ord', 'chr', 'bin', 'oct', 'hex'
        }

        for name in allowed_builtins:
            if hasattr(__builtins__, name):
                globals_dict[name] = getattr(__builtins__, name)

        # 添加特殊的函数和类
        globals_dict.update({
            '__plugin_id__': plugin_id,
            '__name__': f'plugin_{plugin_id}',
            '__file__': None,
        })

        return globals_dict

    def validate_plugin_code(self, code: str, plugin_id: str) -> bool:
        """验证插件代码安全性"""
        try:
            compile(code, f'<plugin_{plugin_id}>', 'exec')
            return True
        except SyntaxError as e:
            logger.error(f"Plugin {plugin_id} syntax error: {e}")
            return False
        except Exception as e:
            logger.error(f"Plugin {plugin_id} validation error: {e}")
            return False


class PluginManager:
    """插件管理器"""

    def __init__(self, hub_dir: str):
        self.hub_dir = Path(hub_dir)
        self.plugins_dir = self.hub_dir / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

        self.event_bus = EventBus()
        self.storage_manager = StorageManager(str(self.hub_dir / "plugin_data"))
        self.sandbox = SandboxManager()

        # 插件注册表
        self._plugins: Dict[str, PluginInterface] = {}
        self._metadata: Dict[str, PluginMetadata] = {}
        self._contexts: Dict[str, PluginContext] = {}
        self._configs: Dict[str, Dict[str, Any]] = {}

        # 依赖解析
        self._dependency_graph: Dict[str, Set[str]] = {}
        self._load_order: List[str] = []

        # 插件状态跟踪
        self._load_times: Dict[str, datetime] = {}
        self._error_counts: Dict[str, int] = {}
        self._last_errors: Dict[str, str] = {}

        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """设置事件处理器"""
        async def on_plugin_error(event: Event):
            plugin_id = event.source
            self._error_counts[plugin_id] = self._error_counts.get(plugin_id, 0) + 1
            self._last_errors[plugin_id] = str(event.data.get('error', 'Unknown error'))

            # 如果错误次数过多，自动停用插件
            if self._error_counts[plugin_id] >= 3:
                logger.warning(f"Plugin {plugin_id} has too many errors, deactivating")
                await self.deactivate_plugin(plugin_id)

        self.event_bus.subscribe(EventType.PLUGIN_ERROR, on_plugin_error)

    async def discover_plugins(self) -> List[str]:
        """发现可用插件"""
        discovered = []

        for plugin_dir in self.plugins_dir.iterdir():
            if plugin_dir.is_dir():
                metadata_file = plugin_dir / "plugin.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata_data = json.load(f)

                        metadata = PluginMetadata(**metadata_data)
                        errors = validate_plugin_metadata(metadata)

                        if not errors:
                            self._metadata[metadata.id] = metadata
                            discovered.append(metadata.id)
                        else:
                            logger.error(f"Plugin {metadata.id} has validation errors: {errors}")

                    except Exception as e:
                        logger.error(f"Error loading plugin metadata from {plugin_dir}: {e}")

        return discovered

    async def install_plugin(self, plugin_package: str) -> str:
        """
        安装插件包

        Args:
            plugin_package: 插件包路径或URL

        Returns:
            str: 插件ID
        """
        try:
            # 临时解压目录
            with tempfile.TemporaryDirectory() as temp_dir:
                # 解压插件包
                await self._extract_plugin_package(plugin_package, temp_dir)

                # 验证插件
                plugin_id = await self._validate_plugin_package(temp_dir)
                if not plugin_id:
                    raise PluginValidationError("Plugin validation failed")

                # 安装插件
                plugin_dir = self.plugins_dir / plugin_id
                if plugin_dir.exists():
                    await self.uninstall_plugin(plugin_id)

                shutil.copytree(temp_dir, plugin_dir)

                # 读取元数据
                metadata_file = plugin_dir / "plugin.json"
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_data = json.load(f)
                metadata = PluginMetadata(**metadata_data)

                self._metadata[plugin_id] = metadata
                metadata.installed_at = datetime.now()
                metadata.install_path = str(plugin_dir)

                # 发布事件
                await self.event_bus.publish(Event(
                    type=EventType.PLUGIN_LOADED,
                    source="plugin_manager",
                    data={"plugin_id": plugin_id, "metadata": metadata.__dict__}
                ))

                logger.info(f"Plugin {plugin_id} installed successfully")
                return plugin_id

        except Exception as e:
            logger.error(f"Failed to install plugin: {e}")
            raise PluginLoadError(f"Plugin installation failed: {e}")

    async def load_plugin(self, plugin_id: str) -> bool:
        """
        加载插件

        Args:
            plugin_id: 插件ID

        Returns:
            bool: 加载是否成功
        """
        if plugin_id in self._plugins:
            logger.warning(f"Plugin {plugin_id} is already loaded")
            return True

        if plugin_id not in self._metadata:
            logger.error(f"Plugin {plugin_id} metadata not found")
            return False

        try:
            metadata = self._metadata[plugin_id]

            # 检查依赖
            if not await self._check_dependencies(plugin_id):
                return False

            # 加载插件模块
            plugin_module = await self._load_plugin_module(plugin_id)
            if not plugin_module:
                return False

            # 创建插件实例
            plugin_class = self._find_plugin_class(plugin_module)
            if not plugin_class:
                raise PluginLoadError(f"No plugin class found in {plugin_id}")

            plugin = plugin_class()
            plugin._metadata = metadata

            # 创建插件上下文
            context = self._create_plugin_context(plugin_id)
            plugin._context = context

            # 初始化插件
            if await plugin.initialize(context):
                self._plugins[plugin_id] = plugin
                self._contexts[plugin_id] = context
                self._load_times[plugin_id] = datetime.now()

                # 发布事件
                await self.event_bus.publish(Event(
                    type=EventType.PLUGIN_LOADED,
                    source=plugin_id,
                    data={"plugin_id": plugin_id}
                ))

                logger.info(f"Plugin {plugin_id} loaded successfully")
                return True
            else:
                raise PluginLoadError(f"Plugin {plugin_id} initialization failed")

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_id}: {e}")
            await self.event_bus.publish(Event(
                type=EventType.PLUGIN_ERROR,
                source=plugin_id,
                data={"error": str(e), "traceback": traceback.format_exc()}
            ))
            return False

    async def activate_plugin(self, plugin_id: str) -> bool:
        """
        激活插件

        Args:
            plugin_id: 插件ID

        Returns:
            bool: 激活是否成功
        """
        if plugin_id not in self._plugins:
            if not await self.load_plugin(plugin_id):
                return False

        plugin = self._plugins[plugin_id]

        try:
            if plugin._status == PluginStatus.ACTIVE:
                return True

            # 按依赖顺序激活
            dependencies = self._dependency_graph.get(plugin_id, set())
            for dep_id in dependencies:
                if dep_id in self._plugins:
                    await self.activate_plugin(dep_id)

            if await plugin.activate():
                plugin._status = PluginStatus.ACTIVE

                # 发布事件
                await self.event_bus.publish(Event(
                    type=EventType.PLUGIN_LOADED,
                    source=plugin_id,
                    data={"action": "activated", "plugin_id": plugin_id}
                ))

                logger.info(f"Plugin {plugin_id} activated successfully")
                return True
            else:
                raise PluginLoadError(f"Plugin {plugin_id} activation failed")

        except Exception as e:
            logger.error(f"Failed to activate plugin {plugin_id}: {e}")
            plugin._status = PluginStatus.ERROR
            await self.event_bus.publish(Event(
                type=EventType.PLUGIN_ERROR,
                source=plugin_id,
                data={"error": str(e)}
            ))
            return False

    async def deactivate_plugin(self, plugin_id: str) -> bool:
        """
        停用插件

        Args:
            plugin_id: 插件ID

        Returns:
            bool: 停用是否成功
        """
        if plugin_id not in self._plugins:
            return True

        plugin = self._plugins[plugin_id]

        try:
            if plugin._status == PluginStatus.ACTIVE:
                # 先停用依赖此插件的其他插件
                dependents = self._get_dependent_plugins(plugin_id)
                for dep_id in dependents:
                    await self.deactivate_plugin(dep_id)

                if await plugin.deactivate():
                    plugin._status = PluginStatus.INACTIVE
                    logger.info(f"Plugin {plugin_id} deactivated successfully")
                    return True
                else:
                    raise PluginLoadError(f"Plugin {plugin_id} deactivation failed")

            return True

        except Exception as e:
            logger.error(f"Failed to deactivate plugin {plugin_id}: {e}")
            await self.event_bus.publish(Event(
                type=EventType.PLUGIN_ERROR,
                source=plugin_id,
                data={"error": str(e)}
            ))
            return False

    async def unload_plugin(self, plugin_id: str) -> bool:
        """
        卸载插件

        Args:
            plugin_id: 插件ID

        Returns:
            bool: 卸载是否成功
        """
        if plugin_id not in self._plugins:
            return True

        try:
            # 先停用插件
            await self.deactivate_plugin(plugin_id)

            plugin = self._plugins[plugin_id]
            await plugin.cleanup()

            # 清理资源
            del self._plugins[plugin_id]
            if plugin_id in self._contexts:
                del self._contexts[plugin_id]
            if plugin_id in self._load_times:
                del self._load_times[plugin_id]

            # 发布事件
            await self.event_bus.publish(Event(
                type=EventType.PLUGIN_UNLOADED,
                source=plugin_id,
                data={"plugin_id": plugin_id}
            ))

            logger.info(f"Plugin {plugin_id} unloaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_id}: {e}")
            return False

    async def uninstall_plugin(self, plugin_id: str) -> bool:
        """
        卸载插件

        Args:
            plugin_id: 插件ID

        Returns:
            bool: 卸载是否成功
        """
        try:
            # 先卸载插件
            await self.unload_plugin(plugin_id)

            # 删除插件文件
            if plugin_id in self._metadata:
                metadata = self._metadata[plugin_id]
                if metadata.install_path:
                    plugin_path = Path(metadata.install_path)
                    if plugin_path.exists():
                        shutil.rmtree(plugin_path, ignore_errors=True)

            # 清理数据
            self.storage_manager.cleanup_plugin_data(plugin_id)

            # 清理元数据
            if plugin_id in self._metadata:
                del self._metadata[plugin_id]

            logger.info(f"Plugin {plugin_id} uninstalled successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to uninstall plugin {plugin_id}: {e}")
            return False

    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """获取插件实例"""
        return self._plugins.get(plugin_id)

    def get_plugins_by_type(self, plugin_type: str) -> List[PluginInterface]:
        """根据类型获取插件"""
        return [
            plugin for plugin in self._plugins.values()
            if plugin.metadata.plugin_type.value == plugin_type
        ]

    def get_plugin_status(self, plugin_id: str) -> Optional[PluginStatus]:
        """获取插件状态"""
        plugin = self._plugins.get(plugin_id)
        return plugin._status if plugin else None

    def get_plugin_list(self) -> Dict[str, Dict[str, Any]]:
        """获取插件列表"""
        result = {}
        for plugin_id, metadata in self._metadata.items():
            plugin = self._plugins.get(plugin_id)
            status = plugin._status if plugin else PluginStatus.INACTIVE

            result[plugin_id] = {
                "metadata": metadata.__dict__,
                "status": status.value,
                "loaded": plugin_id in self._plugins,
                "active": status == PluginStatus.ACTIVE,
                "load_time": self._load_times.get(plugin_id),
                "error_count": self._error_counts.get(plugin_id, 0),
                "last_error": self._last_errors.get(plugin_id)
            }

        return result

    async def reload_plugin(self, plugin_id: str) -> bool:
        """重新加载插件"""
        if plugin_id in self._plugins:
            await self.unload_plugin(plugin_id)
        return await self.load_plugin(plugin_id)

    async def _extract_plugin_package(self, plugin_package: str, extract_dir: str):
        """解压插件包"""
        import zipfile
        import tarfile

        plugin_path = Path(plugin_package)

        if plugin_path.suffix == '.zip':
            with zipfile.ZipFile(plugin_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
        elif plugin_path.suffix in ['.tar', '.gz', '.bz2']:
            with tarfile.open(plugin_path, 'r:*') as tar_ref:
                tar_ref.extractall(extract_dir)
        else:
            raise PluginLoadError("Unsupported plugin package format")

    async def _validate_plugin_package(self, package_dir: str) -> Optional[str]:
        """验证插件包"""
        package_path = Path(package_dir)
        metadata_file = package_path / "plugin.json"
        main_file = package_path / "main.py"

        if not metadata_file.exists():
            raise PluginValidationError("plugin.json not found")

        if not main_file.exists():
            raise PluginValidationError("main.py not found")

        # 验证元数据
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata_data = json.load(f)

        metadata = PluginMetadata(**metadata_data)
        errors = validate_plugin_metadata(metadata)
        if errors:
            raise PluginValidationError(f"Metadata validation failed: {errors}")

        # 验证主文件
        with open(main_file, 'r', encoding='utf-8') as f:
            main_code = f.read()

        if not self.sandbox.validate_plugin_code(main_code, metadata.id):
            raise PluginValidationError("Main file validation failed")

        return metadata.id

    async def _check_dependencies(self, plugin_id: str) -> bool:
        """检查插件依赖"""
        metadata = self._metadata[plugin_id]

        for dep_name, dep_version in metadata.dependencies.items():
            if dep_name not in self._metadata:
                logger.error(f"Plugin {plugin_id} requires {dep_name} but it's not installed")
                return False

            # 简单版本检查（实际应该使用更复杂的版本比较）
            dep_metadata = self._metadata[dep_name]
            # TODO: 实现语义化版本比较

        # 构建依赖图
        self._dependency_graph[plugin_id] = set(metadata.dependencies.keys())

        return True

    async def _load_plugin_module(self, plugin_id: str):
        """加载插件模块"""
        metadata = self._metadata[plugin_id]
        plugin_dir = Path(metadata.install_path)

        # 添加插件目录到Python路径
        if str(plugin_dir) not in sys.path:
            sys.path.insert(0, str(plugin_dir))

        try:
            # 在沙箱中加载模块
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_id}",
                plugin_dir / "main.py"
            )

            if spec is None or spec.loader is None:
                raise PluginLoadError(f"Cannot load plugin module for {plugin_id}")

            module = importlib.util.module_from_spec(spec)

            # 设置安全的模块全局变量
            safe_globals = self.sandbox.create_plugin_globals(plugin_id)
            module.__dict__.update(safe_globals)

            spec.loader.exec_module(module)
            return module

        except Exception as e:
            logger.error(f"Failed to load plugin module {plugin_id}: {e}")
            return None

    def _find_plugin_class(self, module) -> Optional[Type[PluginInterface]]:
        """查找插件类"""
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and
                issubclass(obj, PluginInterface) and
                obj != PluginInterface):
                return obj
        return None

    def _create_plugin_context(self, plugin_id: str) -> PluginContext:
        """创建插件上下文"""
        metadata = self._metadata[plugin_id]
        config = self._configs.get(plugin_id, metadata.default_config.copy())

        # 创建插件专用日志器
        plugin_logger = logging.getLogger(f"plugin.{plugin_id}")

        return PluginContext(
            plugin_id=plugin_id,
            hub_version="1.0.0",  # 应该从配置中获取
            config=config,
            data_dir=str(self.storage_manager.get_plugin_data_dir(plugin_id)),
            temp_dir=str(self.storage_manager.get_plugin_temp_dir(plugin_id)),
            log_dir=str(self.storage_manager.get_plugin_log_dir(plugin_id)),
            event_bus=self.event_bus,
            storage_manager=self.storage_manager,
            api_client=None,  # TODO: 实现API客户端
            logger=plugin_logger,
            permissions=metadata.permissions,
            resources=metadata.resources
        )

    def _get_dependent_plugins(self, plugin_id: str) -> List[str]:
        """获取依赖此插件的其他插件"""
        dependents = []
        for other_id, deps in self._dependency_graph.items():
            if plugin_id in deps:
                dependents.append(other_id)
        return dependents

    async def shutdown(self):
        """关闭插件管理器"""
        for plugin_id in list(self._plugins.keys()):
            await self.unload_plugin(plugin_id)