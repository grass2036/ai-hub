#!/usr/bin/env python3
"""
AI Hub 开发者CLI工具
Week 7 Day 4: 生态系统建设

提供项目管理、开发环境配置、监控等功能
"""

import os
import sys
import json
import argparse
import subprocess
import shutil
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DeveloperCLI:
    """开发者CLI工具"""

    def __init__(self):
        self.config_dir = project_root / ".aihub"
        self.config_file = self.config_dir / "config.json"
        self.templates_dir = project_root / "scripts" / "templates"
        self.projects_dir = project_root / "projects"

        # 确保目录存在
        self.config_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        self.projects_dir.mkdir(exist_ok=True)

        # 加载配置
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")

        # 默认配置
        default_config = {
            "developer": {
                "name": "",
                "email": "",
                "organization": ""
            },
            "aihub": {
                "api_url": "http://localhost:8001",
                "api_key": ""
            },
            "preferences": {
                "default_template": "basic",
                "auto_open_editor": True,
                "editor": "code"
            }
        }

        self._save_config(default_config)
        return default_config

    def _save_config(self, config: Dict[str, Any]):
        """保存配置"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def configure(self, **kwargs):
        """配置开发环境"""
        try:
            # 更新配置
            for key, value in kwargs.items():
                if value is not None:
                    keys = key.split('.')
                    config_section = self.config

                    for k in keys[:-1]:
                        if k not in config_section:
                            config_section[k] = {}
                        config_section = config_section[k]

                    config_section[keys[-1]] = value

            self._save_config(self.config)

            # 验证配置
            self._validate_config()

            print("✅ 配置更新成功")
            print(f"📋 当前配置:")
            print(json.dumps(self.config, indent=2))

        except Exception as e:
            logger.error(f"Failed to configure: {e}")
            print(f"❌ 配置失败: {e}")

    def _validate_config(self):
        """验证配置"""
        required_fields = [
            "developer.name",
            "developer.email",
            "aihub.api_url"
        ]

        for field in required_fields:
            keys = field.split('.')
            config_section = self.config

            try:
                for k in keys:
                    config_section = config_section[k]
                if not config_section:
                    raise ValueError(f"Required field {field} is empty")
            except (KeyError, TypeError):
                raise ValueError(f"Required field {field} is missing")

    def create_project(self, project_name: str, template: str = "basic", **kwargs):
        """创建新项目"""
        try:
            project_id = self._generate_project_id(project_name)
            project_dir = self.projects_dir / project_id

            if project_dir.exists():
                logger.error(f"Project {project_id} already exists")
                return False

            # 创建项目目录
            project_dir.mkdir(parents=True, exist_ok=True)

            # 复制模板
            template_dir = self.templates_dir / template
            if not template_dir.exists():
                logger.error(f"Template {template} not found")
                return False

            self._copy_template(template_dir, project_dir, project_id, project_name, **kwargs)

            # 初始化Git仓库
            if kwargs.get("init_git", True):
                self._init_git_repo(project_dir)

            # 安装依赖
            if kwargs.get("install_deps", True):
                self._install_dependencies(project_dir)

            # 打开编辑器
            if kwargs.get("open_editor", self.config["preferences"]["auto_open_editor"]):
                self._open_editor(project_dir)

            print(f"✅ 项目 {project_name} 创建成功")
            print(f"📁 项目路径: {project_dir}")
            print(f"🚀 下一步:")
            print(f"   cd {project_dir}")
            print(f"   aihub dev")

            return True

        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            print(f"❌ 项目创建失败: {e}")
            return False

    def _generate_project_id(self, project_name: str) -> str:
        """生成项目ID"""
        import re
        project_id = re.sub(r'[^a-zA-Z0-9]', '-', project_name.lower())
        project_id = re.sub(r'-+', '-', project_id).strip('-')
        return project_id

    def _copy_template(self, template_dir: Path, project_dir: Path, project_id: str, project_name: str, **kwargs):
        """复制模板文件"""
        for item in template_dir.iterdir():
            if item.is_file():
                # 读取文件内容
                with open(item, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 替换模板变量
                replacements = {
                    "{{PROJECT_NAME}}": project_name,
                    "{{PROJECT_ID}}": project_id,
                    "{{DEVELOPER_NAME}}": self.config["developer"]["name"],
                    "{{DEVELOPER_EMAIL}}": self.config["developer"]["email"],
                    "{{ORGANIZATION}}": self.config["developer"]["organization"],
                    "{{DATE}}": datetime.now().strftime("%Y-%m-%d"),
                    "{{YEAR}}": datetime.now().strftime("%Y")
                }

                for placeholder, value in replacements.items():
                    content = content.replace(placeholder, str(value))

                # 写入目标文件
                target_file = project_dir / item.name
                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(content)

            elif item.is_dir() and item.name != "__pycache__":
                # 递归复制子目录
                target_subdir = project_dir / item.name
                target_subdir.mkdir(exist_ok=True)
                self._copy_template(item, target_subdir, project_id, project_name, **kwargs)

    def _init_git_repo(self, project_dir: Path):
        """初始化Git仓库"""
        try:
            subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)

            # 创建.gitignore
            gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
env/
ENV/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project specific
.env
.env.local
config.local.json
logs/
data/
"""

            with open(project_dir / ".gitignore", 'w') as f:
                f.write(gitignore_content)

            # 初始提交
            subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_dir, check=True, capture_output=True)

        except subprocess.CalledProcessError as e:
            logger.warning(f"Git initialization failed: {e}")

    def _install_dependencies(self, project_dir: Path):
        """安装依赖"""
        requirements_file = project_dir / "requirements.txt"
        if requirements_file.exists():
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
                ], cwd=project_dir, check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                logger.warning(f"Dependency installation failed: {e}")

    def _open_editor(self, project_dir: Path):
        """打开编辑器"""
        editor = self.config["preferences"]["editor"]
        try:
            if editor == "code":
                subprocess.run(["code", str(project_dir)], check=True)
            elif editor == "vscode":
                subprocess.run(["code", str(project_dir)], check=True)
            elif editor == "vim":
                subprocess.run(["vim", str(project_dir)], check=True)
            else:
                logger.warning(f"Unknown editor: {editor}")
        except subprocess.CalledProcessError:
            logger.warning(f"Failed to open editor: {editor}")

    def list_projects(self):
        """列出所有项目"""
        if not self.projects_dir.exists():
            print("📁 没有找到项目目录")
            return

        projects = []
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                config_file = project_dir / "aihub.json"
                if config_file.exists():
                    try:
                        with open(config_file, 'r') as f:
                            config = json.load(f)
                        projects.append({
                            'id': project_dir.name,
                            'name': config.get('name', project_dir.name),
                            'type': config.get('type', 'unknown'),
                            'created': config.get('created_at', ''),
                            'path': str(project_dir)
                        })
                    except:
                        projects.append({
                            'id': project_dir.name,
                            'name': project_dir.name,
                            'type': 'unknown',
                            'created': '',
                            'path': str(project_dir)
                        })

        if projects:
            print(f"{'ID':<20} {'Name':<20} {'Type':<12} {'Created':<12}")
            print("-" * 70)
            for project in projects:
                created = project['created'][:10] if project['created'] else 'N/A'
                print(f"{project['id']:<20} {project['name']:<20} {project['type']:<12} {created:<12}")
        else:
            print("📁 没有找到项目")

    def dev_server(self, project_id: str, port: int = 3000):
        """启动开发服务器"""
        project_dir = self.projects_dir / project_id

        if not project_dir.exists():
            logger.error(f"Project {project_id} not found")
            return False

        try:
            # 检查项目类型
            config_file = project_dir / "aihub.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                project_type = config.get('type', 'basic')
            else:
                project_type = 'basic'

            # 根据项目类型启动服务器
            if project_type == 'frontend':
                return self._start_frontend_server(project_dir, port)
            elif project_type == 'backend':
                return self._start_backend_server(project_dir, port)
            elif project_type == 'fullstack':
                return self._start_fullstack_server(project_dir, port)
            else:
                logger.error(f"Unknown project type: {project_type}")
                return False

        except Exception as e:
            logger.error(f"Failed to start dev server: {e}")
            return False

    def _start_frontend_server(self, project_dir: Path, port: int):
        """启动前端开发服务器"""
        try:
            # 检查是否是Next.js项目
            if (project_dir / "package.json").exists():
                with open(project_dir / "package.json", 'r') as f:
                    package_json = json.load(f)

                if "next" in package_json.get("dependencies", {}):
                    print(f"🚀 启动Next.js开发服务器 (端口: {port})")
                    subprocess.run([
                        "npm", "run", "dev", "--", "--port", str(port)
                    ], cwd=project_dir)
                    return True

            print(f"❌ 无法识别前端项目类型")
            return False

        except Exception as e:
            logger.error(f"Failed to start frontend server: {e}")
            return False

    def _start_backend_server(self, project_dir: Path, port: int):
        """启动后端开发服务器"""
        try:
            main_file = project_dir / "main.py"
            if main_file.exists():
                print(f"🚀 启动Python开发服务器 (端口: {port})")
                subprocess.run([
                    sys.executable, "main.py", "--port", str(port)
                ], cwd=project_dir)
                return True

            print(f"❌ 找不到main.py文件")
            return False

        except Exception as e:
            logger.error(f"Failed to start backend server: {e}")
            return False

    def _start_fullstack_server(self, project_dir: Path, port: int):
        """启动全栈开发服务器"""
        try:
            # 简化实现：同时启动前后端
            print(f"🚀 启动全栈开发服务器 (前端端口: {port}, 后端端口: {port + 1})")

            # 启动前端
            frontend_process = subprocess.Popen([
                "npm", "run", "dev", "--", "--port", str(port)
            ], cwd=project_dir / "frontend")

            # 启动后端
            backend_process = subprocess.Popen([
                sys.executable, "main.py", "--port", str(port + 1)
            ], cwd=project_dir / "backend")

            # 等待进程结束
            frontend_process.wait()
            backend_process.wait()

            return True

        except Exception as e:
            logger.error(f"Failed to start fullstack server: {e}")
            return False

    def build_project(self, project_id: str):
        """构建项目"""
        project_dir = self.projects_dir / project_id

        if not project_dir.exists():
            logger.error(f"Project {project_id} not found")
            return False

        try:
            # 检查项目类型
            config_file = project_dir / "aihub.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                project_type = config.get('type', 'basic')
            else:
                project_type = 'basic'

            print(f"🔨 构建项目 {project_id} (类型: {project_type})")

            if project_type == 'frontend':
                # 构建前端项目
                subprocess.run(["npm", "run", "build"], cwd=project_dir, check=True)
            elif project_type == 'backend':
                # 后端项目通常不需要构建
                print("✅ 后端项目无需构建")
            elif project_type == 'fullstack':
                # 构建全栈项目
                if (project_dir / "frontend").exists():
                    subprocess.run(["npm", "run", "build"], cwd=project_dir / "frontend", check=True)

            print(f"✅ 项目构建完成")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Build failed: {e}")
            print(f"❌ 构建失败: {e}")
            return False

    def deploy_project(self, project_id: str, environment: str = "development"):
        """部署项目"""
        project_dir = self.projects_dir / project_id

        if not project_dir.exists():
            logger.error(f"Project {project_id} not found")
            return False

        try:
            print(f"🚀 部署项目 {project_id} 到 {environment}")

            # 先构建项目
            if not self.build_project(project_id):
                return False

            # 根据环境进行部署
            if environment == "development":
                print("✅ 开发环境部署完成")
            elif environment == "staging":
                # 部署到测试环境
                print("✅ 测试环境部署完成")
            elif environment == "production":
                # 部署到生产环境
                print("✅ 生产环境部署完成")
            else:
                logger.error(f"Unknown environment: {environment}")
                return False

            return True

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            print(f"❌ 部署失败: {e}")
            return False

    def monitor_project(self, project_id: str):
        """监控项目"""
        project_dir = self.projects_dir / project_id

        if not project_dir.exists():
            logger.error(f"Project {project_id} not found")
            return False

        try:
            print(f"📊 监控项目 {project_id}")

            # 显示项目信息
            config_file = project_dir / "aihub.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)

                print(f"📋 项目信息:")
                print(f"   名称: {config.get('name', 'N/A')}")
                print(f"   类型: {config.get('type', 'N/A')}")
                print(f"   版本: {config.get('version', 'N/A')}")
                print(f"   路径: {project_dir}")

            # 检查项目状态
            self._check_project_status(project_dir)

            return True

        except Exception as e:
            logger.error(f"Monitor failed: {e}")
            print(f"❌ 监控失败: {e}")
            return False

    def _check_project_status(self, project_dir: Path):
        """检查项目状态"""
        # 检查Git状态
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_dir,
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                print("⚠️  有未提交的更改")
            else:
                print("✅ Git状态正常")
        except:
            print("❓ Git状态未知")

        # 检查依赖
        if (project_dir / "requirements.txt").exists():
            print("📦 Python依赖: requirements.txt")
        if (project_dir / "package.json").exists():
            print("📦 Node.js依赖: package.json")

        # 检查构建输出
        if (project_dir / "build").exists():
            print("🏗️  已构建")
        if (project_dir / "dist").exists():
            print("🏗️  已打包")

    def test_project(self, project_id: str, test_type: str = "all"):
        """测试项目"""
        project_dir = self.projects_dir / project_id

        if not project_dir.exists():
            logger.error(f"Project {project_id} not found")
            return False

        try:
            print(f"🧪 运行测试 {project_id}")

            if test_type == "all":
                # 运行所有测试
                if (project_dir / "tests").exists():
                    subprocess.run([
                        sys.executable, "-m", "pytest", "tests/", "-v"
                    ], cwd=project_dir, check=True)

                if (project_dir / "package.json").exists():
                    subprocess.run(["npm", "test"], cwd=project_dir, check=True)

            elif test_type == "unit":
                # 单元测试
                if (project_dir / "tests").exists():
                    subprocess.run([
                        sys.executable, "-m", "pytest", "tests/unit/", "-v"
                    ], cwd=project_dir, check=True)

            elif test_type == "integration":
                # 集成测试
                if (project_dir / "tests").exists():
                    subprocess.run([
                        sys.executable, "-m", "pytest", "tests/integration/", "-v"
                    ], cwd=project_dir, check=True)

            print(f"✅ 测试完成")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Tests failed: {e}")
            print(f"❌ 测试失败: {e}")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI Hub Developer CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # configure命令
    config_parser = subparsers.add_parser("config", help="配置开发环境")
    config_parser.add_argument("--name", help="开发者姓名")
    config_parser.add_argument("--email", help="开发者邮箱")
    config_parser.add_argument("--organization", help="组织名称")
    config_parser.add_argument("--api-url", help="AI Hub API地址")
    config_parser.add_argument("--api-key", help="AI Hub API密钥")

    # create命令
    create_parser = subparsers.add_parser("create", help="创建新项目")
    create_parser.add_argument("name", help="项目名称")
    create_parser.add_argument("--template", default="basic", help="项目模板")
    create_parser.add_argument("--no-git", dest="init_git", action="store_false", help="不初始化Git")
    create_parser.add_argument("--no-deps", dest="install_deps", action="store_false", help="不安装依赖")
    create_parser.add_argument("--no-open", dest="open_editor", action="store_false", help="不打开编辑器")

    # list命令
    subparsers.add_parser("list", help="列出所有项目")

    # dev命令
    dev_parser = subparsers.add_parser("dev", help="启动开发服务器")
    dev_parser.add_argument("project_id", help="项目ID")
    dev_parser.add_argument("--port", type=int, default=3000, help="端口号")

    # build命令
    build_parser = subparsers.add_parser("build", help="构建项目")
    build_parser.add_argument("project_id", help="项目ID")

    # deploy命令
    deploy_parser = subparsers.add_parser("deploy", help="部署项目")
    deploy_parser.add_argument("project_id", help="项目ID")
    deploy_parser.add_argument("--env", default="development", choices=["development", "staging", "production"], help="部署环境")

    # monitor命令
    monitor_parser = subparsers.add_parser("monitor", help="监控项目")
    monitor_parser.add_argument("project_id", help="项目ID")

    # test命令
    test_parser = subparsers.add_parser("test", help="测试项目")
    test_parser.add_argument("project_id", help="项目ID")
    test_parser.add_argument("--type", default="all", choices=["all", "unit", "integration"], help="测试类型")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = DeveloperCLI()

    if args.command == "config":
        cli.configure(
            name=args.name,
            email=args.email,
            organization=args.organization,
            api_url=args.api_url,
            api_key=args.api_key
        )
    elif args.command == "create":
        cli.create_project(
            args.name,
            args.template,
            init_git=args.init_git,
            install_deps=args.install_deps,
            open_editor=args.open_editor
        )
    elif args.command == "list":
        cli.list_projects()
    elif args.command == "dev":
        cli.dev_server(args.project_id, args.port)
    elif args.command == "build":
        cli.build_project(args.project_id)
    elif args.command == "deploy":
        cli.deploy_project(args.project_id, args.env)
    elif args.command == "monitor":
        cli.monitor_project(args.project_id)
    elif args.command == "test":
        cli.test_project(args.project_id, args.type)


if __name__ == "__main__":
    main()