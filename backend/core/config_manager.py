"""
配置文件管理器
用于动态管理应用配置和特性开关
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

@dataclass
class FeatureFlag:
    """特性开关"""
    name: str
    enabled: bool
    description: str
    rollout_percentage: int = 100
    last_updated: Optional[str] = None

@dataclass
class AppConfig:
    """应用配��"""
    debug_mode: bool = False
    enable_rate_limiting: bool = True
    enable_request_logging: bool = True
    enable_response_cache: bool = True
    enable_analytics: bool = False
    max_requests_per_minute: int = 60
    cache_ttl_seconds: int = 300
    maintenance_mode: bool = False
    allowed_origins: List[str] = None

    def __post_init__(self):
        if self.allowed_origins is None:
            self.allowed_origins = ["http://localhost:3000", "http://localhost:8080"]

class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.app_config_file = self.config_dir / "app_config.json"
        self.feature_flags_file = self.config_dir / "feature_flags.json"
        self._executor = ThreadPoolExecutor(max_workers=2)

        # 内存缓存
        self._app_config: Optional[AppConfig] = None
        self._feature_flags: Dict[str, FeatureFlag] = {}
        self._last_load_time: Optional[float] = None

    async def _read_json_file(self, file_path: Path) -> Dict[str, Any]:
        """异步读取JSON文件"""
        loop = asyncio.get_event_loop()

        def _read():
            if not file_path.exists():
                return {}
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        return await loop.run_in_executor(self._executor, _read)

    async def _write_json_file(self, file_path: Path, data: Dict[str, Any]):
        """异步写入JSON文件"""
        loop = asyncio.get_event_loop()

        def _write():
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        await loop.run_in_executor(self._executor, _write)

    async def load_app_config(self) -> AppConfig:
        """加载应用配置"""
        if (self._app_config is None or
            self._last_load_time is None or
            time.time() - self._last_load_time > 60):  # 1分钟缓存

            try:
                config_data = await self._read_json_file(self.app_config_file)
                self._app_config = AppConfig(**config_data)
                self._last_load_time = time.time()
            except Exception as e:
                print(f"加载应用配置失败，使用默认配置: {e}")
                self._app_config = AppConfig()
                self._last_load_time = time.time()

        return self._app_config

    async def save_app_config(self, config: AppConfig):
        """保存应用配置"""
        try:
            config_dict = asdict(config)
            await self._write_json_file(self.app_config_file, config_dict)
            self._app_config = config
            self._last_load_time = time.time()
            return True
        except Exception as e:
            print(f"保存应用配置失败: {e}")
            return False

    async def load_feature_flags(self) -> Dict[str, FeatureFlag]:
        """加载特性开关"""
        try:
            flags_data = await self._read_json_file(self.feature_flags_file)

            for flag_name, flag_data in flags_data.items():
                if isinstance(flag_data, dict):
                    self._feature_flags[flag_name] = FeatureFlag(
                        name=flag_name,
                        **flag_data
                    )
                else:
                    # 简单的布尔值格式
                    self._feature_flags[flag_name] = FeatureFlag(
                        name=flag_name,
                        enabled=bool(flag_data),
                        description=f"特性开关: {flag_name}"
                    )

        except Exception as e:
            print(f"加载特性开关失败: {e}")
            # 设置默认特性开关
            self._set_default_feature_flags()

        return self._feature_flags

    def _set_default_feature_flags(self):
        """设置默认特性开关"""
        default_flags = {
            "new_ui_theme": FeatureFlag(
                name="new_ui_theme",
                enabled=False,
                description="新UI主题",
                rollout_percentage=50
            ),
            "advanced_analytics": FeatureFlag(
                name="advanced_analytics",
                enabled=True,
                description="高级分析功能"
            ),
            "beta_models": FeatureFlag(
                name="beta_models",
                enabled=False,
                description="测试版AI模型",
                rollout_percentage=20
            ),
            "export_features": FeatureFlag(
                name="export_features",
                enabled=True,
                description="导出功能"
            ),
            "real_time_collaboration": FeatureFlag(
                name="real_time_collaboration",
                enabled=False,
                description="实时协作功能"
            )
        }
        self._feature_flags = default_flags

    async def save_feature_flags(self):
        """保存特性开关"""
        try:
            flags_data = {}
            for flag_name, flag in self._feature_flags.items():
                flags_data[flag_name] = asdict(flag)

            await self._write_json_file(self.feature_flags_file, flags_data)
            return True
        except Exception as e:
            print(f"保存特性开关失败: {e}")
            return False

    async def is_feature_enabled(self, feature_name: str, user_id: Optional[str] = None) -> bool:
        """检查特性是否启用"""
        await self.load_feature_flags()

        if feature_name not in self._feature_flags:
            return False

        flag = self._feature_flags[feature_name]

        if not flag.enabled:
            return False

        # 检查渐进式发布
        if flag.rollout_percentage < 100 and user_id:
            # 基于用户ID的哈希进行渐进式发布
            import hashlib
            hash_value = int(hashlib.md5(f"{feature_name}:{user_id}".encode()).hexdigest(), 16)
            if (hash_value % 100) >= flag.rollout_percentage:
                return False

        return True

    async def update_feature_flag(self, feature_name: str, enabled: bool,
                                description: str = None, rollout_percentage: int = None):
        """更新特性开关"""
        await self.load_feature_flags()

        if feature_name not in self._feature_flags:
            self._feature_flags[feature_name] = FeatureFlag(
                name=feature_name,
                enabled=enabled,
                description=description or f"特性开关: {feature_name}",
                rollout_percentage=rollout_percentage or 100,
                last_updated=datetime.now().isoformat()
            )
        else:
            flag = self._feature_flags[feature_name]
            flag.enabled = enabled
            if description is not None:
                flag.description = description
            if rollout_percentage is not None:
                flag.rollout_percentage = rollout_percentage
            flag.last_updated = datetime.now().isoformat()

        return await self.save_feature_flags()

    async def get_all_configs(self) -> Dict[str, Any]:
        """获取所有配置"""
        app_config = await self.load_app_config()
        feature_flags = await self.load_feature_flags()

        return {
            "app_config": asdict(app_config),
            "feature_flags": {
                name: asdict(flag) for name, flag in feature_flags.items()
            },
            "last_updated": datetime.now().isoformat()
        }

    async def reset_to_defaults(self):
        """重置为默认配置"""
        try:
            # 重置应用配置
            default_config = AppConfig()
            await self.save_app_config(default_config)

            # 重置特性开关
            self._set_default_feature_flags()
            await self.save_feature_flags()

            return True
        except Exception as e:
            print(f"重置配置失败: {e}")
            return False

    async def cleanup(self):
        """清理资源"""
        self._executor.shutdown(wait=False)

# 全局配置管理器实例
config_manager = ConfigManager()

async def get_app_config() -> AppConfig:
    """获取应用配置"""
    return await config_manager.load_app_config()

async def is_feature_enabled(feature_name: str, user_id: Optional[str] = None) -> bool:
    """检查特性是否启用"""
    return await config_manager.is_feature_enabled(feature_name, user_id)