"""
智能API性能分析器
基于机器学习和统计分析的智能性能分析系统
"""

import asyncio
import time
import json
import logging
import statistics
import math
from typing import Any, Dict, List, Optional, Tuple, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class PerformanceIssueType(Enum):
    """性能问题类型"""
    SLOW_RESPONSE = "slow_response"
    HIGH_ERROR_RATE = "high_error_rate"
    MEMORY_LEAK = "memory_leak"
    CPU_SPIKE = "cpu_spike"
    DATABASE_BOTTLENECK = "database_bottleneck"
    CACHE_EFFICIENCY = "cache_efficiency"
    CONCURRENT_OVERLOAD = "concurrent_overload"
    NETWORK_LATENCY = "network_latency"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


class AlertSeverity(Enum):
    """告警严重程度"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class PerformanceIssue:
    """性能问题"""
    issue_id: str
    type: PerformanceIssueType
    severity: AlertSeverity
    title: str
    description: str
    affected_endpoints: List[str]
    metrics: Dict[str, float]
    detected_at: float
    confidence: float = 0.0
    suggested_actions: List[str] = None
    related_patterns: List[str] = None

    def __post_init__(self):
        if self.suggested_actions is None:
            self.suggested_actions = []
        if self.related_patterns is None:
            self.related_patterns = []

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class PerformancePattern:
    """性能模式"""
    pattern_id: str
    name: str
    description: str
    pattern_type: str
    characteristics: Dict[str, Any]
    confidence: float = 0.0
    frequency: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0
    affected_endpoints: Set[str] = None

    def __post_init__(self):
        if self.affected_endpoints is None:
            self.affected_endpoints = set()


class MLPerformanceAnalyzer:
    """机器学习性能分析器"""

    def __init__(self):
        self.anomaly_detector = IsolationForest(
            contamination=0.1,
            random_state=42
        )
        self.pattern_clustering = KMeans(n_clusters=5, random_state=42)
        self.scaler = StandardScaler()

        self.feature_columns = [
            'response_time',
            'response_size',
            'concurrent_requests',
            'error_rate',
            'cache_hit_rate',
            'database_query_time',
            'cpu_usage',
            'memory_usage'
        ]

        self.is_trained = False
        self.training_data: List[Dict] = []
        self.min_training_samples = 100

    def extract_features(self, metrics: List[Dict]) -> np.ndarray:
        """提取特征向量"""
        features = []
        for metric in metrics:
            feature_vector = [
                metric.get('response_time', 0),
                metric.get('response_size', 0),
                metric.get('concurrent_requests', 0),
                metric.get('error_rate', 0),
                metric.get('cache_hit_rate', 0),
                metric.get('database_query_time', 0),
                metric.get('cpu_usage', 0),
                metric.get('memory_usage', 0)
            ]
            features.append(feature_vector)

        return np.array(features)

    def train_models(self, training_data: List[Dict]):
        """训练机器学习模型"""
        if len(training_data) < self.min_training_samples:
            logger.warning(f"Insufficient training data: {len(training_data)} < {self.min_training_samples}")
            return False

        try:
            # 提取特征
            features = self.extract_features(training_data)

            # 标准化特征
            scaled_features = self.scaler.fit_transform(features)

            # 训练异常检测模型
            self.anomaly_detector.fit(scaled_features)

            # 训练聚类模型
            self.pattern_clustering.fit(scaled_features)

            self.is_trained = True
            self.training_data = training_data

            logger.info(f"ML models trained with {len(training_data)} samples")
            return True

        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return False

    def detect_anomalies(self, metrics: List[Dict]) -> List[bool]:
        """检测异常"""
        if not self.is_trained:
            return [False] * len(metrics)

        try:
            features = self.extract_features(metrics)
            scaled_features = self.scaler.transform(features)
            anomalies = self.anomaly_detector.predict(scaled_features)
            return anomalies == -1  # -1 表示异常

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return [False] * len(metrics)

    def cluster_patterns(self, metrics: List[Dict]) -> np.ndarray:
        """聚类性能模式"""
        if not self.is_trained:
            return np.zeros(len(metrics))

        try:
            features = self.extract_features(metrics)
            scaled_features = self.scaler.transform(features)
            return self.pattern_clustering.predict(scaled_features)

        except Exception as e:
            logger.error(f"Pattern clustering failed: {e}")
            return np.zeros(len(metrics))


class StatisticalAnalyzer:
    """统计分析器"""

    @staticmethod
    def calculate_trend(values: List[float], window_size: int = 10) -> str:
        """计算趋势"""
        if len(values) < window_size:
            return "insufficient_data"

        # 使用线性回归计算趋势
        recent_values = values[-window_size:]
        x = list(range(len(recent_values)))

        # 简单线性回归
        n = len(recent_values)
        sum_x = sum(x)
        sum_y = sum(recent_values)
        sum_xy = sum(x[i] * recent_values[i] for i in range(n))
        sum_x2 = sum(x[i]**2 for i in range(n))

        if n * sum_x2 - sum_x**2 == 0:
            return "stable"

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)

        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"

    @staticmethod
    def detect_outliers(values: List[float], threshold: float = 2.0) -> List[int]:
        """检测异常值"""
        if len(values) < 3:
            return []

        mean = statistics.mean(values)
        std = statistics.stdev(values)

        outliers = []
        for i, value in enumerate(values):
            z_score = abs((value - mean) / std) if std > 0 else 0
            if z_score > threshold:
                outliers.append(i)

        return outliers

    @staticmethod
    def calculate_percentiles(values: List[float]) -> Dict[str, float]:
        """计算百分位数"""
        if not values:
            return {}

        sorted_values = sorted(values)
        n = len(sorted_values)

        return {
            'p50': sorted_values[int(n * 0.5)],
            'p75': sorted_values[int(n * 0.75)],
            'p90': sorted_values[int(n * 0.9)],
            'p95': sorted_values[int(n * 0.95)],
            'p99': sorted_values[int(n * 0.99)],
            'min': sorted_values[0],
            'max': sorted_values[-1]
        }


class IntelligentPerformanceAnalyzer:
    """智能性能分析器"""

    def __init__(self):
        self.ml_analyzer = MLPerformanceAnalyzer()
        self.statistical_analyzer = StatisticalAnalyzer()

        # 数据存储
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.issues_history: List[PerformanceIssue] = []
        self.patterns: Dict[str, PerformancePattern] = {}

        # 分析配置
        self.analysis_window = 100  # 分析窗口大小
        self.anomaly_threshold = 0.1  # 异常阈值
        self.trend_window = 20  # 趋势分析窗口
        self.issue_correlation_threshold = 0.7  # 问题关联阈值

        # 告警阈值
        self.thresholds = {
            'response_time_p95': 1.0,  # 95分位数超过1秒
            'error_rate': 0.05,      # 错误率超过5%
            'memory_usage': 0.85,     # 内存使用率超过85%
            'cpu_usage': 0.80,       # CPU使用率超过80%
            'cache_hit_rate': 0.5,    # 缓存命中���低于50%
            'concurrent_requests': 100  # 并发请求数超过100
        }

        self._analysis_task: Optional[asyncio.Task] = None

    async def start_analysis(self):
        """启动性能分析"""
        if self._analysis_task is not None:
            return

        self._analysis_task = asyncio.create_task(self._analysis_loop())
        logger.info("Performance analyzer started")

    async def stop_analysis(self):
        """停止性能分析"""
        if self._analysis_task:
            self._analysis_task.cancel()
            try:
                await self._analysis_task
            except asyncio.CancelledError:
                pass

        logger.info("Performance analyzer stopped")

    async def add_metrics(self, endpoint: str, metrics: Dict):
        """添加性能指标"""
        timestamp = time.time()
        metrics['timestamp'] = timestamp

        self.performance_history[endpoint].append(metrics)

        # 定期重新训练模型
        total_samples = sum(len(history) for history in self.performance_history.values())
        if total_samples % 100 == 0 and total_samples >= self.ml_analyzer.min_training_samples:
            await self._retrain_models()

    async def analyze_performance(self, endpoint: str = None) -> Dict:
        """分析性能"""
        if endpoint:
            return await self._analyze_endpoint(endpoint)
        else:
            return await self._analyze_all_endpoints()

    async def _analyze_endpoint(self, endpoint: str) -> Dict:
        """分析单个端点"""
        history = list(self.performance_history[endpoint])
        if not history:
            return {"endpoint": endpoint, "status": "no_data"}

        # 提取关键指标
        response_times = [m.get('response_time', 0) for m in history]
        error_rates = [m.get('error_rate', 0) for m in history]
        cache_hit_rates = [m.get('cache_hit_rate', 1) for m in history]

        analysis = {
            "endpoint": endpoint,
            "total_requests": len(history),
            "analysis_timestamp": time.time()
        }

        # 统计分析
        if response_times:
            analysis["response_time"] = self.statistical_analyzer.calculate_percentiles(response_times)
            analysis["response_time_trend"] = self.statistical_analyzer.calculate_trend(
                response_times, self.trend_window
            )

        if error_rates:
            analysis["error_rate"] = {
                "current": error_rates[-1],
                "average": statistics.mean(error_rates),
                "max": max(error_rates)
            }

        if cache_hit_rates:
            analysis["cache_hit_rate"] = {
                "current": cache_hit_rates[-1],
                "average": statistics.mean(cache_hit_rates),
                "min": min(cache_hit_rates)
            }

        # 异常检测
        if len(history) >= self.ml_analyzer.min_training_samples and self.ml_analyzer.is_trained:
            anomalies = self.ml_analyzer.detect_anomalies(history)
            analysis["anomalies"] = {
                "count": sum(anomalies),
                "recent_anomalies": [
                    i for i, is_anomaly in enumerate(anomalies)
                    if is_anomaly and i >= len(anomalies) - 10
                ]
            }

        return analysis

    async def _analyze_all_endpoints(self) -> Dict:
        """分析所有端点"""
        all_analysis = {
            "timestamp": time.time(),
            "endpoints": {},
            "global_issues": [],
            "system_health": {},
            "recommendations": []
        }

        # 分析每个端点
        for endpoint in list(self.performance_history.keys()):
            analysis = await self._analyze_endpoint(endpoint)
            all_analysis["endpoints"][endpoint] = analysis

            # 检测端点级别的问题
            issues = await self._detect_endpoint_issues(endpoint, analysis)
            all_analysis["global_issues"].extend(issues)

        # 系统级分析
        all_analysis["system_health"] = await self._analyze_system_health()

        # 生成建议
        all_analysis["recommendations"] = await self._generate_recommendations(all_analysis)

        return all_analysis

    async def _detect_endpoint_issues(self, endpoint: str, analysis: Dict) -> List[PerformanceIssue]:
        """检测端点问题"""
        issues = []

        try:
            # 响应时间问题
            if "response_time" in analysis:
                p95 = analysis["response_time"].get("p95", 0)
                if p95 > self.thresholds["response_time_p95"]:
                    issues.append(PerformanceIssue(
                        issue_id=f"slow_response_{endpoint}_{int(time.time())}",
                        type=PerformanceIssueType.SLOW_RESPONSE,
                        severity=AlertSeverity.HIGH if p95 > 2.0 else AlertSeverity.MEDIUM,
                        title=f"Slow Response Time",
                        description=f"Endpoint {endpoint} has slow P95 response time: {p95:.3f}s",
                        affected_endpoints=[endpoint],
                        metrics={"p95_response_time": p95},
                        detected_at=time.time(),
                        suggested_actions=[
                            "Optimize database queries",
                            "Add or improve caching",
                            "Check for blocking operations",
                            "Consider code optimization"
                        ]
                    ))

            # 错误率问题
            if "error_rate" in analysis:
                avg_error_rate = analysis["error_rate"].get("average", 0)
                if avg_error_rate > self.thresholds["error_rate"]:
                    issues.append(PerformanceIssue(
                        issue_id=f"high_error_rate_{endpoint}_{int(time.time())}",
                        type=PerformanceIssueType.HIGH_ERROR_RATE,
                        severity=AlertSeverity.CRITICAL if avg_error_rate > 0.1 else AlertSeverity.HIGH,
                        title=f"High Error Rate",
                        description=f"Endpoint {endpoint} has high error rate: {avg_error_rate:.2%}",
                        affected_endpoints=[endpoint],
                        metrics={"error_rate": avg_error_rate},
                        detected_at=time.time(),
                        suggested_actions=[
                            "Check application logs",
                            "Investigate error patterns",
                            "Review recent deployments",
                            "Monitor external dependencies"
                        ]
                    ))

            # 缓存效率问题
            if "cache_hit_rate" in analysis:
                avg_cache_rate = analysis["cache_hit_rate"].get("average", 1)
                if avg_cache_rate < self.thresholds["cache_hit_rate"]:
                    issues.append(PerformanceIssue(
                        issue_id=f"low_cache_hit_rate_{endpoint}_{int(time.time())}",
                        type=PerformanceIssueType.CACHE_EFFICIENCY,
                        severity=AlertSeverity.MEDIUM,
                        title=f"Low Cache Hit Rate",
                        description=f"Endpoint {endpoint} has low cache hit rate: {avg_cache_rate:.2%}",
                        affected_endpoints=[endpoint],
                        metrics={"cache_hit_rate": avg_cache_rate},
                        detected_at=time.time(),
                        suggested_actions=[
                            "Review cache key patterns",
                            "Adjust cache TTL settings",
                            "Optimize cache warming strategy",
                            "Check cache invalidation logic"
                        ]
                    ))

        except Exception as e:
            logger.error(f"Error detecting endpoint issues for {endpoint}: {e}")

        return issues

    async def _analyze_system_health(self) -> Dict:
        """分析系统健康状态"""
        health = {
            "overall_status": "healthy",
            "health_score": 100,
            "critical_issues": 0,
            "warnings": 0
        }

        # 统计问题
        critical_issues = sum(1 for issue in self.issues_history if issue.severity == AlertSeverity.CRITICAL)
        medium_issues = sum(1 for issue in self.issues_history if issue.severity == AlertSeverity.MEDIUM)

        health["critical_issues"] = critical_issues
        health["warnings"] = medium_issues

        # 计算健康分数
        health_score = 100
        health_score -= critical_issues * 25
        health_score -= medium_issues * 10
        health_score = max(0, health_score)

        health["health_score"] = health_score

        # 确定整体状态
        if health_score >= 80:
            health["overall_status"] = "healthy"
        elif health_score >= 60:
            health["overall_status"] = "degraded"
        elif health_score >= 40:
            health["overall_status"] = "unhealthy"
        else:
            health["overall_status"] = "critical"

        return health

    async def _generate_recommendations(self, analysis: Dict) -> List[Dict]:
        """生成优化建议"""
        recommendations = []

        try:
            # 基于问题生成建议
            global_issues = analysis.get("global_issues", [])
            issue_types = [issue.type for issue in global_issues]

            # 响应时间优化建议
            if PerformanceIssueType.SLOW_RESPONSE in issue_types:
                slow_endpoints = [issue for issue in global_issues
                                if issue.type == PerformanceIssueType.SLOW_RESPONSE]
                if len(slow_endpoints) > 2:
                    recommendations.append({
                        "category": "performance_optimization",
                        "priority": "high",
                        "title": "System-wide Performance Optimization Needed",
                        "description": "Multiple endpoints show slow response times",
                        "actions": [
                            "Review database query optimization",
                            "Implement aggressive caching",
                            "Consider asynchronous processing",
                            "Add response compression"
                        ]
                    })

            # 错误率优化建议
            if PerformanceIssueType.HIGH_ERROR_RATE in issue_types:
                recommendations.append({
                    "category": "reliability_improvement",
                    "priority": "critical",
                    "title": "High Error Rate Detected",
                    "description": "System shows elevated error rates",
                    "actions": [
                        "Implement comprehensive error monitoring",
                        "Add circuit breaker patterns",
                        "Review external service dependencies",
                        "Implement retry mechanisms"
                    ]
                })

            # 缓存优化建议
            if PerformanceIssueType.CACHE_EFFICIENCY in issue_types:
                recommendations.append({
                    "category": "cache_optimization",
                    "priority": "medium",
                    "title": "Cache Efficiency Improvement",
                    "description": "Cache hit rates are below optimal levels",
                    "actions": [
                        "Optimize cache key strategies",
                        "Implement cache warming",
                        "Adjust cache TTL settings",
                        "Review cache invalidation patterns"
                    ]
                })

            # 并发优化建议
            system_health = analysis.get("system_health", {})
            if system_health.get("health_score", 100) < 70:
                recommendations.append({
                    "category": "scalability",
                    "priority": "high",
                    "title": "System Scalability Improvement",
                    "description": "System health score indicates performance degradation",
                    "actions": [
                        "Consider horizontal scaling",
                        "Implement load balancing",
                        "Optimize resource allocation",
                        "Review connection pool settings"
                    ]
                })

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")

        return recommendations

    async def _analysis_loop(self):
        """分析主循环"""
        while True:
            try:
                # 定期分析
                await asyncio.sleep(60)  # 每分钟分析一次

                # 检测全局问题
                issues = await self._detect_global_issues()
                if issues:
                    self.issues_history.extend(issues)
                    # 保持问题历史在合理范围内
                    if len(self.issues_history) > 100:
                        self.issues_history = self.issues_history[-50:]

                    # 记录问题
                    for issue in issues:
                        logger.warning(f"Performance issue detected: {issue.title} - {issue.description}")

                # 发现模式
                await self._discover_patterns()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in analysis loop: {e}")
                await asyncio.sleep(10)

    async def _detect_global_issues(self) -> List[PerformanceIssue]:
        """检测全局问题"""
        issues = []

        try:
            # 聚合所有端点的最新指标
            recent_metrics = []
            for endpoint, history in self.performance_history.items():
                if history:
                    recent_metrics.append(history[-1])

            if not recent_metrics:
                return issues

            # 计算系统级指标
            avg_response_time = statistics.mean([m.get('response_time', 0) for m in recent_metrics])
            avg_error_rate = statistics.mean([m.get('error_rate', 0) for m in recent_metrics])
            total_concurrent = sum([m.get('concurrent_requests', 0) for m in recent_metrics])

            # 检测系统级问题
            if avg_response_time > self.thresholds["response_time_p95"] * 1.5:
                issues.append(PerformanceIssue(
                    issue_id=f"global_slow_response_{int(time.time())}",
                    type=PerformanceIssueType.SLOW_RESPONSE,
                    severity=AlertSeverity.HIGH,
                    title="Global Slow Response Time",
                    description=f"System-wide average response time is slow: {avg_response_time:.3f}s",
                    affected_endpoints=list(self.performance_history.keys()),
                    metrics={"avg_response_time": avg_response_time},
                    detected_at=time.time(),
                    suggested_actions=[
                        "Check system resource utilization",
                        "Review database performance",
                        "Investigate network latency",
                        "Scale system resources"
                    ]
                ))

            if avg_error_rate > self.thresholds["error_rate"]:
                issues.append(PerformanceIssue(
                    issue_id=f"global_high_error_rate_{int(time.time())}",
                    type=PerformanceIssueType.HIGH_ERROR_RATE,
                    severity=AlertSeverity.CRITICAL,
                    title="Global High Error Rate",
                    description=f"System-wide error rate is high: {avg_error_rate:.2%}",
                    affected_endpoints=list(self.performance_history.keys()),
                    metrics={"avg_error_rate": avg_error_rate},
                    detected_at=time.time(),
                    suggested_actions=[
                        "Check application logs",
                        "Review recent deployments",
                        "Monitor external services",
                        "Implement circuit breakers"
                    ]
                ))

            if total_concurrent > self.thresholds["concurrent_requests"]:
                issues.append(PerformanceIssue(
                    issue_id=f"high_concurrent_load_{int(time.time())}",
                    type=PerformanceIssueType.CONCURRENT_OVERLOAD,
                    severity=AlertSeverity.MEDIUM,
                    title="High Concurrent Load",
                    description=f"System experiencing high concurrent load: {total_concurrent}",
                    affected_endpoints=list(self.performance_history.keys()),
                    metrics={"total_concurrent": total_concurrent},
                    detected_at=time.time(),
                    suggested_actions=[
                        "Implement rate limiting",
                        "Add load balancing",
                        "Scale horizontally",
                        "Optimize request processing"
                    ]
                ))

        except Exception as e:
            logger.error(f"Error detecting global issues: {e}")

        return issues

    async def _discover_patterns(self):
        """发现性能模式"""
        try:
            # 聚合所有历史数据
            all_metrics = []
            for history in self.performance_history.values():
                all_metrics.extend(history)

            if len(all_metrics) < self.ml_analyzer.min_training_samples:
                return

            # 使用聚类发现模式
            if not self.ml_analyzer.is_trained:
                success = self.ml_analyzer.train_models(all_metrics)
                if not success:
                    return

            # 执行聚类
            cluster_labels = self.ml_analyzer.cluster_patterns(all_metrics)

            # 分析聚类结果
            for i, label in enumerate(set(cluster_labels)):
                cluster_indices = [j for j, l in enumerate(cluster_labels) if l == label]
                cluster_metrics = [all_metrics[j] for j in cluster_indices]

                if len(cluster_metrics) > 5:  # 只关注有意义的模式
                    await self._analyze_cluster_pattern(i, cluster_metrics)

        except Exception as e:
            logger.error(f"Error discovering patterns: {e}")

    async def _analyze_cluster_pattern(self, cluster_id: int, metrics: List[Dict]):
        """分析聚类模式"""
        try:
            # 计算聚类特征
            avg_response_time = statistics.mean([m.get('response_time', 0) for m in metrics])
            avg_error_rate = statistics.mean([m.get('error_rate', 0) for m in metrics])
            std_response_time = statistics.stdev([m.get('response_time', 0) for m in metrics])

            # 确定模式类型
            if avg_response_time > 1.0 and std_response_time > 0.5:
                pattern_type = "high_variance_slow"
                name = "High Variance Slow Pattern"
                description = "Endpoints with slow and highly variable response times"
            elif avg_error_rate > 0.05:
                pattern_type = "error_prone"
                name = "Error Prone Pattern"
                description = "Endpoints with elevated error rates"
            elif avg_response_time < 0.1:
                pattern_type = "fast_responsive"
                name = "Fast Responsive Pattern"
                description = "Endpoints with consistently fast response times"
            else:
                pattern_type = "normal_behavior"
                name = "Normal Behavior Pattern"
                description = "Endpoints with normal performance characteristics"

            pattern = PerformancePattern(
                pattern_id=f"pattern_{cluster_id}",
                name=name,
                description=description,
                pattern_type=pattern_type,
                characteristics={
                    "avg_response_time": avg_response_time,
                    "avg_error_rate": avg_error_rate,
                    "std_response_time": std_response_time,
                    "sample_count": len(metrics)
                },
                frequency=len(metrics)
            )

            self.patterns[pattern.pattern_id] = pattern

        except Exception as e:
            logger.error(f"Error analyzing cluster pattern: {e}")

    async def _retrain_models(self):
        """重新训练机器学习模型"""
        try:
            # 聚合所有数据
            all_metrics = []
            for history in self.performance_history.values():
                all_metrics.extend(history)

            if len(all_metrics) >= self.ml_analyzer.min_training_samples:
                success = self.ml_analyzer.train_models(all_metrics)
                if success:
                    logger.info("ML models retrained successfully")

        except Exception as e:
            logger.error(f"Error retraining models: {e}")

    def get_analysis_summary(self) -> Dict:
        """获取分析摘要"""
        return {
            "performance_endpoints": len(self.performance_history),
            "total_issues": len(self.issues_history),
            "discovered_patterns": len(self.patterns),
            "ml_models_trained": self.ml_analyzer.is_trained,
            "last_analysis_time": time.time()
        }

    def get_recent_issues(self, limit: int = 20) -> List[Dict]:
        """获取最近的问题"""
        recent_issues = sorted(
            self.issues_history,
            key=lambda x: x.detected_at,
            reverse=True
        )
        return [issue.to_dict() for issue in recent_issues[:limit]]

    def get_performance_patterns(self) -> List[Dict]:
        """获取性能模式"""
        return [
            {
                "pattern_id": pattern.pattern_id,
                "name": pattern.name,
                "description": pattern.description,
                "pattern_type": pattern.pattern_type,
                "characteristics": pattern.characteristics,
                "frequency": pattern.frequency
            }
            for pattern in self.patterns.values()
        ]


# 全局分析器实例
_performance_analyzer: Optional[IntelligentPerformanceAnalyzer] = None


async def get_performance_analyzer() -> IntelligentPerformanceAnalyzer:
    """获取全局性能分析器实例"""
    global _performance_analyzer
    if _performance_analyzer is None:
        _performance_analyzer = IntelligentPerformanceAnalyzer()
        await _performance_analyzer.start_analysis()
    return _performance_analyzer


# 便捷函数
async def analyze_endpoint_performance(endpoint: str) -> Dict:
    """分析端点性能"""
    analyzer = await get_performance_analyzer()
    return await analyzer.analyze_performance(endpoint)


async def get_system_performance_analysis() -> Dict:
    """获取系统性能分析"""
    analyzer = await get_performance_analyzer()
    return await analyzer.analyze_performance()