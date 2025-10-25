#!/usr/bin/env python3
"""
AI Hub 插件CLI工具
Week 7 Day 4: 生态系统建设

提供插件的创建、构建、测试、打包和发布功能
"""

import os
import sys
import json
import argparse
import subprocess
import shutil
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PluginCLI:
    """插件CLI工具"""

    def __init__(self):
        self.templates_dir = project_root / "scripts" / "plugin_templates"
        self.plugins_dir = project_root / "plugins"

    def create_plugin(self, plugin_name: str, plugin_type: str = "utility", author: str = "", email: str = ""):
        """
        创建新插件项目

        Args:
            plugin_name: 插件名称
            plugin_type: 插件类型
            author: 作者
            email: 邮箱
        """
        plugin_id = self._generate_plugin_id(plugin_name)
        plugin_dir = self.plugins_dir / plugin_id

        if plugin_dir.exists():
            logger.error(f"Plugin directory {plugin_dir} already exists")
            return False

        try:
            # 创建插件目录
            plugin_dir.mkdir(parents=True, exist_ok=True)

            # 生成插件元数据
            metadata = self._generate_metadata(plugin_id, plugin_name, plugin_type, author, email)

            # 创建插件文件结构
            self._create_plugin_structure(plugin_dir, metadata, plugin_type)

            # 生成插件代码
            self._generate_plugin_code(plugin_dir, metadata, plugin_type)

            # 生成配置文件
            self._generate_config_files(plugin_dir, metadata)

            logger.info(f"Plugin {plugin_id} created successfully at {plugin_dir}")
            logger.info(f"Next steps:")
            logger.info(f"  1. cd {plugin_dir}")
            logger.info(f"  2. Edit main.py to implement your plugin logic")
            logger.info(f"  3. Run: python scripts/plugin_cli.py build {plugin_id}")
            logger.info(f"  4. Run: python scripts/plugin_cli.py test {plugin_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to create plugin: {e}")
            # 清理失败的创建
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
            return False

    def build_plugin(self, plugin_id: str):
        """构建插件"""
        plugin_dir = self.plugins_dir / plugin_id

        if not plugin_dir.exists():
            logger.error(f"Plugin {plugin_id} not found")
            return False

        try:
            # 验证插件
            if not self._validate_plugin(plugin_dir):
                return False

            # 运行测试
            if not self._run_tests(plugin_dir):
                logger.warning("Tests failed, but continuing build")

            # 生成构建文件
            build_dir = plugin_dir / "build"
            if build_dir.exists():
                shutil.rmtree(build_dir)
            build_dir.mkdir()

            # 复制必要文件
            self._copy_build_files(plugin_dir, build_dir)

            # 生成文档
            self._generate_documentation(plugin_dir, build_dir)

            logger.info(f"Plugin {plugin_id} built successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to build plugin: {e}")
            return False

    def test_plugin(self, plugin_id: str, verbose: bool = False):
        """测试插件"""
        plugin_dir = self.plugins_dir / plugin_id

        if not plugin_dir.exists():
            logger.error(f"Plugin {plugin_id} not found")
            return False

        try:
            return self._run_tests(plugin_dir, verbose)
        except Exception as e:
            logger.error(f"Failed to test plugin: {e}")
            return False

    def package_plugin(self, plugin_id: str, format_type: str = "zip"):
        """打包插件"""
        plugin_dir = self.plugins_dir / plugin_id
        build_dir = plugin_dir / "build"

        if not build_dir.exists():
            logger.error(f"Plugin {plugin_id} not built. Run 'build' command first")
            return False

        try:
            # 读取版本信息
            metadata_file = build_dir / "plugin.json"
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            version = metadata.get("version", "1.0.0")
            package_name = f"{plugin_id}-v{version}.{format_type}"
            package_path = project_root / "dist" / package_name

            # 创建dist目录
            (project_root / "dist").mkdir(exist_ok=True)

            # 打包
            if format_type == "zip":
                with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in build_dir.rglob('*'):
                        if file_path.is_file():
                            arcname = file_path.relative_to(build_dir)
                            zipf.write(file_path, arcname)

            elif format_type in ["tar.gz", "tgz"]:
                with tarfile.open(package_path, 'w:gz') as tarf:
                    tarf.add(build_dir, arcname=plugin_id)

            logger.info(f"Plugin packaged as {package_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to package plugin: {e}")
            return False

    def install_plugin(self, package_path: str):
        """安装插件"""
        package_file = Path(package_path)

        if not package_file.exists():
            logger.error(f"Package file {package_path} not found")
            return False

        try:
            # 创建临时解压目录
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                # 解压包
                if package_file.suffix == '.zip':
                    with zipfile.ZipFile(package_file, 'r') as zipf:
                        zipf.extractall(temp_dir)
                elif package_file.suffix in ['.gz', '.bz2'] or package_file.name.endswith('.tar.gz'):
                    with tarfile.open(package_file, 'r:*') as tarf:
                        tarf.extractall(temp_dir)
                else:
                    logger.error("Unsupported package format")
                    return False

                # 验证插件
                plugin_id = self._validate_package(temp_dir)
                if not plugin_id:
                    logger.error("Package validation failed")
                    return False

                # 安装到系统插件目录
                system_plugins_dir = project_root / "data" / "plugins"
                system_plugins_dir.mkdir(parents=True, exist_ok=True)

                target_dir = system_plugins_dir / plugin_id
                if target_dir.exists():
                    logger.warning(f"Plugin {plugin_id} already exists, updating...")

                # 复制文件
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                shutil.copytree(temp_dir, target_dir)

            logger.info(f"Plugin {plugin_id} installed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to install plugin: {e}")
            return False

    def list_plugins(self):
        """列出所有插件"""
        plugins_dir = self.plugins_dir
        if not plugins_dir.exists():
            logger.info("No plugins found")
            return

        plugins = []
        for plugin_dir in plugins_dir.iterdir():
            if plugin_dir.is_dir():
                metadata_file = plugin_dir / "plugin.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        plugins.append({
                            'id': metadata.get('id', plugin_dir.name),
                            'name': metadata.get('name', 'Unknown'),
                            'version': metadata.get('version', '0.0.0'),
                            'type': metadata.get('plugin_type', 'utility'),
                            'author': metadata.get('author', 'Unknown'),
                            'description': metadata.get('description', 'No description')
                        })
                    except Exception as e:
                        logger.warning(f"Failed to read metadata for {plugin_dir.name}: {e}")

        if plugins:
            print(f"{'ID':<20} {'Name':<20} {'Version':<10} {'Type':<12} {'Author':<20}")
            print("-" * 100)
            for plugin in plugins:
                print(f"{plugin['id']:<20} {plugin['name']:<20} {plugin['version']:<10} {plugin['type']:<12} {plugin['author']:<20}")
        else:
            logger.info("No valid plugins found")

    def _generate_plugin_id(self, plugin_name: str) -> str:
        """生成插件ID"""
        # 转换为小写，用下划线替换空格和特殊字符
        import re
        plugin_id = re.sub(r'[^a-zA-Z0-9]', '_', plugin_name.lower())
        plugin_id = re.sub(r'_+', '_', plugin_id).strip('_')
        return plugin_id

    def _generate_metadata(self, plugin_id: str, plugin_name: str, plugin_type: str, author: str, email: str) -> Dict[str, Any]:
        """生成插件元数据"""
        from datetime import datetime

        return {
            "id": plugin_id,
            "name": plugin_name,
            "version": "1.0.0",
            "description": f"A {plugin_type} plugin for AI Hub",
            "author": author or "AI Hub Developer",
            "email": email or "developer@ai-hub.com",
            "license": "MIT",
            "homepage": "",
            "repository": "",
            "tags": [plugin_type],
            "category": plugin_type,
            "plugin_type": plugin_type,
            "dependencies": {},
            "min_hub_version": "1.0.0",
            "max_hub_version": None,
            "permissions": [],
            "resources": {},
            "config_schema": None,
            "default_config": {},
            "created_at": datetime.now().isoformat()
        }

    def _create_plugin_structure(self, plugin_dir: Path, metadata: Dict[str, Any], plugin_type: str):
        """创建插件文件结构"""
        # 创建目录结构
        (plugin_dir / "src").mkdir(exist_ok=True)
        (plugin_dir / "tests").mkdir(exist_ok=True)
        (plugin_dir / "docs").mkdir(exist_ok=True)
        (plugin_dir / "data").mkdir(exist_ok=True)

        # 创建__init__.py文件
        (plugin_dir / "src" / "__init__.py").touch()

    def _generate_plugin_code(self, plugin_dir: Path, metadata: Dict[str, Any], plugin_type: str):
        """生成插件代码"""
        plugin_id = metadata["id"]
        plugin_name = metadata["name"]

        # 生成主插件文件
        main_template = f'''"""
{plugin_name} Plugin
Generated by AI Hub Plugin CLI
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


class {self._to_class_name(plugin_id)}Plugin(PluginInterface):
    """{plugin_name} Plugin"""

    def __init__(self):
        super().__init__()
        self._running = False

    @property
    def metadata(self) -> PluginMetadata:
        """插件元数据"""
        from backend.core.plugin_system.plugin_interface import PluginMetadata, PluginType
        return PluginMetadata(
            id="{metadata["id"]}",
            name="{metadata["name"]}",
            version="{metadata["version"]}",
            description="{metadata["description"]}",
            author="{metadata["author"]}",
            email="{metadata["email"]}",
            license="{metadata["license"]}",
            homepage="{metadata["homepage"]}",
            repository="{metadata["repository"]}",
            tags={metadata["tags"]},
            category="{metadata["category"]}",
            plugin_type=PluginType.{plugin_type.upper()},
            dependencies={metadata["dependencies"]},
            min_hub_version="{metadata["min_hub_version"]}",
            max_hub_version={metadata["max_hub_version"]},
            permissions={metadata["permissions"]},
            resources={metadata["resources"]},
            config_schema={metadata["config_schema"]},
            default_config={metadata["default_config"]}
        )

    async def initialize(self, context: PluginContext) -> bool:
        """
        初始化插件
        """
        try:
            self._context = context
            self._status = PluginStatus.LOADING

            # TODO: 实现初始化逻辑
            logger.info(f"Initializing {{self.metadata.name}} plugin")

            # 示例：读取配置
            config = context.config
            logger.info(f"Plugin config: {{config}}")

            # 示例：订阅事件
            context.event_bus.subscribe(EventType.USER_ACTION, self.handle_event)

            self._status = PluginStatus.INACTIVE
            return True

        except Exception as e:
            logger.error(f"Failed to initialize plugin: {{e}}")
            self._status = PluginStatus.ERROR
            return False

    async def activate(self) -> bool:
        """
        激活插件
        """
        try:
            if self._status != PluginStatus.INACTIVE:
                return False

            # TODO: 实现激活逻辑
            logger.info(f"Activating {{self.metadata.name}} plugin")

            # 示例：启动后台任务
            self._running = True
            asyncio.create_task(self._background_task())

            self._status = PluginStatus.ACTIVE
            return True

        except Exception as e:
            logger.error(f"Failed to activate plugin: {{e}}")
            self._status = PluginStatus.ERROR
            return False

    async def deactivate(self) -> bool:
        """
        停用插件
        """
        try:
            if self._status != PluginStatus.ACTIVE:
                return False

            # TODO: 实现停用逻辑
            logger.info(f"Deactivating {{self.metadata.name}} plugin")

            # 停止后台任务
            self._running = False

            self._status = PluginStatus.INACTIVE
            return True

        except Exception as e:
            logger.error(f"Failed to deactivate plugin: {{e}}")
            return False

    async def cleanup(self) -> bool:
        """
        清理插件资源
        """
        try:
            logger.info(f"Cleaning up {{self.metadata.name}} plugin")

            # TODO: 实现清理逻辑
            self._running = False

            return True

        except Exception as e:
            logger.error(f"Failed to cleanup plugin: {{e}}")
            return False

    async def handle_event(self, event: Event) -> None:
        """
        处理事件
        """
        try:
            # TODO: 实现事件处理逻辑
            logger.debug(f"Handling event: {{event.type}} from {{event.source}}")

        except Exception as e:
            logger.error(f"Error handling event: {{e}}")

    async def _background_task(self):
        """
        后台任务示例
        """
        while self._running:
            try:
                # TODO: 实现后台逻辑
                await asyncio.sleep(10)  # 每10秒执行一次

            except Exception as e:
                logger.error(f"Error in background task: {{e}}")
                await asyncio.sleep(30)  # 错误时等待更长时间

    def get_health_check(self) -> Dict[str, Any]:
        """
        健康检查
        """
        return {{
            "status": "healthy" if self._status == PluginStatus.ACTIVE else "unhealthy",
            "timestamp": asyncio.get_event_loop().time(),
            "running": self._running,
            "checks": {{
                "background_task": self._running,
                "configuration": bool(self._context),
                "event_subscription": True
            }}
        }}


# 插件工厂函数
def create_plugin():
    return {self._to_class_name(plugin_id)}Plugin()


if __name__ == "__main__":
    # 插件测试代码
    plugin = create_plugin()
    print(f"Plugin {{plugin.metadata.name}} created successfully")
'''

        # 写入主文件
        main_file = plugin_dir / "main.py"
        with open(main_file, 'w', encoding='utf-8') as f:
            f.write(main_template)

        # 生成测试文件
        test_template = f'''"""
{plugin_name} Plugin Tests
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from main import {self._to_class_name(plugin_id)}Plugin


class Test{self._to_class_name(plugin_id)}Plugin:
    """{plugin_name} Plugin Tests"""

    @pytest.fixture
    def plugin(self):
        return {self._to_class_name(plugin_id)}Plugin()

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.config = {{}}
        context.event_bus = Mock()
        context.event_bus.subscribe = Mock()
        context.storage_manager = Mock()
        context.api_client = Mock()
        context.logger = Mock()
        context.permissions = []
        context.resources = {{}}
        return context

    @pytest.mark.asyncio
    async def test_initialize(self, plugin, mock_context):
        """测试插件初始化"""
        result = await plugin.initialize(mock_context)
        assert result is True
        assert plugin.context == mock_context

    @pytest.mark.asyncio
    async def test_activate(self, plugin, mock_context):
        """测试插件激活"""
        await plugin.initialize(mock_context)
        result = await plugin.activate()
        assert result is True
        assert plugin._running is True

    @pytest.mark.asyncio
    async def test_deactivate(self, plugin, mock_context):
        """测试插件停用"""
        await plugin.initialize(mock_context)
        await plugin.activate()
        result = await plugin.deactivate()
        assert result is True
        assert plugin._running is False

    @pytest.mark.asyncio
    async def test_cleanup(self, plugin, mock_context):
        """测试插件清理"""
        await plugin.initialize(mock_context)
        result = await plugin.cleanup()
        assert result is True

    def test_metadata(self, plugin):
        """测试插件元数据"""
        metadata = plugin.metadata
        assert metadata.id == "{plugin_id}"
        assert metadata.name == "{plugin_name}"
        assert metadata.version == "1.0.0"

    def test_health_check(self, plugin):
        """测试健康检查"""
        health = plugin.get_health_check()
        assert "status" in health
        assert "timestamp" in health
        assert "checks" in health


if __name__ == "__main__":
    pytest.main([__file__])
'''

        test_file = plugin_dir / "tests" / "test_main.py"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_template)

    def _generate_config_files(self, plugin_dir: Path, metadata: Dict[str, Any]):
        """生成配置文件"""
        # 写入plugin.json
        with open(plugin_dir / "plugin.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # 生成requirements.txt
        requirements = """# Plugin dependencies
# Add your plugin dependencies here

# Development dependencies
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
"""

        with open(plugin_dir / "requirements.txt", 'w', encoding='utf-8') as f:
            f.write(requirements)

        # 生成setup.py
        setup_template = f'''"""
Setup script for {metadata["name"]} plugin
"""

from setuptools import setup, find_packages

setup(
    name="{metadata["id"]}",
    version="{metadata["version"]}",
    description="{metadata["description"]}",
    author="{metadata["author"]}",
    author_email="{metadata["email"]}",
    license="{metadata["license"]}",
    packages=find_packages(),
    install_requires=[
        # Add your dependencies here
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
'''

        with open(plugin_dir / "setup.py", 'w', encoding='utf-8') as f:
            f.write(setup_template)

        # 生成README.md
        readme_template = f'''# {metadata["name"]}

{metadata["description"]}

## 安装

```bash
# 使用CLI工具安装
python scripts/plugin_cli.py install {metadata["id"]}-v{metadata["version"]}.zip

# 或手动安装
1. 下载插件包
2. 解压到 AI Hub 插件目录
3. 重启 AI Hub
```

## 配置

插件支持以下配置选项：

```json
{{
    // 添加配置选项
}}
```

## 使用

{metadata["description"]}

## 开发

```bash
# 安装开发依赖
pip install -r requirements.txt

# 运行测试
python scripts/plugin_cli.py test {metadata["id"]}

# 构建插件
python scripts/plugin_cli.py build {metadata["id"]}

# 打包插件
python scripts/plugin_cli.py package {metadata["id"]}
```

## 作者

- {metadata["author"]} ({metadata["email"]})

## 许可证

{metadata["license"]}

## 贡献

欢迎提交 Issue 和 Pull Request！
'''

        with open(plugin_dir / "README.md", 'w', encoding='utf-8') as f:
            f.write(readme_template)

    def _to_class_name(self, plugin_id: str) -> str:
        """转换为类名"""
        return ''.join(word.capitalize() for word in plugin_id.split('_'))

    def _validate_plugin(self, plugin_dir: Path) -> bool:
        """验证插件"""
        required_files = ["plugin.json", "main.py", "README.md"]
        for file_name in required_files:
            if not (plugin_dir / file_name).exists():
                logger.error(f"Required file {file_name} not found")
                return False

        # 验证plugin.json
        try:
            with open(plugin_dir / "plugin.json", 'r') as f:
                metadata = json.load(f)
                required_fields = ["id", "name", "version", "description", "author"]
                for field in required_fields:
                    if field not in metadata:
                        logger.error(f"Required field {field} missing in plugin.json")
                        return False
        except Exception as e:
            logger.error(f"Invalid plugin.json: {e}")
            return False

        return True

    def _run_tests(self, plugin_dir: Path, verbose: bool = False) -> bool:
        """运行测试"""
        test_dir = plugin_dir / "tests"
        if not test_dir.exists():
            logger.warning("No tests found")
            return True

        try:
            cmd = [sys.executable, "-m", "pytest", str(test_dir)]
            if verbose:
                cmd.append("-v")

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=plugin_dir)

            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to run tests: {e}")
            return False

    def _copy_build_files(self, plugin_dir: Path, build_dir: Path):
        """复制构建文件"""
        files_to_copy = [
            "plugin.json",
            "main.py",
            "README.md",
            "requirements.txt"
        ]

        for file_name in files_to_copy:
            src = plugin_dir / file_name
            dst = build_dir / file_name
            if src.exists():
                shutil.copy2(src, dst)

        # 复制src目录
        src_dir = plugin_dir / "src"
        if src_dir.exists():
            shutil.copytree(src_dir, build_dir / "src")

    def _generate_documentation(self, plugin_dir: Path, build_dir: Path):
        """生成文档"""
        docs_dir = build_dir / "docs"
        docs_dir.mkdir(exist_ok=True)

        # 生成API文档
        api_doc = f"""# API Documentation

## Plugin: {plugin_dir.name}

### Configuration

Configuration options for this plugin.

### Methods

- `initialize()`: Initialize the plugin
- `activate()`: Activate the plugin
- `deactivate()`: Deactivate the plugin
- `cleanup()`: Cleanup plugin resources
- `handle_event()`: Handle events

### Events

This plugin responds to the following events:
- USER_ACTION

### Example Usage

```python
# Example usage code
```
"""

        with open(docs_dir / "api.md", 'w', encoding='utf-8') as f:
            f.write(api_doc)

    def _validate_package(self, package_dir: Path) -> Optional[str]:
        """验证插件包"""
        metadata_file = package_dir / "plugin.json"
        if not metadata_file.exists():
            logger.error("plugin.json not found in package")
            return None

        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                return metadata.get("id")
        except Exception as e:
            logger.error(f"Failed to read package metadata: {e}")
            return None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI Hub Plugin CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # create命令
    create_parser = subparsers.add_parser("create", help="Create a new plugin")
    create_parser.add_argument("name", help="Plugin name")
    create_parser.add_argument("--type", default="utility", help="Plugin type")
    create_parser.add_argument("--author", help="Author name")
    create_parser.add_argument("--email", help="Author email")

    # build命令
    build_parser = subparsers.add_parser("build", help="Build a plugin")
    build_parser.add_argument("plugin_id", help="Plugin ID")

    # test命令
    test_parser = subparsers.add_parser("test", help="Test a plugin")
    test_parser.add_argument("plugin_id", help="Plugin ID")
    test_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # package命令
    package_parser = subparsers.add_parser("package", help="Package a plugin")
    package_parser.add_argument("plugin_id", help="Plugin ID")
    package_parser.add_argument("--format", default="zip", choices=["zip", "tar.gz"], help="Package format")

    # install命令
    install_parser = subparsers.add_parser("install", help="Install a plugin package")
    install_parser.add_argument("package", help="Package file path")

    # list命令
    subparsers.add_parser("list", help="List all plugins")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = PluginCLI()

    if args.command == "create":
        cli.create_plugin(args.name, args.type, args.author, args.email)
    elif args.command == "build":
        cli.build_plugin(args.plugin_id)
    elif args.command == "test":
        cli.test_plugin(args.plugin_id, args.verbose)
    elif args.command == "package":
        cli.package_plugin(args.plugin_id, args.format)
    elif args.command == "install":
        cli.install_plugin(args.package)
    elif args.command == "list":
        cli.list_plugins()


if __name__ == "__main__":
    main()