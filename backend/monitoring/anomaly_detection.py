"""
机器学习异常检测模块
基于Isolation Forest和其他算法实现智能异常检测
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.cluster import DBSCAN
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import joblib
import json
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class AnomalyResult:
    """异常检测结果"""
    is_anomaly: bool
    anomaly_score: float
    confidence: float
    feature_contributions: Dict[str, float]
    detected_at: datetime
    model_version: str
    threshold_used: float

@dataclass
class ModelPerformance:
    """模型性能指标"""
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    false_positive_rate: float
    training_date: datetime
    training_samples: int

class FeatureExtractor:
    """特征提取��"""

    def __init__(self):
        self.feature_names = [
            'value', 'rate_of_change', 'moving_avg_5', 'moving_avg_15', 'moving_avg_60',
            'volatility_5', 'volatility_15', 'trend_slope_15', 'trend_slope_60',
            'hour_of_day', 'day_of_week', 'is_weekend', 'is_business_hours',
            'deviation_from_mean', 'deviation_from_median', 'percentile_rank',
            'z_score', 'iqr_score', 'seasonal_deviation'
        ]

    def extract_features(self, data: List[Dict], current_index: int = -1) -> np.ndarray:
        """从时间序列数据中提取特征"""
        if not data or len(data) < 5:
            return np.zeros(len(self.feature_names))

        if current_index == -1:
            current_index = len(data) - 1

        current_point = data[current_index]
        current_value = current_point.get('value', 0)
        current_time = datetime.fromisoformat(current_point['timestamp'])

        # 基础特征
        features = {}

        # 1. 当前值
        features['value'] = current_value

        # 2. 变化率
        if current_index > 0:
            prev_value = data[current_index - 1].get('value', 0)
            features['rate_of_change'] = (current_value - prev_value) / max(abs(prev_value), 1)
        else:
            features['rate_of_change'] = 0

        # 3. 移动平均
        features['moving_avg_5'] = self._calculate_moving_average(data, current_index, 5)
        features['moving_avg_15'] = self._calculate_moving_average(data, current_index, 15)
        features['moving_avg_60'] = self._calculate_moving_average(data, current_index, 60)

        # 4. 波动率
        features['volatility_5'] = self._calculate_volatility(data, current_index, 5)
        features['volatility_15'] = self._calculate_volatility(data, current_index, 15)

        # 5. 趋势斜率
        features['trend_slope_15'] = self._calculate_trend_slope(data, current_index, 15)
        features['trend_slope_60'] = self._calculate_trend_slope(data, current_index, 60)

        # 6. 时间特征
        features['hour_of_day'] = current_time.hour
        features['day_of_week'] = current_time.weekday()
        features['is_weekend'] = 1 if current_time.weekday() >= 5 else 0
        features['is_business_hours'] = 1 if 9 <= current_time.hour <= 17 else 0

        # 7. 统计特征
        values = [point.get('value', 0) for point in data[:current_index + 1]]
        if values:
            mean_val = np.mean(values)
            median_val = np.median(values)
            std_val = np.std(values) if len(values) > 1 else 1

            features['deviation_from_mean'] = (current_value - mean_val) / max(std_val, 1)
            features['deviation_from_median'] = (current_value - median_val) / max(std_val, 1)

            # 百分位排名
            features['percentile_rank'] = (sum(1 for v in values if v <= current_value) / len(values)) * 100

            # Z-score
            features['z_score'] = (current_value - mean_val) / max(std_val, 1)

            # IQR分数
            if len(values) > 3:
                q75, q25 = np.percentile(values, [75, 25])
                iqr = q75 - q25
                features['iqr_score'] = (current_value - median_val) / max(iqr, 1)
            else:
                features['iqr_score'] = 0

            # 季节性偏差（基于小时的偏差）
            hourly_values = defaultdict(list)
            for point in data:
                time = datetime.fromisoformat(point['timestamp'])
                hourly_values[time.hour].append(point.get('value', 0))

            if current_time.hour in hourly_values and len(hourly_values[current_time.hour]) > 2:
                hourly_avg = np.mean(hourly_values[current_time.hour])
                hourly_std = np.std(hourly_values[current_time.hour])
                features['seasonal_deviation'] = (current_value - hourly_avg) / max(hourly_std, 1)
            else:
                features['seasonal_deviation'] = 0
        else:
            # 默认值
            for feature in ['deviation_from_mean', 'deviation_from_median', 'percentile_rank',
                          'z_score', 'iqr_score', 'seasonal_deviation']:
                features[feature] = 0

        # 返回特征向量（按固定顺序）
        return np.array([features.get(name, 0) for name in self.feature_names])

    def _calculate_moving_average(self, data: List[Dict], current_index: int, window: int) -> float:
        """计算移动平均"""
        start_index = max(0, current_index - window + 1)
        values = [point.get('value', 0) for point in data[start_index:current_index + 1]]
        return np.mean(values) if values else 0

    def _calculate_volatility(self, data: List[Dict], current_index: int, window: int) -> float:
        """计算波动率（标准差）"""
        start_index = max(0, current_index - window + 1)
        values = [point.get('value', 0) for point in data[start_index:current_index + 1]]
        return np.std(values) if len(values) > 1 else 0

    def _calculate_trend_slope(self, data: List[Dict], current_index: int, window: int) -> float:
        """计算趋势斜率"""
        start_index = max(0, current_index - window + 1)
        if current_index - start_index < 2:
            return 0

        x = np.arange(len(data[start_index:current_index + 1]))
        y = np.array([point.get('value', 0) for point in data[start_index:current_index + 1]])

        # 线性回归计算斜率
        if len(x) > 1 and len(y) > 1:
            slope = np.polyfit(x, y, 1)[0]
            return slope
        return 0

class AnomalyDetector:
    """异常检测器主类"""

    def __init__(self, model_dir: str = "models/anomaly_detection"):
        self.models = {}  # metric_name -> model
        self.scalers = {}  # metric_name -> scaler
        self.feature_extractor = FeatureExtractor()
        self.training_data = {}  # metric_name -> training_data
        self.performance_metrics = {}  # metric_name -> ModelPerformance
        self.model_dir = model_dir
        self.min_training_samples = 100
        self.max_training_samples = 5000
        self.detection_threshold = -0.1  # Isolation Forest阈值

    def train_model(self, metric_name: str, historical_data: List[Dict],
                   force_retrain: bool = False) -> bool:
        """训练异常检测模型"""
        try:
            # 检查是否需要重新训练
            if (not force_retrain and
                metric_name in self.models and
                metric_name in self.performance_metrics):

                last_training = self.performance_metrics[metric_name].training_date
                if datetime.utcnow() - last_training < timedelta(days=7):
                    logger.info(f"Model for {metric_name} is recent, skipping training")
                    return True

            # 检查数据量
            if len(historical_data) < self.min_training_samples:
                logger.warning(f"Insufficient data for {metric_name}: {len(historical_data)} < {self.min_training_samples}")
                return False

            # 限制训练数据量
            if len(historical_data) > self.max_training_samples:
                historical_data = historical_data[-self.max_training_samples:]

            logger.info(f"Training anomaly detection model for {metric_name} with {len(historical_data)} samples")

            # 提取特征
            features = []
            valid_indices = []

            for i in range(len(historical_data)):
                try:
                    feature_vector = self.feature_extractor.extract_features(historical_data, i)
                    if not np.isnan(feature_vector).any():
                        features.append(feature_vector)
                        valid_indices.append(i)
                except Exception as e:
                    logger.warning(f"Failed to extract features for {metric_name} at index {i}: {e}")

            if len(features) < self.min_training_samples:
                logger.warning(f"Insufficient valid features for {metric_name}: {len(features)} < {self.min_training_samples}")
                return False

            features = np.array(features)

            # 数据标准化
            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(features)

            # 训练Isolation Forest模型
            model = IsolationForest(
                contamination=0.1,  # 假设10%的异常率
                random_state=42,
                n_estimators=100,
                max_samples='auto',
                bootstrap=False
            )

            model.fit(scaled_features)

            # 保存模型和标准化器
            self.models[metric_name] = model
            self.scalers[metric_name] = scaler
            self.training_data[metric_name] = historical_data

            # 评估模型性能
            performance = self._evaluate_model(model, scaled_features)
            self.performance_metrics[metric_name] = performance

            # 保存模型到文件
            self._save_model(metric_name, model, scaler, performance)

            logger.info(f"Successfully trained model for {metric_name} - F1: {performance.f1_score:.3f}")
            return True

        except Exception as e:
            logger.error(f"Failed to train model for {metric_name}: {e}")
            return False

    def detect_anomaly(self, metric_name: str, current_data: Dict,
                      historical_data: List[Dict] = None) -> Optional[AnomalyResult]:
        """检测异常"""
        try:
            if metric_name not in self.models:
                # 如果没有模型，尝试训练一个
                if historical_data and len(historical_data) >= self.min_training_samples:
                    if not self.train_model(metric_name, historical_data):
                        return None
                else:
                    return None

            model = self.models[metric_name]
            scaler = self.scalers[metric_name]

            # 获取历史数据用于特征提取
            if historical_data is None:
                historical_data = self.training_data.get(metric_name, [])

            if not historical_data:
                return None

            # 确保当前数据在历史数据的末尾
            training_data = historical_data.copy()
            training_data.append(current_data)

            # 提取特征
            features = self.feature_extractor.extract_features(training_data, -1)

            if np.isnan(features).any():
                logger.warning(f"Invalid features detected for {metric_name}")
                return None

            # 标准化特征
            scaled_features = scaler.transform([features])[0]

            # 预测异常
            anomaly_score = model.decision_function([scaled_features])[0]
            is_anomaly = model.predict([scaled_features])[0] == -1

            # 计算置信度
            confidence = self._calculate_confidence(anomaly_score, metric_name)

            # 计算特征贡献
            feature_contributions = self._calculate_feature_contributions(
                scaled_features, model, metric_name
            )

            result = AnomalyResult(
                is_anomaly=is_anomaly,
                anomaly_score=float(anomaly_score),
                confidence=float(confidence),
                feature_contributions=feature_contributions,
                detected_at=datetime.utcnow(),
                model_version=self._get_model_version(metric_name),
                threshold_used=self.detection_threshold
            )

            return result

        except Exception as e:
            logger.error(f"Failed to detect anomaly for {metric_name}: {e}")
            return None

    def _evaluate_model(self, model, features: np.ndarray) -> ModelPerformance:
        """评估模型性能"""
        try:
            # 使用Isolation Forest的决策函数作为预测分数
            scores = model.decision_function(features)
            predictions = model.predict(features)

            # 由于这是无监督学习，我们使用分数分布来估算性能
            threshold = np.percentile(scores, 10)  # 假设最低10%为异常

            # 估算性能指标（简化版本）
            predicted_anomalies = predictions == -1
            true_anomalies = scores <= threshold

            if predicted_anomalies.sum() > 0:
                precision = (predicted_anomalies & true_anomalies).sum() / predicted_anomalies.sum()
                recall = (predicted_anomalies & true_anomalies).sum() / true_anomalies.sum()
                f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            else:
                precision = recall = f1_score = 0

            accuracy = (predictions == (scores > threshold).astype(int)).mean()
            false_positive_rate = predicted_anomalies.sum() / len(predictions)

            return ModelPerformance(
                precision=float(precision),
                recall=float(recall),
                f1_score=float(f1_score),
                accuracy=float(accuracy),
                false_positive_rate=float(false_positive_rate),
                training_date=datetime.utcnow(),
                training_samples=len(features)
            )

        except Exception as e:
            logger.error(f"Failed to evaluate model: {e}")
            return ModelPerformance(
                precision=0.0, recall=0.0, f1_score=0.0, accuracy=0.0,
                false_positive_rate=0.0, training_date=datetime.utcnow(),
                training_samples=0
            )

    def _calculate_confidence(self, anomaly_score: float, metric_name: str) -> float:
        """计算检测置信度"""
        # 基于分数偏离阈值的程度计算置信度
        if metric_name in self.performance_metrics:
            fpr = self.performance_metrics[metric_name].false_positive_rate
            # 使用历史误报率调整置信度
            adjusted_score = anomaly_score + (fpr * 0.1)
        else:
            adjusted_score = anomaly_score

        # 将分数映射到0-1置信度范围
        confidence = max(0, min(1, abs(adjusted_score) * 2))
        return confidence

    def _calculate_feature_contributions(self, features: np.ndarray, model, metric_name: str) -> Dict[str, float]:
        """计算特征对异常检测的贡献度"""
        try:
            # 简化的特征贡献计算
            feature_names = self.feature_extractor.feature_names

            # 计算每个特征与平均值的偏差
            if metric_name in self.training_data and len(self.training_data[metric_name]) > 10:
                # 使用训练数据计算特征统计
                training_features = []
                for i in range(min(100, len(self.training_data[metric_name]))):
                    feat = self.feature_extractor.extract_features(self.training_data[metric_name], i)
                    if not np.isnan(feat).any():
                        training_features.append(feat)

                if training_features:
                    training_features = np.array(training_features)
                    feature_means = np.mean(training_features, axis=0)
                    feature_stds = np.std(training_features, axis=0)

                    contributions = {}
                    for i, name in enumerate(feature_names):
                        if i < len(features) and i < len(feature_means) and feature_stds[i] > 0:
                            z_score = abs(features[i] - feature_means[i]) / feature_stds[i]
                            contributions[name] = float(z_score)
                        else:
                            contributions[name] = 0.0

                    return contributions

            # 回退到简单的特征值贡献
            return {name: float(abs(features[i]) if i < len(features) else 0.0)
                   for i, name in enumerate(feature_names)}

        except Exception as e:
            logger.error(f"Failed to calculate feature contributions: {e}")
            return {}

    def _save_model(self, metric_name: str, model, scaler, performance: ModelPerformance):
        """保存模型到文件"""
        try:
            import os
            os.makedirs(self.model_dir, exist_ok=True)

            model_data = {
                'model': model,
                'scaler': scaler,
                'performance': performance,
                'feature_names': self.feature_extractor.feature_names,
                'training_date': datetime.utcnow().isoformat()
            }

            model_file = f"{self.model_dir}/{metric_name}_model.joblib"
            joblib.dump(model_data, model_file)

            logger.info(f"Model saved for {metric_name} to {model_file}")

        except Exception as e:
            logger.error(f"Failed to save model for {metric_name}: {e}")

    def load_model(self, metric_name: str) -> bool:
        """从文件加载模型"""
        try:
            model_file = f"{self.model_dir}/{metric_name}_model.joblib"

            if not os.path.exists(model_file):
                return False

            model_data = joblib.load(model_file)

            self.models[metric_name] = model_data['model']
            self.scalers[metric_name] = model_data['scaler']
            self.performance_metrics[metric_name] = model_data['performance']

            logger.info(f"Model loaded for {metric_name} from {model_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to load model for {metric_name}: {e}")
            return False

    def _get_model_version(self, metric_name: str) -> str:
        """获取模型版本"""
        if metric_name in self.performance_metrics:
            return self.performance_metrics[metric_name].training_date.strftime("%Y%m%d_%H%M%S")
        return "unknown"

    def get_model_info(self, metric_name: str) -> Optional[Dict]:
        """获取模型信息"""
        if metric_name not in self.models:
            return None

        performance = self.performance_metrics.get(metric_name)
        if not performance:
            return None

        return {
            'metric_name': metric_name,
            'model_version': self._get_model_version(metric_name),
            'training_samples': performance.training_samples,
            'training_date': performance.training_date.isoformat(),
            'performance': {
                'precision': performance.precision,
                'recall': performance.recall,
                'f1_score': performance.f1_score,
                'accuracy': performance.accuracy,
                'false_positive_rate': performance.false_positive_rate
            },
            'feature_count': len(self.feature_extractor.feature_names),
            'detection_threshold': self.detection_threshold
        }

    def list_trained_models(self) -> List[str]:
        """列出所有已训练的模型"""
        return list(self.models.keys())

    def retrain_all_models(self, training_data: Dict[str, List[Dict]]) -> Dict[str, bool]:
        """重新训练所有模型"""
        results = {}

        for metric_name, data in training_data.items():
            try:
                success = self.train_model(metric_name, data, force_retrain=True)
                results[metric_name] = success
                logger.info(f"Retrain {'successful' if success else 'failed'} for {metric_name}")
            except Exception as e:
                logger.error(f"Failed to retrain model for {metric_name}: {e}")
                results[metric_name] = False

        return results

    def cleanup_old_models(self, days_threshold: int = 30):
        """清理旧模型"""
        try:
            import os
            if not os.path.exists(self.model_dir):
                return

            current_time = datetime.utcnow()
            removed_count = 0

            for filename in os.listdir(self.model_dir):
                if filename.endswith("_model.joblib"):
                    file_path = os.path.join(self.model_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))

                    if (current_time - file_time).days > days_threshold:
                        os.remove(file_path)
                        removed_count += 1

            logger.info(f"Cleaned up {removed_count} old model files")

        except Exception as e:
            logger.error(f"Failed to cleanup old models: {e}")

# 全局异常检测器实例
anomaly_detector = AnomalyDetector()