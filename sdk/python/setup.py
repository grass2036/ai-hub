"""
AI Hub Platform Python SDK 安装配置
"""

from setuptools import setup, find_packages
import os

# 读取README文件
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

# 读取requirements文件
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(requirements_path):
        with open(requirements_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return ["requests>=2.25.0"]

setup(
    name="ai-hub-python",
    version="1.0.0",
    description="AI Hub Platform Python SDK - 企业级AI应用平台开发工具包",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="AI Hub Platform Team",
    author_email="support@aihub.com",
    url="https://github.com/ai-hub/platform",
    project_urls={
        "Documentation": "https://docs.aihub.com",
        "Source": "https://github.com/ai-hub/platform",
        "Tracker": "https://github.com/ai-hub/platform/issues",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.7",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.900",
            "pre-commit>=2.0",
        ],
        "docs": [
            "sphinx>=4.0",
            "sphinx-rtd-theme>=1.0",
            "myst-parser>=0.15",
        ],
    },
    entry_points={
        "console_scripts": [
            "ai-hub=ai_hub.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "ai_hub": ["py.typed"],
    },
    keywords=[
        "ai hub",
        "artificial intelligence",
        "machine learning",
        "api",
        "chat",
        "llm",
        "gpt",
        "claude",
        "enterprise",
    ],
    license="MIT",
    zip_safe=False,
)