"""
区域化缓存管理模块
Regional Cache Management Module

实现基于地理位置的智能缓存策略
Implements geography-based intelligent caching strategies
"""

import logging
import json
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from pydantic import BaseModel
import redis.asyncio as redis
from pathlib import Path

logger = logging.getLogger(__name__)

class CacheRegion(Enum):
    """缓存区域枚举"""
    ASIA_PACIFIC = "asia_pacific"
    EUROPE = "europe"
    AMERICAS = "americas"
    CHINA = "china"
    MIDDLE_EAST = "middle_east"
    AFRICA = "africa"

class CacheLevel(Enum):
    """缓存级别枚举"""
    L1_EDGE = "l1_edge"           # 边缘节点缓存
    L2_REGIONAL = "l2_regional"   # 区域缓存
    L3_GLOBAL = "l3_global"       # 全球���存

class CachePolicy(BaseModel):
    """缓存策略"""
    policy_id: str
    name: str
    content_type: str
    cache_levels: List[CacheLevel]
    ttl: Dict[CacheLevel, int]     # 各级别TTL（秒）
    max_size: Dict[CacheLevel, int] # 各级别最大大小（MB）
    compression_enabled: bool
    encryption_enabled: bool
    geo_restrictions: List[str]
    vary_headers: List[str]

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    content_type: str
    created_at: datetime
    expires_at: datetime
    access_count: int
    last_accessed: datetime
    size_bytes: int
    cache_level: CacheLevel
    region: CacheRegion
    checksum: str

class RegionCacheManager:
    """区域缓存管理器"""

    def __init__(self, config_path: str = "config/cache_config.json"):
        self.config_path = Path(config_path)
        self.cache_connections: Dict[CacheRegion, redis.Redis] = {}
        self.cache_policies: Dict[str, CachePolicy] = {}
        self.cache_stats: Dict[CacheRegion, Dict[str, Any]] = {}

        # 初始化配置
        self._load_config()
        self._initialize_connections()

        logger.info("Region cache manager initialized")

    def _load_config(self):
        """加载缓存配置"""
        default_config = {
            "regions": {
                "asia_pacific": {
                    "host": "redis-ap-southeast-1.ai-hub.com",
                    "port": 6379,
                    "db": 0,
                    "max_connections": 100,
                    "max_memory": "8gb"
                },
                "europe": {
                    "host": "redis-eu-central-1.ai-hub.com",
                    "port": 6379,
                    "db": 0,
                    "max_connections": 100,
                    "max_memory": "6gb"
                },
                "americas": {
                    "host": "redis-us-east-1.ai-hub.com",
                    "port": 6379,
                    "db": 0,
                    "max_connections": 150,
                    "max_memory": "12gb"
                }
            },
            "policies": {
                "static_assets": {
                    "policy_id": "static_assets",
                    "name": "Static Assets Policy",
                    "content_type": "static",
                    "cache_levels": ["l1_edge", "l2_regional", "l3_global"],
                    "ttl": {
                        "l1_edge": 86400,    # 1天
                        "l2_regional": 604800, # 7天
                        "l3_global": 2592000  # 30天
                    },
                    "max_size": {
                        "l1_edge": 1000,     # 1GB
                        "l2_regional": 5000,  # 5GB
                        "l3_global": 20000    # 20GB
                    },
                    "compression_enabled": True,
                    "encryption_enabled": False,
                    "geo_restrictions": [],
                    "vary_headers": ["Accept-Encoding"]
                },
                "api_responses": {
                    "policy_id": "api_responses",
                    "name": "API Responses Policy",
                    "content_type": "api",
                    "cache_levels": ["l1_edge", "l2_regional"],
                    "ttl": {
                        "l1_edge": 300,      # 5分钟
                        "l2_regional": 900   # 15分钟
                    },
                    "max_size": {
                        "l1_edge": 500,      # 500MB
                        "l2_regional": 2000   # 2GB
                    },
                    "compression_enabled": True,
                    "encryption_enabled": True,
                    "geo_restrictions": [],
                    "vary_headers": ["Accept-Language", "Authorization"]
                },
                "user_data": {
                    "policy_id": "user_data",
                    "name": "User Data Policy",
                    "content_type": "personal",
                    "cache_levels": ["l2_regional"],
                    "ttl": {
                        "l2_regional": 1800   # 30分钟
                    },
                    "max_size": {
                        "l2_regional": 1000   # 1GB
                    },
                    "compression_enabled": True,
                    "encryption_enabled": True,
                    "geo_restrictions": ["same_country"],
                    "vary_headers": ["User-Agent", "Accept-Language"]
                }
            }
        }

        # 创建配置目录
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # 加载或创建配置文件
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = default_config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)

        # 初始化缓存策略
        for policy_id, policy_data in config["policies"].items():
            policy_data["cache_levels"] = [CacheLevel(level) for level in policy_data["cache_levels"]]
            self.cache_policies[policy_id] = CachePolicy(**policy_data)

        self.config = config

    async def _initialize_connections(self):
        """初始化Redis连接"""
        for region_name, region_config in self.config["regions"].items():
            try:
                region = CacheRegion(region_name)
                connection = redis.Redis(
                    host=region_config["host"],
                    port=region_config["port"],
                    db=region_config["db"],
                    max_connections=region_config["max_connections"],
                    decode_responses=False
                )

                # 测试连接
                await connection.ping()
                self.cache_connections[region] = connection

                # 初始化统计信息
                self.cache_stats[region] = {
                    "hits": 0,
                    "misses": 0,
                    "sets": 0,
                    "deletes": 0,
                    "size_bytes": 0,
                    "entry_count": 0,
                    "last_reset": datetime.now().isoformat()
                }

                logger.info(f"Connected to Redis for region: {region_name}")

            except Exception as e:
                logger.error(f"Failed to connect to Redis for region {region_name}: {e}")

    async def get_region_from_ip(self, ip_address: str) -> CacheRegion:
        """根据IP地址确定区域"""
        try:
            # 这里应该使用GeoIP数据库
            # 简化实现，实际应该使用MaxMind GeoIP或类似服务

            # 示例IP范围映射
            ip_ranges = {
                CacheRegion.ASIA_PACIFIC: ["1.0.0.0/8", "203.0.0.0/8", "202.0.0.0/8"],
                CacheRegion.EUROPE: ["81.0.0.0/8", "82.0.0.0/8", "83.0.0.0/8"],
                CacheRegion.AMERICAS: ["192.0.0.0/8", "172.0.0.0/8", "10.0.0.0/8"],
                CacheRegion.CHINA: ["58.0.0.0/8", "59.0.0.0/8", "60.0.0.0/8"]
            }

            # 简化的IP匹配逻辑
            for region, ranges in ip_ranges.items():
                for ip_range in ranges:
                    if self._ip_in_range(ip_address, ip_range):
                        return region

            # 默认返回美洲区域
            return CacheRegion.AMERICAS

        except Exception as e:
            logger.error(f"Failed to determine region for IP {ip_address}: {e}")
            return CacheRegion.AMERICAS

    def _ip_in_range(self, ip: str, ip_range: str) -> bool:
        """检查IP是否在指定范围内"""
        # 简化实现，实际应该使用proper IP range checking
        return False

    async def get(self, key: str, region: CacheRegion = None,
                  cache_level: CacheLevel = CacheLevel.L1_EDGE) -> Optional[Any]:
        """获取缓存值"""
        try:
            if region is None:
                # 尝试从最近的区域开始查找
                regions = [CacheRegion.AMERICAS, CacheRegion.EUROPE, CacheRegion.ASIA_PACIFIC]
            else:
                regions = [region]

            # 按照级别顺序查找
            levels = [CacheLevel.L1_EDGE, CacheLevel.L2_REGIONAL, CacheLevel.L3_GLOBAL]

            for target_region in regions:
                if target_region not in self.cache_connections:
                    continue

                connection = self.cache_connections[target_region]

                for level in levels:
                    if cache_level and level != cache_level:
                        continue

                    # 构造缓存键
                    cache_key = f"{level.value}:{key}"

                    try:
                        # 获取缓存数据
                        cached_data = await connection.get(cache_key)
                        if cached_data:
                            # 解析缓存条目
                            cache_entry = json.loads(cached_data)

                            # 检查是否过期
                            expires_at = datetime.fromisoformat(cache_entry["expires_at"])
                            if datetime.now() > expires_at:
                                # 过期，删除缓存
                                await connection.delete(cache_key)
                                continue

                            # 更新访问统计
                            await self._update_access_stats(target_region, cache_key)

                            # 返回值
                            logger.debug(f"Cache hit for key {key} in region {target_region}, level {level}")
                            return json.loads(cache_entry["value"])

                    except Exception as e:
                        logger.warning(f"Failed to get cache entry {cache_key}: {e}")
                        continue

            # 缓存未命中
            logger.debug(f"Cache miss for key {key}")
            return None

        except Exception as e:
            logger.error(f"Failed to get cache for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, policy_id: str,
                  region: CacheRegion = CacheRegion.AMERICAS,
                  user_ip: str = None, headers: Dict[str, str] = None) -> bool:
        """设置缓存值"""
        try:
            if policy_id not in self.cache_policies:
                logger.error(f"Unknown cache policy: {policy_id}")
                return False

            policy = self.cache_policies[policy_id]

            # 确定目标区域
            if user_ip:
                target_region = await self.get_region_from_ip(user_ip)
            else:
                target_region = region

            if target_region not in self.cache_connections:
                logger.warning(f"No cache connection for region: {target_region}")
                return False

            connection = self.cache_connections[target_region]

            # 检查地理位置限制
            if policy.geo_restrictions and not self._check_geo_restrictions(
                target_region, policy.geo_restrictions
            ):
                logger.debug(f"Geo restriction blocked cache for key {key}")
                return False

            # 为每个缓存级别设置值
            current_time = datetime.now()
            value_json = json.dumps(value, ensure_ascii=False)
            checksum = hashlib.md5(value_json.encode()).hexdigest()

            for cache_level in policy.cache_levels:
                # 计算过期时间
                ttl_seconds = policy.ttl[cache_level]
                expires_at = current_time + timedelta(seconds=ttl_seconds)

                # 创建缓存条目
                cache_entry = CacheEntry(
                    key=key,
                    value=value_json,
                    content_type=policy.content_type,
                    created_at=current_time,
                    expires_at=expires_at,
                    access_count=0,
                    last_accessed=current_time,
                    size_bytes=len(value_json.encode('utf-8')),
                    cache_level=cache_level,
                    region=target_region,
                    checksum=checksum
                )

                # 序列化缓存条目
                cache_data = json.dumps(asdict(cache_entry), default=str)

                # 压缩数据（如果启用）
                if policy.compression_enabled:
                    cache_data = await self._compress_data(cache_data)

                # 加密数据（如果启用）
                if policy.encryption_enabled:
                    cache_data = await self._encrypt_data(cache_data)

                # 存储到Redis
                cache_key = f"{cache_level.value}:{key}"
                await connection.setex(cache_key, ttl_seconds, cache_data)

                # 更新统计信息
                self.cache_stats[target_region]["sets"] += 1

            logger.debug(f"Cache set for key {key} in region {target_region}")
            return True

        except Exception as e:
            logger.error(f"Failed to set cache for key {key}: {e}")
            return False

    async def delete(self, key: str, region: CacheRegion = None) -> bool:
        """删除缓存值"""
        try:
            if region is None:
                regions = list(self.cache_connections.keys())
            else:
                regions = [region]

            levels = [CacheLevel.L1_EDGE, CacheLevel.L2_REGIONAL, CacheLevel.L3_GLOBAL]
            deleted = False

            for target_region in regions:
                if target_region not in self.cache_connections:
                    continue

                connection = self.cache_connections[target_region]

                for level in levels:
                    cache_key = f"{level.value}:{key}"
                    result = await connection.delete(cache_key)
                    if result:
                        deleted = True
                        self.cache_stats[target_region]["deletes"] += 1

            if deleted:
                logger.debug(f"Cache deleted for key {key}")
            else:
                logger.debug(f"Cache key {key} not found for deletion")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete cache for key {key}: {e}")
            return False

    async def invalidate_pattern(self, pattern: str, region: CacheRegion = None) -> int:
        """根据模式删除缓存"""
        try:
            if region is None:
                regions = list(self.cache_connections.keys())
            else:
                regions = [region]

            total_deleted = 0

            for target_region in regions:
                if target_region not in self.cache_connections:
                    continue

                connection = self.cache_connections[target_region]

                # 获取匹配的键
                keys = []
                for level in [CacheLevel.L1_EDGE, CacheLevel.L2_REGIONAL, CacheLevel.L3_GLOBAL]:
                    level_pattern = f"{level.value}:{pattern}"
                    level_keys = await connection.keys(level_pattern)
                    keys.extend(level_keys)

                # 删除匹配的键
                if keys:
                    deleted = await connection.delete(*keys)
                    total_deleted += deleted
                    self.cache_stats[target_region]["deletes"] += deleted

            logger.info(f"Invalidated {total_deleted} cache entries matching pattern: {pattern}")
            return total_deleted

        except Exception as e:
            logger.error(f"Failed to invalidate cache pattern {pattern}: {e}")
            return 0

    async def _update_access_stats(self, region: CacheRegion, cache_key: str):
        """更新访问统计"""
        try:
            if region in self.cache_connections:
                self.cache_stats[region]["hits"] += 1
                # 这里可以更新更详细的统计信息
        except Exception as e:
            logger.warning(f"Failed to update access stats: {e}")

    def _check_geo_restrictions(self, region: CacheRegion, restrictions: List[str]) -> bool:
        """检查地理位置限制"""
        if "same_country" in restrictions:
            # 实现同国家检查逻辑
            pass
        elif "same_region" in restrictions:
            # 实现同区域检查逻辑
            pass

        return True

    async def _compress_data(self, data: str) -> str:
        """压缩数据"""
        # 实现压缩逻辑
        return data

    async def _encrypt_data(self, data: str) -> str:
        """加密数据"""
        # 实现加密逻辑
        return data

    async def get_cache_stats(self, region: CacheRegion = None) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            if region:
                if region in self.cache_stats:
                    return self.cache_stats[region]
                else:
                    return {}
            else:
                return self.cache_stats
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}

    async def clear_region_cache(self, region: CacheRegion) -> bool:
        """清空指定区域的缓存"""
        try:
            if region not in self.cache_connections:
                return False

            connection = self.cache_connections[region]
            await connection.flushdb()

            # 重置统计信息
            self.cache_stats[region] = {
                "hits": 0,
                "misses": 0,
                "sets": 0,
                "deletes": 0,
                "size_bytes": 0,
                "entry_count": 0,
                "last_reset": datetime.now().isoformat()
            }

            logger.info(f"Cache cleared for region: {region}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear cache for region {region}: {e}")
            return False

    async def optimize_cache(self, region: CacheRegion = None) -> Dict[str, Any]:
        """优化缓存"""
        try:
            optimization_results = {
                "entries_removed": 0,
                "memory_freed": 0,
                "recommendations": []
            }

            regions = [region] if region else list(self.cache_connections.keys())

            for target_region in regions:
                if target_region not in self.cache_connections:
                    continue

                connection = self.cache_connections[target_region]

                # 获取所有缓存键
                all_keys = await connection.keys("*")

                # 分析缓存条目
                current_time = datetime.now()
                expired_keys = []
                low_priority_keys = []

                for key in all_keys:
                    try:
                        # 获取TTL
                        ttl = await connection.ttl(key)
                        if ttl == -2:  # 已过期但未删除
                            expired_keys.append(key)
                        elif ttl > 0 and ttl < 300:  # 即将过期（5分钟内）
                            low_priority_keys.append(key)

                    except Exception:
                        continue

                # 删除过期键
                if expired_keys:
                    deleted = await connection.delete(*expired_keys)
                    optimization_results["entries_removed"] += deleted

                # 生成优化建议
                hit_rate = self.cache_stats[target_region].get("hits", 0) / max(
                    self.cache_stats[target_region].get("hits", 1) +
                    self.cache_stats[target_region].get("misses", 1), 1
                )

                if hit_rate < 0.7:
                    optimization_results["recommendations"].append(
                        f"Low hit rate ({hit_rate:.2%}) in {target_region}. Consider adjusting TTL policies."
                    )

                if len(low_priority_keys) > 1000:
                    optimization_results["recommendations"].append(
                        f"High number of soon-to-expire entries in {target_region}. Consider prefetching."
                    )

            logger.info(f"Cache optimization completed: {optimization_results}")
            return optimization_results

        except Exception as e:
            logger.error(f"Failed to optimize cache: {e}")
            return {"entries_removed": 0, "memory_freed": 0, "recommendations": []}

    async def close_connections(self):
        """关闭所有连接"""
        for region, connection in self.cache_connections.items():
            try:
                await connection.close()
                logger.info(f"Closed Redis connection for region: {region}")
            except Exception as e:
                logger.error(f"Failed to close connection for region {region}: {e}")

# 全局缓存管理器实例
cache_manager = RegionCacheManager()

async def get_cache_manager() -> RegionCacheManager:
    """获取缓存管理器实例"""
    return cache_manager