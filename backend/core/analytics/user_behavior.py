"""
用户行为分析系统
User Behavior Analytics Module

提供企业级用户行为分析功能，包括：
- 用户访问模式分析
- 功能使用统计分析
- 错误率分析
- 用户留存分析
- 用户画像构建
- 行为异常检测
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import hashlib
import uuid
from pathlib import Path

from backend.config.settings import get_settings
from backend.core.cache.multi_level_cache import cache_manager

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class UserSession:
    """用户会话数据结构"""
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime]
    page_views: int
    api_calls: int
    errors: int
    duration: float  # 会话持续时间（秒）
    device_type: str
    browser: str
    ip_address: str
    pages_visited: List[str]
    actions: List[Dict[str, Any]]

@dataclass
class UserBehaviorMetrics:
    """用户行为指标数据结构"""
    avg_session_duration: float
    bounce_rate: float
    pages_per_session: float
    return_user_rate: float
    daily_active_users: int
    weekly_active_users: int
    monthly_active_users: int
    peak_usage_hours: List[int]
    most_used_features: List[Dict[str, Any]]
    user_segments: Dict[str, int]

@dataclass
class UserFunnelMetrics:
    """用户转化漏斗指标"""
    funnel_name: str
    total_users: int
    stage_metrics: Dict[str, Dict[str, Any]]  # stage_name -> {users: int, conversion_rate: float}
    overall_conversion_rate: float
    drop_off_points: List[Dict[str, Any]]

@dataclass
class UserPersona:
    """用户画像数据结构"""
    persona_id: str
    user_count: int
    characteristics: Dict[str, Any]
    behavior_patterns: List[str]
    preferred_features: List[str]
    engagement_level: str  # high, medium, low
    value_score: float

@dataclass
class BehaviorAnomaly:
    """行为异常数据结构"""
    anomaly_id: str
    user_id: str
    anomaly_type: str
    description: str
    severity: str  # low, medium, high, critical
    detected_at: datetime
    metrics: Dict[str, Any]
    recommended_action: str


class UserBehaviorAnalytics:
    """用户行为分析器"""

    def __init__(self):
        self.cache_key_prefix = "user_behavior"
        self.data_dir = Path("data/analytics/user_behavior")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 数据存储路径
        self.sessions_path = self.data_dir / "user_sessions.json"
        self.behavior_metrics_path = self.data_dir / "behavior_metrics.json"
        self.funnels_path = self.data_dir / "user_funnels.json"
        self.personas_path = self.data_dir / "user_personas.json"
        self.anomalies_path = self.data_dir / "behavior_anomalies.json"

        # 行为跟踪配置
        self.tracking_enabled = True
        self.anonymization_enabled = True
        self.retention_days = 90

    async def track_user_session(
        self,
        user_id: str,
        session_data: Dict[str, Any]
    ) -> str:
        """
        跟踪用户会话

        Args:
            user_id: 用户ID
            session_data: 会话数据

        Returns:
            str: 会话ID
        """
        try:
            if not self.tracking_enabled:
                return ""

            # 匿名化处理
            if self.anonymization_enabled:
                user_id = self._anonymize_user_id(user_id)

            session_id = str(uuid.uuid4())

            session = UserSession(
                session_id=session_id,
                user_id=user_id,
                start_time=datetime.fromisoformat(session_data.get("start_time", datetime.now().isoformat())),
                end_time=None,
                page_views=session_data.get("page_views", 0),
                api_calls=session_data.get("api_calls", 0),
                errors=session_data.get("errors", 0),
                duration=session_data.get("duration", 0),
                device_type=session_data.get("device_type", "unknown"),
                browser=session_data.get("browser", "unknown"),
                ip_address=self._anonymize_ip(session_data.get("ip_address", "")),
                pages_visited=session_data.get("pages_visited", []),
                actions=session_data.get("actions", [])
            )

            # 保存会话数据
            await self._save_session(session)

            # 更新实时指标
            await self._update_realtime_metrics(session)

            logger.info(f"Tracked user session: {session_id} for user: {user_id}")
            return session_id

        except Exception as e:
            logger.error(f"Error tracking user session: {e}")
            return ""

    async def calculate_behavior_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> UserBehaviorMetrics:
        """
        计算用户行为指标

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            UserBehaviorMetrics: 用户行为指标
        """
        try:
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()

            cache_key = f"{self.cache_key_prefix}:behavior_metrics:{start_date.date()}:{end_date.date()}"

            # 尝试从缓存获取
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                return UserBehaviorMetrics(**cached_result)

            logger.info(f"Calculating user behavior metrics from {start_date.date()} to {end_date.date()}")

            # 获取会话数据
            sessions = await self._load_sessions(start_date, end_date)

            # 计算各项行为指标
            avg_session_duration = self._calculate_avg_session_duration(sessions)
            bounce_rate = self._calculate_bounce_rate(sessions)
            pages_per_session = self._calculate_pages_per_session(sessions)
            return_user_rate = self._calculate_return_user_rate(sessions)
            daily_active_users = self._calculate_active_users(sessions, "daily")
            weekly_active_users = self._calculate_active_users(sessions, "weekly")
            monthly_active_users = self._calculate_active_users(sessions, "monthly")
            peak_usage_hours = self._calculate_peak_usage_hours(sessions)
            most_used_features = self._calculate_most_used_features(sessions)
            user_segments = self._calculate_user_segments(sessions)

            metrics = UserBehaviorMetrics(
                avg_session_duration=avg_session_duration,
                bounce_rate=bounce_rate,
                pages_per_session=pages_per_session,
                return_user_rate=return_user_rate,
                daily_active_users=daily_active_users,
                weekly_active_users=weekly_active_users,
                monthly_active_users=monthly_active_users,
                peak_usage_hours=peak_usage_hours,
                most_used_features=most_used_features,
                user_segments=user_segments
            )

            # 缓存结果（缓存30分钟）
            await cache_manager.set(
                cache_key,
                asdict(metrics),
                expire_seconds=1800
            )

            # 保存到文件
            await self._save_behavior_metrics(metrics)

            logger.info(f"Behavior metrics calculated: DAU={daily_active_users}, Bounce={bounce_rate:.2%}")
            return metrics

        except Exception as e:
            logger.error(f"Error calculating behavior metrics: {e}")
            return UserBehaviorMetrics(
                avg_session_duration=0.0,
                bounce_rate=0.0,
                pages_per_session=0.0,
                return_user_rate=0.0,
                daily_active_users=0,
                weekly_active_users=0,
                monthly_active_users=0,
                peak_usage_hours=[],
                most_used_features=[],
                user_segments={}
            )

    async def analyze_user_funnel(
        self,
        funnel_name: str,
        funnel_stages: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> UserFunnelMetrics:
        """
        分析用户转化漏斗

        Args:
            funnel_name: 漏斗名称
            funnel_stages: 漏斗阶段列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            UserFunnelMetrics: 漏斗分析结果
        """
        try:
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()

            cache_key = f"{self.cache_key_prefix}:funnel:{funnel_name}:{start_date.date()}:{end_date.date()}"

            # 尝试从缓存获取
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                return UserFunnelMetrics(**cached_result)

            logger.info(f"Analyzing user funnel: {funnel_name}")

            # 获取用户行为数据
            user_actions = await self._load_user_actions(start_date, end_date)

            # 分析漏斗
            total_users = len(set(action["user_id"] for action in user_actions))
            stage_metrics = {}
            previous_stage_users = set()

            for i, stage in enumerate(funnel_stages):
                stage_users = set()

                # 找到完成此阶段的用户
                for action in user_actions:
                    if self._is_stage_completion(action, stage):
                        stage_users.add(action["user_id"])

                stage_users_count = len(stage_users)

                # 计算转化率
                if i == 0:
                    conversion_rate = stage_users_count / total_users if total_users > 0 else 0
                else:
                    conversion_rate = stage_users_count / len(previous_stage_users) if previous_stage_users else 0

                stage_metrics[stage] = {
                    "users": stage_users_count,
                    "conversion_rate": conversion_rate,
                    "drop_off_rate": 1 - conversion_rate
                }

                previous_stage_users = stage_users

            # 计算总体转化率
            final_stage_users = len(stage_metrics[funnel_stages[-1]]["users"]) if funnel_stages else 0
            overall_conversion_rate = final_stage_users / total_users if total_users > 0 else 0

            # 识别流失点
            drop_off_points = self._identify_drop_off_points(stage_metrics)

            funnel_metrics = UserFunnelMetrics(
                funnel_name=funnel_name,
                total_users=total_users,
                stage_metrics=stage_metrics,
                overall_conversion_rate=overall_conversion_rate,
                drop_off_points=drop_off_points
            )

            # 缓存结果（缓存1小时）
            await cache_manager.set(
                cache_key,
                asdict(funnel_metrics),
                expire_seconds=3600
            )

            logger.info(f"Funnel analysis completed: {funnel_name}, Conversion: {overall_conversion_rate:.2%}")
            return funnel_metrics

        except Exception as e:
            logger.error(f"Error analyzing user funnel: {e}")
            return UserFunnelMetrics(
                funnel_name=funnel_name,
                total_users=0,
                stage_metrics={},
                overall_conversion_rate=0.0,
                drop_off_points=[]
            )

    async def generate_user_personas(self) -> List[UserPersona]:
        """
        生成用户画像

        Returns:
            List[UserPersona]: 用户画像列表
        """
        try:
            cache_key = f"{self.cache_key_prefix}:personas"

            # 尝试从缓存获取
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                return [UserPersona(**persona) for persona in cached_result]

            logger.info("Generating user personas")

            # 获取用户行为数据
            sessions = await self._load_sessions(
                datetime.now() - timedelta(days=90),
                datetime.now()
            )

            # 聚类分析用户行为
            user_groups = self._cluster_user_behavior(sessions)

            # 生成画像
            personas = []
            for group_name, group_data in user_groups.items():
                persona = await self._create_persona(group_name, group_data)
                personas.append(persona)

            # 缓存结果（缓存24小时）
            await cache_manager.set(
                cache_key,
                [asdict(persona) for persona in personas],
                expire_seconds=86400
            )

            # 保存到文件
            await self._save_user_personas(personas)

            logger.info(f"Generated {len(personas)} user personas")
            return personas

        except Exception as e:
            logger.error(f"Error generating user personas: {e}")
            return []

    async def detect_behavior_anomalies(self) -> List[BehaviorAnomaly]:
        """
        检测行为异常

        Returns:
            List[BehaviorAnomaly]: 异常列表
        """
        try:
            cache_key = f"{self.cache_key_prefix}:anomalies"

            # 尝试从缓存获取
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                return [BehaviorAnomaly(**anomaly) for anomaly in cached_result]

            logger.info("Detecting behavior anomalies")

            # 获取最近24小时的数据
            recent_sessions = await self._load_sessions(
                datetime.now() - timedelta(hours=24),
                datetime.now()
            )

            anomalies = []

            # 检测各类异常
            anomalies.extend(await self._detect_usage_spike_anomalies(recent_sessions))
            anomalies.extend(await self._detect_error_rate_anomalies(recent_sessions))
            anomalies.extend(await self._detect_session_duration_anomalies(recent_sessions))
            anomalies.extend(await self._detect_unusual_access_patterns(recent_sessions))

            # 缓存结果（缓存1小时）
            await cache_manager.set(
                cache_key,
                [asdict(anomaly) for anomaly in anomalies],
                expire_seconds=3600
            )

            # 保存到文件
            await self._save_behavior_anomalies(anomalies)

            logger.info(f"Detected {len(anomalies)} behavior anomalies")
            return anomalies

        except Exception as e:
            logger.error(f"Error detecting behavior anomalies: {e}")
            return []

    # 私有辅助方法

    def _anonymize_user_id(self, user_id: str) -> str:
        """匿名化用户ID"""
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]

    def _anonymize_ip(self, ip_address: str) -> str:
        """匿名化IP地址"""
        if not ip_address:
            return ""

        # 简单的IP匿名化（保留前3段）
        parts = ip_address.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
        return ip_address

    async def _save_session(self, session: UserSession):
        """保存会话数据"""
        try:
            sessions_file = self.sessions_path
            sessions_data = []

            # 读取现有数据
            if sessions_file.exists():
                with open(sessions_file, 'r') as f:
                    sessions_data = json.load(f)

            # 添加新会话
            session_dict = asdict(session)
            session_dict["start_time"] = session.start_time.isoformat()
            if session.end_time:
                session_dict["end_time"] = session.end_time.isoformat()

            sessions_data.append(session_dict)

            # 清理过期数据
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            sessions_data = [
                s for s in sessions_data
                if datetime.fromisoformat(s["start_time"]) > cutoff_date
            ]

            # 保存数据
            with open(sessions_file, 'w') as f:
                json.dump(sessions_data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving session: {e}")

    async def _load_sessions(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[UserSession]:
        """加载会话数据"""
        try:
            if not self.sessions_path.exists():
                return []

            with open(self.sessions_path, 'r') as f:
                sessions_data = json.load(f)

            sessions = []
            for session_dict in sessions_data:
                session_time = datetime.fromisoformat(session_dict["start_time"])
                if start_date <= session_time <= end_date:
                    session_dict["start_time"] = datetime.fromisoformat(session_dict["start_time"])
                    if session_dict.get("end_time"):
                        session_dict["end_time"] = datetime.fromisoformat(session_dict["end_time"])
                    sessions.append(UserSession(**session_dict))

            return sessions

        except Exception as e:
            logger.error(f"Error loading sessions: {e}")
            return []

    async def _update_realtime_metrics(self, session: UserSession):
        """更新实时指标"""
        # TODO: 实现实时指标更新逻辑
        pass

    def _calculate_avg_session_duration(self, sessions: List[UserSession]) -> float:
        """计算平均会话持续时间"""
        if not sessions:
            return 0.0
        total_duration = sum(s.duration for s in sessions)
        return total_duration / len(sessions)

    def _calculate_bounce_rate(self, sessions: List[UserSession]) -> float:
        """计算跳出率（单页访问会话比例）"""
        if not sessions:
            return 0.0
        bounce_sessions = sum(1 for s in sessions if s.page_views <= 1 and s.duration < 30)
        return bounce_sessions / len(sessions)

    def _calculate_pages_per_session(self, sessions: List[UserSession]) -> float:
        """计算每会话平均页面数"""
        if not sessions:
            return 0.0
        total_pages = sum(s.page_views for s in sessions)
        return total_pages / len(sessions)

    def _calculate_return_user_rate(self, sessions: List[UserSession]) -> float:
        """计算回访用户率"""
        if not sessions:
            return 0.0
        user_sessions = defaultdict(list)
        for session in sessions:
            user_sessions[session.user_id].append(session)

        return_users = sum(1 for user_id, user_sessions_list in user_sessions.items() if len(user_sessions_list) > 1)
        return return_users / len(user_sessions)

    def _calculate_active_users(self, sessions: List[UserSession], period: str) -> int:
        """计算活跃用户数"""
        if not sessions:
            return 0

        if period == "daily":
            today = datetime.now().date()
            today_sessions = [s for s in sessions if s.start_time.date() == today]
            return len(set(s.user_id for s in today_sessions))
        elif period == "weekly":
            week_ago = datetime.now() - timedelta(days=7)
            week_sessions = [s for s in sessions if s.start_time >= week_ago]
            return len(set(s.user_id for s in week_sessions))
        elif period == "monthly":
            month_ago = datetime.now() - timedelta(days=30)
            month_sessions = [s for s in sessions if s.start_time >= month_ago]
            return len(set(s.user_id for s in month_sessions))

        return 0

    def _calculate_peak_usage_hours(self, sessions: List[UserSession]) -> List[int]:
        """计算高峰使用时段"""
        if not sessions:
            return []

        hour_counts = defaultdict(int)
        for session in sessions:
            hour = session.start_time.hour
            hour_counts[hour] += 1

        # 获取使用量最高的3个小时
        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
        return [hour for hour, count in sorted_hours[:3]]

    def _calculate_most_used_features(self, sessions: List[UserSession]) -> List[Dict[str, Any]]:
        """计算最常用功能"""
        feature_usage = defaultdict(int)

        for session in sessions:
            for action in session.actions:
                feature = action.get("feature", "unknown")
                feature_usage[feature] += 1

        # 排序并返回前10个功能
        sorted_features = sorted(feature_usage.items(), key=lambda x: x[1], reverse=True)
        total_usage = sum(feature_usage.values())

        return [
            {
                "feature": feature,
                "usage_count": count,
                "usage_percentage": count / total_usage if total_usage > 0 else 0
            }
            for feature, count in sorted_features[:10]
        ]

    def _calculate_user_segments(self, sessions: List[UserSession]) -> Dict[str, int]:
        """计算用户细分"""
        segments = defaultdict(int)

        for session in sessions:
            # 基于使用量进行细分
            if session.api_calls > 100:
                segments["power_users"] += 1
            elif session.api_calls > 20:
                segments["regular_users"] += 1
            else:
                segments["casual_users"] += 1

            # 基于设备类型细分
            segments[f"device_{session.device_type}"] += 1

        return dict(segments)

    async def _load_user_actions(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """加载用户行为数据"""
        # TODO: 从数据库加载用户行为数据
        # 这里返回模拟数据
        return [
            {
                "user_id": f"user_{i % 50}",
                "action": "page_view",
                "feature": "chat",
                "timestamp": (start_date + timedelta(hours=i)).isoformat(),
                "properties": {}
            }
            for i in range(1000)
        ]

    def _is_stage_completion(self, action: Dict[str, Any], stage: str) -> bool:
        """判断是否完成某个漏斗阶段"""
        # 简化的阶段完成判断逻辑
        return action.get("feature") == stage

    def _identify_drop_off_points(self, stage_metrics: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """识别流失点"""
        drop_off_points = []

        for stage, metrics in stage_metrics.items():
            if metrics["drop_off_rate"] > 0.3:  # 流失率超过30%
                drop_off_points.append({
                    "stage": stage,
                    "drop_off_rate": metrics["drop_off_rate"],
                    "users_lost": metrics["drop_off_rate"] * 100,  # 假设100个用户
                    "priority": "high" if metrics["drop_off_rate"] > 0.5 else "medium"
                })

        return sorted(drop_off_points, key=lambda x: x["drop_off_rate"], reverse=True)

    def _cluster_user_behavior(self, sessions: List[UserSession]) -> Dict[str, List[UserSession]]:
        """聚类用户行为"""
        # 简化的聚类逻辑
        power_users = []
        regular_users = []
        casual_users = []

        for session in sessions:
            if session.api_calls > 100:
                power_users.append(session)
            elif session.api_calls > 20:
                regular_users.append(session)
            else:
                casual_users.append(session)

        return {
            "power_users": power_users,
            "regular_users": regular_users,
            "casual_users": casual_users
        }

    async def _create_persona(self, group_name: str, group_data: List[UserSession]) -> UserPersona:
        """创建用户画像"""
        if not group_data:
            return UserPersona(
                persona_id=group_name,
                user_count=0,
                characteristics={},
                behavior_patterns=[],
                preferred_features=[],
                engagement_level="low",
                value_score=0.0
            )

        # 分析特征
        avg_session_duration = sum(s.duration for s in group_data) / len(group_data)
        avg_api_calls = sum(s.api_calls for s in group_data) / len(group_data)

        # 确定参与度级别
        if avg_api_calls > 100:
            engagement_level = "high"
            value_score = 0.9
        elif avg_api_calls > 20:
            engagement_level = "medium"
            value_score = 0.6
        else:
            engagement_level = "low"
            value_score = 0.3

        # 提取偏好功能
        feature_counts = defaultdict(int)
        for session in group_data:
            for action in session.actions:
                feature = action.get("feature", "unknown")
                feature_counts[feature] += 1

        preferred_features = [
            feature for feature, count in
            sorted(feature_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        return UserPersona(
            persona_id=group_name,
            user_count=len(set(s.user_id for s in group_data)),
            characteristics={
                "avg_session_duration": avg_session_duration,
                "avg_api_calls": avg_api_calls,
                "primary_device": Counter(s.device_type for s in group_data).most_common(1)[0][0]
            },
            behavior_patterns=[
                f"平均会话时长: {avg_session_duration:.1f}秒",
                f"平均API调用: {avg_api_calls:.1f}次"
            ],
            preferred_features=preferred_features,
            engagement_level=engagement_level,
            value_score=value_score
        )

    async def _detect_usage_spike_anomalies(self, sessions: List[UserSession]) -> List[BehaviorAnomaly]:
        """检测使用量激增异常"""
        anomalies = []

        # 按小时聚合使用量
        hourly_usage = defaultdict(int)
        for session in sessions:
            hour = session.start_time.replace(minute=0, second=0, microsecond=0)
            hourly_usage[hour] += session.api_calls

        if len(hourly_usage) < 2:
            return anomalies

        # 计算平均值和标准差
        usage_values = list(hourly_usage.values())
        avg_usage = sum(usage_values) / len(usage_values)
        std_usage = (sum((x - avg_usage) ** 2 for x in usage_values) / len(usage_values)) ** 0.5

        # 检测异常（超过2个标准差）
        threshold = avg_usage + 2 * std_usage
        for hour, usage in hourly_usage.items():
            if usage > threshold:
                anomalies.append(BehaviorAnomaly(
                    anomaly_id=str(uuid.uuid4()),
                    user_id="system",
                    anomaly_type="usage_spike",
                    description=f"使用量激增：{hour} 时使用量 {usage} 超过正常水平",
                    severity="high" if usage > avg_usage + 3 * std_usage else "medium",
                    detected_at=datetime.now(),
                    metrics={"hour": hour.isoformat(), "usage": usage, "threshold": threshold},
                    recommended_action="检查系统负载和用户活动"
                ))

        return anomalies

    async def _detect_error_rate_anomalies(self, sessions: List[UserSession]) -> List[BehaviorAnomaly]:
        """检测错误率异常"""
        anomalies = []

        # 按用户聚合错误率
        user_errors = defaultdict(lambda: {"total": 0, "errors": 0})
        for session in sessions:
            user_errors[session.user_id]["total"] += session.api_calls
            user_errors[session.user_id]["errors"] += session.errors

        # 检测高错误率用户
        for user_id, stats in user_errors.items():
            if stats["total"] > 10:  # 至少10次调用
                error_rate = stats["errors"] / stats["total"]
                if error_rate > 0.1:  # 错误率超过10%
                    anomalies.append(BehaviorAnomaly(
                        anomaly_id=str(uuid.uuid4()),
                        user_id=user_id,
                        anomaly_type="high_error_rate",
                        description=f"用户 {user_id} 错误率过高: {error_rate:.2%}",
                        severity="high" if error_rate > 0.2 else "medium",
                        detected_at=datetime.now(),
                        metrics={"error_rate": error_rate, "total_calls": stats["total"], "errors": stats["errors"]},
                        recommended_action="联系用户并提供支持"
                    ))

        return anomalies

    async def _detect_session_duration_anomalies(self, sessions: List[UserSession]) -> List[BehaviorAnomaly]:
        """检测会话时长异常"""
        anomalies = []

        if len(sessions) < 10:
            return anomalies

        # 计算平均值和标准差
        durations = [s.duration for s in sessions]
        avg_duration = sum(durations) / len(durations)
        std_duration = (sum((x - avg_duration) ** 2 for x in durations) / len(durations)) ** 0.5

        # 检测异常长的会话（可能是机器人）
        threshold = avg_duration + 3 * std_duration
        for session in sessions:
            if session.duration > threshold and session.duration > 3600:  # 超过1小时
                anomalies.append(BehaviorAnomaly(
                    anomaly_id=str(uuid.uuid4()),
                    user_id=session.user_id,
                    anomaly_type="unusual_session_duration",
                    description=f"异常长的会话：{session.duration:.1f}秒",
                    severity="medium",
                    detected_at=datetime.now(),
                    metrics={"duration": session.duration, "threshold": threshold},
                    recommended_action="检查是否为机器人或异常使用"
                ))

        return anomalies

    async def _detect_unusual_access_patterns(self, sessions: List[UserSession]) -> List[BehaviorAnomaly]:
        """检测异常访问模式"""
        anomalies = []

        # 按IP聚合访问次数
        ip_access = defaultdict(list)
        for session in sessions:
            ip_access[session.ip_address].append(session)

        # 检测来自同一IP的大量会话
        for ip, ip_sessions in ip_access.items():
            if len(ip_sessions) > 50:  # 超过50个会话
                unique_users = len(set(s.user_id for s in ip_sessions))
                if unique_users < 5:  # 但用户数很少
                    anomalies.append(BehaviorAnomaly(
                        anomaly_id=str(uuid.uuid4()),
                        user_id="multiple_users",
                        anomaly_type="suspicious_access_pattern",
                        description=f"IP {ip} 有大量会话但用户数很少",
                        severity="high",
                        detected_at=datetime.now(),
                        metrics={"ip": ip, "sessions": len(ip_sessions), "unique_users": unique_users},
                        recommended_action="检查是否存在滥用行为"
                    ))

        return anomalies

    async def _save_behavior_metrics(self, metrics: UserBehaviorMetrics):
        """保存行为指标到文件"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "metrics": asdict(metrics)
            }
            with open(self.behavior_metrics_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving behavior metrics: {e}")

    async def _save_user_personas(self, personas: List[UserPersona]):
        """保存用户画像到文件"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "personas": [asdict(persona) for persona in personas]
            }
            with open(self.personas_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving user personas: {e}")

    async def _save_behavior_anomalies(self, anomalies: List[BehaviorAnomaly]):
        """保存行为异常到文件"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "anomalies": [asdict(anomaly) for anomaly in anomalies]
            }
            with open(self.anomalies_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving behavior anomalies: {e}")


# 全局实例
user_behavior_analytics = UserBehaviorAnalytics()