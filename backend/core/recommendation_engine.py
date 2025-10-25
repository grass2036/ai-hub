"""
智能推荐引擎
Week 7 Day 2: 用户体验优化

提供多种推荐算法：
- 协同过滤推荐
- 基于内容的推荐
- 上下文感知推荐
- 混合推荐策略
"""

import asyncio
import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class RecommendationType(str, Enum):
    """推荐类型"""
    COLLABORATIVE = "collaborative"  # 协同过滤
    CONTENT_BASED = "content_based"  # 基于内容
    CONTEXT_AWARE = "context_aware"  # 上下文感知
    HYBRID = "hybrid"  # 混合推荐
    POPULAR = "popular"  # 热门推荐


class ItemType(str, Enum):
    """推荐项目类型"""
    AI_MODEL = "ai_model"
    API_ENDPOINT = "api_endpoint"
    WORKFLOW = "workflow"
    DOCUMENT = "document"
    TEMPLATE = "template"


@dataclass
class UserBehavior:
    """用户行为数据"""
    user_id: str
    item_id: str
    item_type: ItemType
    action: str  # 'view', 'use', 'like', 'share', 'save'
    rating: Optional[float] = None
    duration: Optional[int] = None  # 使用时长（秒）
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ItemFeatures:
    """项目特征"""
    item_id: str
    item_type: ItemType
    title: str
    description: str
    category: str
    tags: List[str]
    features: Dict[str, Any]
    popularity_score: float = 0.0
    usage_count: int = 0
    rating_avg: float = 0.0
    rating_count: int = 0


@dataclass
class Recommendation:
    """推荐结果"""
    item_id: str
    item_type: ItemType
    score: float
    reason: str
    confidence: float
    metadata: Dict[str, Any]


class RecommendationEngine:
    """智能推荐引擎"""

    def __init__(self, data_dir: str = "data/recommendations"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # 用户行为数据
        self.user_behaviors: Dict[str, List[UserBehavior]] = {}

        # 项目特征数据
        self.items: Dict[str, ItemFeatures] = {}

        # 用户特征矩阵
        self.user_item_matrix: Optional[np.ndarray] = None
        self.item_features_matrix: Optional[np.ndarray] = None

        # 相似度缓存
        self.similarity_cache: Dict[str, Dict[str, float]] = {}

        # 推荐结果缓存
        self.recommendation_cache: Dict[str, List[Recommendation]] = {}

        # 加载历史数据
        self._load_data()

    def _load_data(self):
        """加载历史数据"""
        try:
            # 加载用户行为
            behaviors_file = self.data_dir / "user_behaviors.json"
            if behaviors_file.exists():
                with open(behaviors_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_id, behaviors in data.items():
                        self.user_behaviors[user_id] = [
                            UserBehavior(**behavior) for behavior in behaviors
                        ]

            # 加载项目特征
            items_file = self.data_dir / "items.json"
            if items_file.exists():
                with open(items_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item_id, item_data in data.items():
                        self.items[item_id] = ItemFeatures(**item_data)

            logger.info(f"Loaded {len(self.user_behaviors)} users and {len(self.items)} items")

        except Exception as e:
            logger.error(f"Failed to load data: {e}")

    def _save_data(self):
        """保存数据"""
        try:
            # 保存用户行为
            behaviors_file = self.data_dir / "user_behaviors.json"
            behaviors_data = {}
            for user_id, behaviors in self.user_behaviors.items():
                behaviors_data[user_id] = [
                    asdict(behavior) for behavior in behaviors
                ]
                # 转换datetime为字符串
                for behavior in behaviors_data[user_id]:
                    if behavior['timestamp']:
                        behavior['timestamp'] = behavior['timestamp'].replace('T', ' ')[:-7]

            with open(behaviors_file, 'w', encoding='utf-8') as f:
                json.dump(behaviors_data, f, ensure_ascii=False, indent=2)

            # 保存项目特征
            items_file = self.data_dir / "items.json"
            items_data = {item_id: asdict(item) for item_id, item in self.items.items()}
            with open(items_file, 'w', encoding='utf-8') as f:
                json.dump(items_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Failed to save data: {e}")

    async def add_user_behavior(self, behavior: UserBehavior):
        """添加用户行为"""
        user_id = behavior.user_id

        if user_id not in self.user_behaviors:
            self.user_behaviors[user_id] = []

        self.user_behaviors[user_id].append(behavior)

        # 更新项目统计
        if behavior.item_id in self.items:
            item = self.items[behavior.item_id]
            item.usage_count += 1
            if behavior.rating:
                # 更新平均评分
                total_rating = item.rating_avg * item.rating_count + behavior.rating
                item.rating_count += 1
                item.rating_avg = total_rating / item.rating_count

        # 清除相关缓存
        self._clear_cache_for_user(user_id)

        # 保存数据
        self._save_data()

    def add_item(self, item: ItemFeatures):
        """添加项目"""
        self.items[item.item_id] = item
        self._save_data()

    def _clear_cache_for_user(self, user_id: str):
        """清除用户相关缓存"""
        if user_id in self.recommendation_cache:
            del self.recommendation_cache[user_id]

    def _build_user_item_matrix(self):
        """构建用户-项目矩阵"""
        if not self.user_behaviors:
            return

        # 获取所有用户和项目
        users = list(self.user_behaviors.keys())
        items = list(self.items.keys())

        if not users or not items:
            return

        # 创建用户和项目索引
        user_index = {user: i for i, user in enumerate(users)}
        item_index = {item: i for i, item in enumerate(items)}

        # 构建评分矩阵
        matrix = np.zeros((len(users), len(items)))

        for user_id, behaviors in self.user_behaviors.items():
            user_i = user_index[user_id]

            for behavior in behaviors:
                if behavior.item_id in item_index:
                    item_j = item_index[behavior.item_id]

                    # 根据行为类型计算评分
                    rating = self._behavior_to_rating(behavior)
                    if rating > 0:
                        matrix[user_i, item_j] = rating

        self.user_item_matrix = matrix

    def _behavior_to_rating(self, behavior: UserBehavior) -> float:
        """将行为转换为评分"""
        base_ratings = {
            'view': 1.0,
            'use': 3.0,
            'like': 4.0,
            'share': 4.5,
            'save': 5.0
        }

        base_rating = base_ratings.get(behavior.action, 0)

        # 如果有明确评分，使用明确评分
        if behavior.rating is not None:
            base_rating = behavior.rating

        # 根据使用时长调整评分
        if behavior.duration:
            # 使用时长越长，评分越高（最多增加1分）
            duration_bonus = min(behavior.duration / 300, 1.0)  # 5分钟为满分
            base_rating += duration_bonus * 0.2

        # 根据时间衰减（最近的行为权重更高）
        if behavior.timestamp:
            days_ago = (datetime.now() - behavior.timestamp).days
            time_decay = max(0.1, 1.0 - days_ago / 30)  # 30天衰减到0.1
            base_rating *= time_decay

        return min(5.0, base_rating)

    def _calculate_user_similarity(self, user1: str, user2: str) -> float:
        """计算用户相似度（余弦相似度）"""
        if user1 not in self.user_behaviors or user2 not in self.user_behaviors:
            return 0.0

        cache_key = f"{user1}_{user2}"
        if cache_key in self.similarity_cache:
            return self.similarity_cache[cache_key]

        # 获取用户行为
        behaviors1 = self.user_behaviors[user1]
        behaviors2 = self.user_behaviors[user2]

        # 构建项目评分向量
        items = set()
        for b in behaviors1 + behaviors2:
            items.add(b.item_id)

        if not items:
            return 0.0

        # 创建评分向量
        vector1 = np.zeros(len(items))
        vector2 = np.zeros(len(items))
        item_list = list(items)

        for behavior in behaviors1:
            if behavior.item_id in item_list:
                idx = item_list.index(behavior.item_id)
                vector1[idx] = self._behavior_to_rating(behavior)

        for behavior in behaviors2:
            if behavior.item_id in item_list:
                idx = item_list.index(behavior.item_id)
                vector2[idx] = self._behavior_to_rating(behavior)

        # 计算余弦相似度
        dot_product = np.dot(vector1, vector2)
        norm1 = np.linalg.norm(vector1)
        norm2 = np.linalg.norm(vector2)

        if norm1 == 0 or norm2 == 0:
            similarity = 0.0
        else:
            similarity = dot_product / (norm1 * norm2)

        # 缓存结果
        self.similarity_cache[cache_key] = similarity

        return similarity

    def _calculate_content_similarity(self, item1: str, item2: str) -> float:
        """计算内容相似度"""
        if item1 not in self.items or item2 not in self.items:
            return 0.0

        item1_features = self.items[item1]
        item2_features = self.items[item2]

        # 类别相似度
        category_sim = 1.0 if item1_features.category == item2_features.category else 0.0

        # 标签相似度（Jaccard相似度）
        tags1 = set(item1_features.tags)
        tags2 = set(item2_features.tags)
        if not tags1 or not tags2:
            tag_sim = 0.0
        else:
            intersection = tags1.intersection(tags2)
            union = tags1.union(tags2)
            tag_sim = len(intersection) / len(union) if union else 0.0

        # 特征相似度
        feature_sim = 0.0
        common_features = set(item1_features.features.keys()) & set(item2_features.features.keys())
        if common_features:
            similarities = []
            for feature in common_features:
                val1 = item1_features.features[feature]
                val2 = item2_features.features[feature]
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    # 数值特征相似度
                    max_val = max(abs(val1), abs(val2), 1e-6)
                    sim = 1.0 - abs(val1 - val2) / max_val
                    similarities.append(sim)
                elif val1 == val2:
                    # 分类特征相似度
                    similarities.append(1.0)
            feature_sim = np.mean(similarities) if similarities else 0.0

        # 加权组合
        return 0.4 * category_sim + 0.4 * tag_sim + 0.2 * feature_sim

    async def collaborative_filtering_recommend(self, user_id: str, n: int = 10) -> List[Recommendation]:
        """协同过滤推荐"""
        if user_id not in self.user_behaviors:
            return await self.popular_items_recommend(n)

        # 找到相似用户
        similarities = []
        for other_user in self.user_behaviors:
            if other_user != user_id:
                sim = self._calculate_user_similarity(user_id, other_user)
                if sim > 0:
                    similarities.append((other_user, sim))

        if not similarities:
            return await self.popular_items_recommend(n)

        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)

        # 获取用户已经交互过的项目
        user_items = set()
        for behavior in self.user_behaviors[user_id]:
            user_items.add(behavior.item_id)

        # 计算推荐分数
        scores = {}
        for other_user, similarity in similarities[:20]:  # 取前20个相似用户
            for behavior in self.user_behaviors[other_user]:
                if behavior.item_id not in user_items:
                    rating = self._behavior_to_rating(behavior)
                    if behavior.item_id not in scores:
                        scores[behavior.item_id] = 0
                    scores[behavior.item_id] += similarity * rating

        # 生成推荐
        recommendations = []
        for item_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]:
            if item_id in self.items:
                item = self.items[item_id]
                confidence = min(score / 5.0, 1.0)

                recommendations.append(Recommendation(
                    item_id=item_id,
                    item_type=item.item_type,
                    score=score,
                    reason=f"与您相似的用户也使用了{item.title}",
                    confidence=confidence,
                    metadata={"similarity_score": score}
                ))

        return recommendations

    async def content_based_recommend(self, user_id: str, n: int = 10) -> List[Recommendation]:
        """基于内容的推荐"""
        if user_id not in self.user_behaviors:
            return await self.popular_items_recommend(n)

        # 获取用户喜欢的项目
        liked_items = []
        for behavior in self.user_behaviors[user_id]:
            if behavior.action in ['like', 'share', 'save'] or (behavior.rating and behavior.rating >= 4):
                liked_items.append(behavior.item_id)

        if not liked_items:
            return await self.popular_items_recommend(n)

        # 计算项目相似度
        user_items = set(liked_items)
        scores = {}

        for item_id in self.items:
            if item_id not in user_items:
                # 计算与用户喜欢项目的平均相似度
                similarities = []
                for liked_item in liked_items:
                    if liked_item in self.items:
                        sim = self._calculate_content_similarity(item_id, liked_item)
                        similarities.append(sim)

                if similarities:
                    avg_similarity = np.mean(similarities)
                    if avg_similarity > 0.1:  # 相似度阈值
                        scores[item_id] = avg_similarity

        # 生成推荐
        recommendations = []
        for item_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]:
            item = self.items[item_id]

            recommendations.append(Recommendation(
                item_id=item_id,
                item_type=item.item_type,
                score=score * 5,  # 放大到5分制
                reason=f"与您喜欢的{self.items[liked_items[0]].title}相似",
                confidence=score,
                metadata={"content_similarity": score}
            ))

        return recommendations

    async def context_aware_recommend(self, user_id: str, context: Dict[str, Any], n: int = 10) -> List[Recommendation]:
        """上下文感知推荐"""
        # 从上下文中提取信息
        time_of_day = context.get('time_of_day', datetime.now().hour)
        device_type = context.get('device_type', 'desktop')
        user_location = context.get('location', 'unknown')

        # 基于时间的推荐策略
        if 6 <= time_of_day <= 9:  # 早晨
            # 推荐工作相关的内容
            preferred_categories = ['productivity', 'analysis', 'automation']
        elif 10 <= time_of_day <= 17:  # 工作时间
            preferred_categories = ['development', 'api', 'integration']
        elif 18 <= time_of_day <= 22:  # 晚上
            preferred_categories = ['learning', 'experiment', 'creative']
        else:  # 深夜
            preferred_categories = ['automation', 'monitoring', 'maintenance']

        # 筛选符合上下文的项目
        candidate_items = []
        for item_id, item in self.items.items():
            score = 1.0

            # 类别匹配
            if item.category in preferred_categories:
                score += 2.0

            # 设备类型适配
            if device_type == 'mobile' and item.features.get('mobile_friendly', False):
                score += 1.0
            elif device_type == 'desktop' and item.features.get('desktop_optimized', False):
                score += 1.0

            # 地区相关（如果有的话）
            if user_location != 'unknown' and item.features.get('region') == user_location:
                score += 1.0

            # 热门度加权
            score += item.popularity_score * 0.5

            candidate_items.append((item_id, score))

        # 排序并生成推荐
        candidate_items.sort(key=lambda x: x[1], reverse=True)

        recommendations = []
        for item_id, score in candidate_items[:n]:
            item = self.items[item_id]

            recommendations.append(Recommendation(
                item_id=item_id,
                item_type=item.item_type,
                score=score,
                reason=f"根据当前时间和使用场景推荐",
                confidence=min(score / 5.0, 1.0),
                metadata={"context_score": score, "context": context}
            ))

        return recommendations

    async def popular_items_recommend(self, n: int = 10) -> List[Recommendation]:
        """热门项目推荐"""
        # 计算热门分数（使用次数 + 评分 + 时间衰减）
        scored_items = []
        current_time = datetime.now()

        for item_id, item in self.items.items():
            # 基础分数：使用次数
            score = item.usage_count

            # 评分加权
            if item.rating_count > 0:
                score += item.rating_avg * item.rating_count * 0.1

            # 时间衰减（最近使用的项目权重更高）
            recent_usage = 0
            if item_id in self.user_behaviors:
                for user_id, behaviors in self.user_behaviors.items():
                    for behavior in behaviors:
                        if behavior.item_id == item_id and behavior.timestamp:
                            days_ago = (current_time - behavior.timestamp).days
                            recent_usage += max(0, 1 - days_ago / 7)  # 一周内的使用

            score += recent_usage * 0.5

            scored_items.append((item_id, score))

        # 排序
        scored_items.sort(key=lambda x: x[1], reverse=True)

        # 生成推荐
        recommendations = []
        for item_id, score in scored_items[:n]:
            item = self.items[item_id]

            recommendations.append(Recommendation(
                item_id=item_id,
                item_type=item.item_type,
                score=min(score / 10, 5.0),  # 归一化到5分制
                reason="热门推荐",
                confidence=0.8,
                metadata={"popularity_score": score}
            ))

        return recommendations

    async def hybrid_recommend(self, user_id: str, context: Optional[Dict[str, Any]] = None, n: int = 10) -> List[Recommendation]:
        """混合推荐策略"""
        # 获取不同类型的推荐
        collaborative_recs = await self.collaborative_filtering_recommend(user_id, n)
        content_recs = await self.content_based_recommend(user_id, n)

        if context:
            context_recs = await self.context_aware_recommend(user_id, context, n)
        else:
            context_recs = await self.popular_items_recommend(n)

        # 合并推荐结果
        all_recommendations = {}

        # 协同过滤权重：0.4
        for rec in collaborative_recs:
            all_recommendations[rec.item_id] = {
                'item_type': rec.item_type,
                'score': rec.score * 0.4,
                'reasons': [rec.reason],
                'confidence': rec.confidence,
                'metadata': rec.metadata
            }

        # 内容推荐权重：0.4
        for rec in content_recs:
            if rec.item_id in all_recommendations:
                all_recommendations[rec.item_id]['score'] += rec.score * 0.4
                all_recommendations[rec.item_id]['reasons'].append(rec.reason)
            else:
                all_recommendations[rec.item_id] = {
                    'item_type': rec.item_type,
                    'score': rec.score * 0.4,
                    'reasons': [rec.reason],
                    'confidence': rec.confidence,
                    'metadata': rec.metadata
                }

        # 上下文推荐权重：0.2
        for rec in context_recs:
            if rec.item_id in all_recommendations:
                all_recommendations[rec.item_id]['score'] += rec.score * 0.2
                all_recommendations[rec.item_id]['reasons'].append(rec.reason)
            else:
                all_recommendations[rec.item_id] = {
                    'item_type': rec.item_type,
                    'score': rec.score * 0.2,
                    'reasons': [rec.reason],
                    'confidence': rec.confidence,
                    'metadata': rec.metadata
                }

        # 生成最终推荐
        final_recommendations = []
        for item_id, data in sorted(all_recommendations.items(), key=lambda x: x[1]['score'], reverse=True)[:n]:
            if item_id in self.items:
                item = self.items[item_id]

                final_recommendations.append(Recommendation(
                    item_id=item_id,
                    item_type=data['item_type'],
                    score=data['score'],
                    reason="; ".join(data['reasons'][:2]),  # 最多显示2个原因
                    confidence=data['confidence'],
                    metadata=data['metadata']
                ))

        return final_recommendations

    async def get_recommendations(self, user_id: str, rec_type: RecommendationType = RecommendationType.HYBRID,
                                 context: Optional[Dict[str, Any]] = None, n: int = 10) -> List[Recommendation]:
        """获取推荐"""
        # 检查缓存
        cache_key = f"{user_id}_{rec_type}_{n}"
        if cache_key in self.recommendation_cache and rec_type != RecommendationType.CONTEXT_AWARE:
            return self.recommendation_cache[cache_key]

        # 根据类型获取推荐
        if rec_type == RecommendationType.COLLABORATIVE:
            recommendations = await self.collaborative_filtering_recommend(user_id, n)
        elif rec_type == RecommendationType.CONTENT_BASED:
            recommendations = await self.content_based_recommend(user_id, n)
        elif rec_type == RecommendationType.CONTEXT_AWARE:
            recommendations = await self.context_aware_recommend(user_id, context or {}, n)
        elif rec_type == RecommendationType.POPULAR:
            recommendations = await self.popular_items_recommend(n)
        else:  # HYBRID
            recommendations = await self.hybrid_recommend(user_id, context, n)

        # 缓存结果（非上下文推荐）
        if rec_type != RecommendationType.CONTEXT_AWARE:
            self.recommendation_cache[cache_key] = recommendations

        return recommendations


# 全局推荐引擎实例
recommendation_engine = RecommendationEngine()