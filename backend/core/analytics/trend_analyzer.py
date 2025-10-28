"""
趋势分析器
Trend Analyzer Module

提供企业级趋势分析和预测功能，包括：
- 时间序列分析
- 趋势预测模型
- 季节性分析
- 异常趋势检测
- 增长率分析
- 预测准确性评估
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import statistics
import math

from backend.config.settings import get_settings
from backend.core.cache.multi_level_cache import cache_manager

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class TrendData:
    """趋势数据点"""
    timestamp: datetime
    value: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TrendMetrics:
    """趋势指标"""
    trend_direction: str  # increasing, decreasing, stable
    trend_strength: float  # 0-1, 趋势强度
    growth_rate: float  # 增长率
    volatility: float  # 波动性
    seasonality: Optional[Dict[str, float]]  # 季节性指标
    confidence_level: float  # 预测置信度


@dataclass
class TrendForecast:
    """趋势预测"""
    forecast_id: str
    metric_name: str
    historical_data: List[TrendData]
    forecast_data: List[TrendData]
    forecast_period_days: int
    accuracy_score: float
    model_used: str
    created_at: datetime
    confidence_intervals: Dict[str, List[Tuple[float, float]]]


@dataclass
class AnomalyDetection:
    """异常检测结果"""
    anomaly_id: str
    metric_name: str
    anomaly_timestamp: datetime
    expected_value: float
    actual_value: float
    deviation_score: float
    anomaly_type: str  # spike, drop, pattern_change
    severity: str  # low, medium, high, critical


class TrendAnalyzer:
    """趋势分析器"""

    def __init__(self):
        self.cache_key_prefix = "trend_analyzer"
        self.data_dir = Path("data/analytics/trends")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 数据存储路径
        self.trends_data_path = self.data_dir / "trends_data.json"
        self.forecasts_path = self.data_dir / "forecasts.json"
        self.anomalies_path = self.data_dir / "anomalies.json"

        # 分析配置
        self.min_data_points = 7  # 最少数据点数
        self.forecast_horizon_days = 30  # 默认预测天数
        self.anomaly_threshold = 2.0  # 异常检测阈值（标准差倍数）

    async def analyze_trend(
        self,
        metric_name: str,
        data_points: List[TrendData],
        forecast_days: int = 30
    ) -> Tuple[TrendMetrics, TrendForecast]:
        """
        分析趋势并生成预测

        Args:
            metric_name: 指标名称
            data_points: 历史数据点
            forecast_days: 预测天数

        Returns:
            Tuple[TrendMetrics, TrendForecast]: 趋势指标和预测结果
        """
        try:
            if len(data_points) < self.min_data_points:
                logger.warning(f"Insufficient data points for trend analysis: {len(data_points)}")
                return self._create_default_analysis(metric_name, data_points)

            logger.info(f"Analyzing trend for {metric_name} with {len(data_points)} data points")

            # 分析趋势指标
            trend_metrics = self._calculate_trend_metrics(data_points)

            # 生成预测
            forecast = await self._generate_forecast(
                metric_name, data_points, forecast_days, trend_metrics
            )

            # 检测异常
            await self._detect_anomalies(metric_name, data_points, trend_metrics)

            # 缓存结果
            cache_key = f"{self.cache_key_prefix}:trend:{metric_name}:{datetime.now().date()}"
            await cache_manager.set(
                cache_key,
                {
                    "metrics": asdict(trend_metrics),
                    "forecast": asdict(forecast)
                },
                expire_seconds=3600
            )

            # 保存分析结果
            await self._save_trend_analysis(metric_name, trend_metrics, forecast)

            logger.info(f"Trend analysis completed for {metric_name}: {trend_metrics.trend_direction}")
            return trend_metrics, forecast

        except Exception as e:
            logger.error(f"Error analyzing trend for {metric_name}: {e}")
            return self._create_default_analysis(metric_name, data_points)

    async def get_forecast(
        self,
        metric_name: str,
        days_ahead: int = 7
    ) -> Optional[TrendForecast]:
        """
        获取预测结果

        Args:
            metric_name: 指标名称
            days_ahead: 预测天数

        Returns:
            Optional[TrendForecast]: 预测结果
        """
        try:
            cache_key = f"{self.cache_key_prefix}:forecast:{metric_name}"
            forecast_data = await cache_manager.get(cache_key)

            if forecast_data:
                forecast_data["created_at"] = datetime.fromisoformat(forecast_data["created_at"])
                forecast_data["historical_data"] = [
                    TrendData(
                        timestamp=datetime.fromisoformat(point["timestamp"]),
                        value=point["value"],
                        metadata=point.get("metadata")
                    )
                    for point in forecast_data["historical_data"]
                ]
                forecast_data["forecast_data"] = [
                    TrendData(
                        timestamp=datetime.fromisoformat(point["timestamp"]),
                        value=point["value"],
                        metadata=point.get("metadata")
                    )
                    for point in forecast_data["forecast_data"]
                ]
                return TrendForecast(**forecast_data)

            # 从文件加载
            return await self._load_forecast(metric_name)

        except Exception as e:
            logger.error(f"Error getting forecast for {metric_name}: {e}")
            return None

    async def detect_trend_anomalies(
        self,
        metric_name: str,
        data_points: List[TrendData]
    ) -> List[AnomalyDetection]:
        """
        检测趋势异常

        Args:
            metric_name: 指标名称
            data_points: 数据点

        Returns:
            List[AnomalyDetection]: 异常列表
        """
        try:
            if len(data_points) < self.min_data_points:
                return []

            anomalies = []
            values = [point.value for point in data_points]
            mean_val = statistics.mean(values)
            std_val = statistics.stdev(values) if len(values) > 1 else 0

            # 检测每个数据点的异常
            for i, point in enumerate(data_points):
                if std_val == 0:
                    continue

                z_score = abs(point.value - mean_val) / std_val

                if z_score > self.anomaly_threshold:
                    anomaly_type = self._classify_anomaly_type(data_points, i)
                    severity = self._classify_anomaly_severity(z_score)

                    anomalies.append(AnomalyDetection(
                        anomaly_id=f"{metric_name}_{i}_{point.timestamp.timestamp()}",
                        metric_name=metric_name,
                        anomaly_timestamp=point.timestamp,
                        expected_value=mean_val,
                        actual_value=point.value,
                        deviation_score=z_score,
                        anomaly_type=anomaly_type,
                        severity=severity
                    ))

            logger.info(f"Detected {len(anomalies)} anomalies for {metric_name}")
            return anomalies

        except Exception as e:
            logger.error(f"Error detecting anomalies for {metric_name}: {e}")
            return []

    def _calculate_trend_metrics(self, data_points: List[TrendData]) -> TrendMetrics:
        """计算趋势指标"""
        try:
            values = [point.value for point in data_points]
            timestamps = [point.timestamp.timestamp() for point in data_points]

            # 计算趋势方向和强度
            trend_direction, trend_strength = self._calculate_linear_trend(timestamps, values)

            # 计算增长率
            growth_rate = self._calculate_growth_rate(values)

            # 计算波动性
            volatility = self._calculate_volatility(values)

            # 检测季节性
            seasonality = self._detect_seasonality(data_points)

            # 计算预测置信度
            confidence_level = self._calculate_confidence_level(values, trend_strength)

            return TrendMetrics(
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                growth_rate=growth_rate,
                volatility=volatility,
                seasonality=seasonality,
                confidence_level=confidence_level
            )

        except Exception as e:
            logger.error(f"Error calculating trend metrics: {e}")
            return TrendMetrics(
                trend_direction="stable",
                trend_strength=0.0,
                growth_rate=0.0,
                volatility=0.0,
                seasonality=None,
                confidence_level=0.0
            )

    def _calculate_linear_trend(self, x_values: List[float], y_values: List[float]) -> Tuple[str, float]:
        """计算线性趋势"""
        try:
            if len(x_values) != len(y_values) or len(x_values) < 2:
                return "stable", 0.0

            n = len(x_values)
            sum_x = sum(x_values)
            sum_y = sum(y_values)
            sum_xy = sum(x * y for x, y in zip(x_values, y_values))
            sum_x2 = sum(x * x for x in x_values)

            # 计算线性回归系数
            denominator = n * sum_x2 - sum_x * sum_x
            if denominator == 0:
                return "stable", 0.0

            slope = (n * sum_xy - sum_x * sum_y) / denominator

            # 确定趋势方向
            if slope > 0.001:  # 正斜率
                direction = "increasing"
            elif slope < -0.001:  # 负斜率
                direction = "decreasing"
            else:
                direction = "stable"

            # 计算趋势强度（基于R²）
            y_mean = sum_y / n
            ss_total = sum((y - y_mean) ** 2 for y in y_values)
            y_pred = [slope * x + (sum_y - slope * sum_x) / n for x in x_values]
            ss_residual = sum((y - y_p) ** 2 for y, y_p in zip(y_values, y_pred))

            r_squared = 1 - (ss_residual / ss_total) if ss_total > 0 else 0
            strength = max(0, min(1, r_squared))

            return direction, strength

        except Exception as e:
            logger.error(f"Error calculating linear trend: {e}")
            return "stable", 0.0

    def _calculate_growth_rate(self, values: List[float]) -> float:
        """计算增长率"""
        try:
            if len(values) < 2:
                return 0.0

            # 使用复合增长率计算
            start_value = values[0]
            end_value = values[-1]
            periods = len(values) - 1

            if start_value <= 0:
                return 0.0

            growth_rate = (end_value / start_value) ** (1 / periods) - 1
            return growth_rate

        except Exception as e:
            logger.error(f"Error calculating growth rate: {e}")
            return 0.0

    def _calculate_volatility(self, values: List[float]) -> float:
        """计算波动性"""
        try:
            if len(values) < 2:
                return 0.0

            mean_val = statistics.mean(values)
            variance = statistics.variance(values)
            std_dev = math.sqrt(variance)

            # 相对波动性（变异系数）
            volatility = std_dev / mean_val if mean_val != 0 else 0
            return volatility

        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return 0.0

    def _detect_seasonality(self, data_points: List[TrendData]) -> Optional[Dict[str, float]]:
        """检测季节性"""
        try:
            if len(data_points) < 30:  # 至少需要30天的数据
                return None

            # 按星期几分组
            weekly_patterns = {}
            for point in data_points:
                day_of_week = point.timestamp.weekday()
                if day_of_week not in weekly_patterns:
                    weekly_patterns[day_of_week] = []
                weekly_patterns[day_of_week].append(point.value)

            # 计算每周期的平均值
            weekly_averages = {}
            for day, values in weekly_patterns.items():
                if values:
                    weekly_averages[day] = statistics.mean(values)

            # 检测是否存在明显的季节性模式
            if len(weekly_averages) >= 7:
                overall_avg = statistics.mean(list(weekly_averages.values()))
                seasonal_strength = max(
                    abs(avg - overall_avg) / overall_avg
                    for avg in weekly_averages.values()
                ) if overall_avg != 0 else 0

                if seasonal_strength > 0.1:  # 10%以上的变化认为是季节性
                    return {
                        "pattern": "weekly",
                        "strength": seasonal_strength,
                        "peak_day": max(weekly_averages, key=weekly_averages.get),
                        "low_day": min(weekly_averages, key=weekly_averages.get)
                    }

            return None

        except Exception as e:
            logger.error(f"Error detecting seasonality: {e}")
            return None

    def _calculate_confidence_level(self, values: List[float], trend_strength: float) -> float:
        """计算预测置信度"""
        try:
            # 基于数据量和趋势强度计算置信度
            data_quality = min(1.0, len(values) / 100)  # 数据量评分
            trend_score = trend_strength  # 趋势强度评分

            # 综合置信度
            confidence = (data_quality * 0.4 + trend_score * 0.6)
            return confidence

        except Exception as e:
            logger.error(f"Error calculating confidence level: {e}")
            return 0.0

    async def _generate_forecast(
        self,
        metric_name: str,
        data_points: List[TrendData],
        forecast_days: int,
        trend_metrics: TrendMetrics
    ) -> TrendForecast:
        """生成趋势预测"""
        try:
            forecast_id = f"{metric_name}_{datetime.now().timestamp()}"

            # 使用简单线性回归预测
            forecast_data = self._linear_regression_forecast(data_points, forecast_days)

            # 计算预测准确性（使用历史数据回测）
            accuracy_score = self._calculate_forecast_accuracy(data_points)

            # 生成置信区间
            confidence_intervals = self._generate_confidence_intervals(
                data_points, forecast_data, trend_metrics.confidence_level
            )

            return TrendForecast(
                forecast_id=forecast_id,
                metric_name=metric_name,
                historical_data=data_points,
                forecast_data=forecast_data,
                forecast_period_days=forecast_days,
                accuracy_score=accuracy_score,
                model_used="linear_regression",
                created_at=datetime.now(),
                confidence_intervals=confidence_intervals
            )

        except Exception as e:
            logger.error(f"Error generating forecast: {e}")
            # 返回默认预测
            return self._create_default_forecast(metric_name, data_points, forecast_days)

    def _linear_regression_forecast(self, data_points: List[TrendData], forecast_days: int) -> List[TrendData]:
        """线性回归预测"""
        try:
            if len(data_points) < 2:
                return []

            values = [point.value for point in data_points]
            timestamps = [point.timestamp.timestamp() for point in data_points]

            # 计算线性回归
            n = len(timestamps)
            sum_x = sum(timestamps)
            sum_y = sum(values)
            sum_xy = sum(x * y for x, y in zip(timestamps, values))
            sum_x2 = sum(x * x for x in timestamps)

            denominator = n * sum_x2 - sum_x * sum_x
            if denominator == 0:
                return []

            slope = (n * sum_xy - sum_x * sum_y) / denominator
            intercept = (sum_y - slope * sum_x) / n

            # 生成预测数据点
            forecast_data = []
            last_timestamp = data_points[-1].timestamp

            for i in range(1, forecast_days + 1):
                future_timestamp = last_timestamp + timedelta(days=i)
                future_x = future_timestamp.timestamp()
                predicted_value = slope * future_x + intercept

                forecast_data.append(TrendData(
                    timestamp=future_timestamp,
                    value=max(0, predicted_value),  # 确保非负值
                    metadata={"forecast": True, "day_ahead": i}
                ))

            return forecast_data

        except Exception as e:
            logger.error(f"Error in linear regression forecast: {e}")
            return []

    def _calculate_forecast_accuracy(self, data_points: List[TrendData]) -> float:
        """计算预测准确性（回测）"""
        try:
            if len(data_points) < 10:
                return 0.5  # 默认准确性

            # 使用最后20%的数据进行回测
            test_size = max(2, len(data_points) // 5)
            train_data = data_points[:-test_size]
            test_data = data_points[-test_size:]

            # 在训练数据上训练模型
            train_values = [point.value for point in train_data]
            train_timestamps = [point.timestamp.timestamp() for point in train_data]

            # 简单的移动平均预测
            if train_values:
                avg_value = statistics.mean(train_values)
                predictions = [avg_value] * len(test_data)
            else:
                predictions = [0] * len(test_data)

            # 计算预测误差
            actual_values = [point.value for point in test_data]
            mae = statistics.mean(abs(pred - actual) for pred, actual in zip(predictions, actual_values))

            # 归一化准确性（0-1）
            if actual_values:
                mean_actual = statistics.mean(actual_values)
                if mean_actual > 0:
                    accuracy = max(0, 1 - (mae / mean_actual))
                else:
                    accuracy = 0.5
            else:
                accuracy = 0.5

            return accuracy

        except Exception as e:
            logger.error(f"Error calculating forecast accuracy: {e}")
            return 0.5

    def _generate_confidence_intervals(
        self,
        data_points: List[TrendData],
        forecast_data: List[TrendData],
        confidence_level: float
    ) -> Dict[str, List[Tuple[float, float]]]:
        """生成置信区间"""
        try:
            if not data_points or not forecast_data:
                return {}

            values = [point.value for point in data_points]
            std_dev = statistics.stdev(values) if len(values) > 1 else 0

            # 置信区间宽度基于历史标准差和置信水平
            z_score = 1.96 if confidence_level > 0.8 else 1.645  # 95% or 90% 置信区间
            margin = z_score * std_dev

            intervals = []
            for point in forecast_data:
                lower_bound = max(0, point.value - margin)
                upper_bound = point.value + margin
                intervals.append((lower_bound, upper_bound))

            return {"forecast": intervals}

        except Exception as e:
            logger.error(f"Error generating confidence intervals: {e}")
            return {}

    def _classify_anomaly_type(self, data_points: List[TrendData], index: int) -> str:
        """分类异常类型"""
        try:
            if index == 0 or index >= len(data_points) - 1:
                return "spike"

            current_value = data_points[index].value
            prev_value = data_points[index - 1].value
            next_value = data_points[index + 1].value

            # 判断异常类型
            if current_value > prev_value * 1.5 and current_value > next_value * 1.5:
                return "spike"
            elif current_value < prev_value * 0.5 and current_value < next_value * 0.5:
                return "drop"
            else:
                return "pattern_change"

        except Exception:
            return "spike"

    def _classify_anomaly_severity(self, z_score: float) -> str:
        """分类异常严重程度"""
        if z_score > 4:
            return "critical"
        elif z_score > 3:
            return "high"
        elif z_score > 2:
            return "medium"
        else:
            return "low"

    def _create_default_analysis(self, metric_name: str, data_points: List[TrendData]) -> Tuple[TrendMetrics, TrendForecast]:
        """创建默认分析结果"""
        default_metrics = TrendMetrics(
            trend_direction="stable",
            trend_strength=0.0,
            growth_rate=0.0,
            volatility=0.0,
            seasonality=None,
            confidence_level=0.0
        )

        default_forecast = self._create_default_forecast(metric_name, data_points, 7)
        return default_metrics, default_forecast

    def _create_default_forecast(self, metric_name: str, data_points: List[TrendData], days: int) -> TrendForecast:
        """创建默认预测"""
        last_value = data_points[-1].value if data_points else 0
        last_timestamp = data_points[-1].timestamp if data_points else datetime.now()

        forecast_data = []
        for i in range(1, days + 1):
            forecast_data.append(TrendData(
                timestamp=last_timestamp + timedelta(days=i),
                value=last_value,
                metadata={"forecast": True, "day_ahead": i}
            ))

        return TrendForecast(
            forecast_id=f"{metric_name}_default_{datetime.now().timestamp()}",
            metric_name=metric_name,
            historical_data=data_points,
            forecast_data=forecast_data,
            forecast_period_days=days,
            accuracy_score=0.5,
            model_used="default",
            created_at=datetime.now(),
            confidence_intervals={}
        )

    async def _detect_anomalies(self, metric_name: str, data_points: List[TrendData], trend_metrics: TrendMetrics):
        """检测异常并保存"""
        try:
            anomalies = await self.detect_trend_anomalies(metric_name, data_points)
            if anomalies:
                await self._save_anomalies(metric_name, anomalies)
                logger.info(f"Saved {len(anomalies)} anomalies for {metric_name}")
        except Exception as e:
            logger.error(f"Error detecting and saving anomalies: {e}")

    async def _save_trend_analysis(self, metric_name: str, metrics: TrendMetrics, forecast: TrendForecast):
        """保存趋势分析结果"""
        try:
            analysis_data = {
                "metric_name": metric_name,
                "timestamp": datetime.now().isoformat(),
                "metrics": asdict(metrics),
                "forecast": asdict(forecast)
            }

            # 保存到文件
            with open(self.trends_data_path, 'a') as f:
                f.write(json.dumps(analysis_data, default=str) + '\n')

        except Exception as e:
            logger.error(f"Error saving trend analysis: {e}")

    async def _save_anomalies(self, metric_name: str, anomalies: List[AnomalyDetection]):
        """保存异常检测结果"""
        try:
            anomaly_data = {
                "metric_name": metric_name,
                "timestamp": datetime.now().isoformat(),
                "anomalies": [asdict(anomaly) for anomaly in anomalies]
            }

            # 保存到文件
            with open(self.anomalies_path, 'a') as f:
                f.write(json.dumps(anomaly_data, default=str) + '\n')

        except Exception as e:
            logger.error(f"Error saving anomalies: {e}")

    async def _load_forecast(self, metric_name: str) -> Optional[TrendForecast]:
        """从文件��载预测结果"""
        try:
            # TODO: 实现从文件加载预测结果的逻辑
            return None
        except Exception as e:
            logger.error(f"Error loading forecast: {e}")
            return None


# 全局实例
trend_analyzer = TrendAnalyzer()