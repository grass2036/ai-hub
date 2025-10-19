"""
内容增强功能
Week 5 Day 4: 高级AI功能 - 内容增强
"""

import asyncio
import re
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import logging

from backend.ai.model_manager import model_manager, TaskType
from backend.core.cache.smart_cache import cache_ai_response, get_smart_cache

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """内容类型"""
    TEXT = "text"
    CODE = "code"
    MARKDOWN = "markdown"
    JSON = "json"
    MIXED = "mixed"


class QualityMetric(Enum):
    """质量指标"""
    CLARITY = "clarity"           # 清晰度
    COHERENCE = "coherence"       # 连贯性
    COMPLETENESS = "completeness" # 完整性
    ACCURACY = "accuracy"         # 准确性
    RELEVANCE = "relevance"       # 相关性
    CONCISENESS = "conciseness"   # 简洁性


@dataclass
class QualityScore:
    """质量评分"""
    overall_score: float
    metrics: Dict[QualityMetric, float]
    issues: List[str]
    suggestions: List[str]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "metrics": {metric.value: score for metric, score in self.metrics.items()},
            "issues": self.issues,
            "suggestions": self.suggestions,
            "confidence": self.confidence
        }


@dataclass
class ContentSummary:
    """内容摘要"""
    short_summary: str
    detailed_summary: str
    key_points: List[str]
    topics: List[str]
    sentiment: str
    word_count: int
    reading_time_minutes: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "short_summary": self.short_summary,
            "detailed_summary": self.detailed_summary,
            "key_points": self.key_points,
            "topics": self.topics,
            "sentiment": self.sentiment,
            "word_count": self.word_count,
            "reading_time_minutes": self.reading_time_minutes
        }


@dataclass
class ContentEnhancement:
    """内容增强结果"""
    original_content: str
    enhanced_content: str
    improvements: List[str]
    quality_score: QualityScore
    summary: Optional[ContentSummary] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "original_content": self.original_content,
            "enhanced_content": self.enhanced_content,
            "improvements": self.improvements,
            "quality_score": self.quality_score.to_dict(),
            "metadata": self.metadata
        }
        if self.summary:
            result["summary"] = self.summary.to_dict()
        return result


class ContentAnalyzer:
    """内容分析器"""

    def __init__(self):
        self.quality_patterns = {
            QualityMetric.CLARITY: [
                r"模糊|不清楚|不明确",
                r"重复|啰嗦|冗余",
                r"复杂|难以理解"
            ],
            QualityMetric.COHERENCE: [
                r"然而|但是|不过.*然而|但是|不过",
                r"首先.*最后.*首先",
                r"因为.*所以.*因为"
            ],
            QualityMetric.COMPLETENESS: [
                r"等等|之类的|之类",
                r"待补充|TODO|FIXME",
                r"不完整|缺少"
            ]
        }

    async def analyze_quality(self, content: str, content_type: ContentType = ContentType.TEXT) -> QualityScore:
        """分析内容质量"""
        try:
            # 获取模型进行质量分析
            manager = await model_manager
            model_id = await manager.get_best_model(TaskType.ANALYSIS)

            if not model_id:
                return self._fallback_quality_analysis(content)

            # 构建分析提示
            analysis_prompt = self._build_quality_analysis_prompt(content, content_type)

            # 调用AI分析
            from backend.core.ai_service import ai_manager
            service = await ai_manager.get_service("openrouter")
            response = await service.generate_response(analysis_prompt, model=model_id)

            # 解析AI响应
            return self._parse_quality_response(response, content)

        except Exception as e:
            logger.error(f"AI quality analysis failed: {e}")
            return self._fallback_quality_analysis(content)

    def _build_quality_analysis_prompt(self, content: str, content_type: ContentType) -> str:
        """构建质量分析提示"""
        return f"""
请分析以下{content_type.value}内容的质量，并提供JSON格式的评估：

内容：
{content[:2000]}  # 限制长度

请评估以下维度并返回JSON格式：
{{
    "overall_score": 0.0-1.0,
    "metrics": {{
        "clarity": 0.0-1.0,      # 清晰度
        "coherence": 0.0-1.0,    # 连贯性
        "completeness": 0.0-1.0,  # 完整性
        "accuracy": 0.0-1.0,      # 准确性
        "relevance": 0.0-1.0,     # 相关性
        "conciseness": 0.0-1.0    # 简洁性
    }},
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"],
    "confidence": 0.0-1.0
}}

请只返回JSON，不要包含其他内容。
"""

    def _parse_quality_response(self, response: str, content: str) -> QualityScore:
        """解析AI质量分析响应"""
        try:
            # 提取JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                metrics = {}
                for metric_name, score in data.get('metrics', {}).items():
                    try:
                        metric = QualityMetric(metric_name)
                        metrics[metric] = float(score)
                    except ValueError:
                        continue

                return QualityScore(
                    overall_score=float(data.get('overall_score', 0.5)),
                    metrics=metrics,
                    issues=data.get('issues', []),
                    suggestions=data.get('suggestions', []),
                    confidence=float(data.get('confidence', 0.5))
                )
        except Exception as e:
            logger.error(f"Failed to parse quality response: {e}")

        return self._fallback_quality_analysis(content)

    def _fallback_quality_analysis(self, content: str) -> QualityScore:
        """备用质量分析"""
        metrics = {}
        issues = []
        suggestions = []

        # 基础文本分析
        word_count = len(content.split())
        sentence_count = len(re.split(r'[.!?。！？]', content))
        avg_sentence_length = word_count / max(sentence_count, 1)

        # 清晰度分析
        if avg_sentence_length > 30:
            metrics[QualityMetric.CLARITY] = 0.3
            issues.append("句子过长，影响可读性")
            suggestions.append("建议拆分长句子")
        elif avg_sentence_length < 10:
            metrics[QualityMetric.CLARITY] = 0.6
            issues.append("句子过短，可能缺乏连贯性")
            suggestions.append("建议合并相关短句")
        else:
            metrics[QualityMetric.CLARITY] = 0.8

        # 完整性分析
        if content.endswith(('...', '等等', '待续')):
            metrics[QualityMetric.COMPLETENESS] = 0.4
            issues.append("内容似乎不完整")
            suggestions.append("请确保内容完整")
        else:
            metrics[QualityMetric.COMPLETENESS] = 0.8

        # 连贯性分析
        transition_words = ['然而', '但是', '因此', '所以', '首先', '其次', '最后']
        transition_count = sum(1 for word in transition_words if word in content)
        metrics[QualityMetric.COHERENCE] = min(0.9, 0.5 + transition_count * 0.1)

        # 其他指标默认值
        metrics[QualityMetric.ACCURACY] = 0.7
        metrics[QualityMetric.RELEVANCE] = 0.7
        metrics[QualityMetric.CONCISENESS] = 0.6

        overall_score = sum(metrics.values()) / len(metrics)

        return QualityScore(
            overall_score=overall_score,
            metrics=metrics,
            issues=issues,
            suggestions=suggestions,
            confidence=0.6
        )


class ContentSummarizer:
    """内容摘要器"""

    def __init__(self):
        pass

    @cache_ai_response(ttl=1800)  # 30分钟缓存
    async def generate_summary(
        self,
        content: str,
        max_length: int = 200,
        detail_level: str = "medium"  # short, medium, detailed
    ) -> ContentSummary:
        """生成内容摘要"""
        try:
            manager = await model_manager
            model_id = await manager.get_best_model(TaskType.SUMMARIZATION)

            if not model_id:
                return self._fallback_summary(content, max_length)

            # 构建摘要提示
            summary_prompt = self._build_summary_prompt(content, max_length, detail_level)

            # 调用AI生成摘要
            from backend.core.ai_service import ai_manager
            service = await ai_manager.get_service("openrouter")
            response = await service.generate_response(summary_prompt, model=model_id)

            # 解析摘要响应
            return self._parse_summary_response(response, content)

        except Exception as e:
            logger.error(f"AI summarization failed: {e}")
            return self._fallback_summary(content, max_length)

    def _build_summary_prompt(self, content: str, max_length: int, detail_level: str) -> str:
        """构建摘要提示"""
        level_instructions = {
            "short": "生成一个简短的摘要（50字以内）",
            "medium": "生成一个中等长度的摘要（100-200字）",
            "detailed": "生成一个详细的摘要（200-300字），包含关键要点"
        }

        return f"""
请为以下内容生成摘要，要求：{level_instructions.get(detail_level, "生成一个中等长度的摘要")}

内容：
{content[:3000]}

请以JSON格式返回：
{{
    "short_summary": "一句话摘要",
    "detailed_summary": "详细摘要内容",
    "key_points": ["要点1", "要点2", "要点3"],
    "topics": ["主题1", "主题2"],
    "sentiment": "positive/negative/neutral"
}}

请只返回JSON，不要包含其他内容。
"""

    def _parse_summary_response(self, response: str, original_content: str) -> ContentSummary:
        """解析摘要响应"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                # 计算阅读时间（假设每分钟200字）
                word_count = len(original_content.split())
                reading_time = max(1, word_count // 200)

                return ContentSummary(
                    short_summary=data.get('short_summary', ''),
                    detailed_summary=data.get('detailed_summary', ''),
                    key_points=data.get('key_points', []),
                    topics=data.get('topics', []),
                    sentiment=data.get('sentiment', 'neutral'),
                    word_count=word_count,
                    reading_time_minutes=reading_time
                )
        except Exception as e:
            logger.error(f"Failed to parse summary response: {e}")

        return self._fallback_summary(original_content)

    def _fallback_summary(self, content: str, max_length: int = 200) -> ContentSummary:
        """备用摘要生成"""
        # 简单的抽取式摘要
        sentences = re.split(r'[.!?。！？]', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        # 选择前几个句子作为摘要
        summary_sentences = []
        current_length = 0

        for sentence in sentences:
            if current_length + len(sentence) <= max_length:
                summary_sentences.append(sentence)
                current_length += len(sentence)
            else:
                break

        short_summary = summary_sentences[0] if summary_sentences else content[:100]
        detailed_summary = ' '.join(summary_sentences)

        word_count = len(content.split())
        reading_time = max(1, word_count // 200)

        return ContentSummary(
            short_summary=short_summary,
            detailed_summary=detailed_summary,
            key_points=summary_sentences[:3],
            topics=[],  # 需要更复杂的主题提取
            sentiment='neutral',
            word_count=word_count,
            reading_time_minutes=reading_time
        )


class ContentEnhancer:
    """内容增强器"""

    def __init__(self):
        self.analyzer = ContentAnalyzer()
        self.summarizer = ContentSummarizer()

    async def enhance_content(
        self,
        content: str,
        enhancement_type: str = "quality",  # quality, clarity, completeness, conciseness
        target_length: Optional[int] = None,
        style: Optional[str] = None  # formal, casual, professional, academic
    ) -> ContentEnhancement:
        """增强内容"""
        try:
            # 分析原始内容质量
            content_type = self._detect_content_type(content)
            quality_score = await self.analyzer.analyze_quality(content, content_type)

            # 生成增强内容
            enhanced_content = await self._generate_enhanced_content(
                content, enhancement_type, quality_score, target_length, style
            )

            # 分析增强后质量
            enhanced_quality = await self.analyzer.analyze_quality(enhanced_content, content_type)

            # 生成摘要
            summary = await self.summarizer.generate_summary(enhanced_content)

            # 计算改进点
            improvements = self._calculate_improvements(quality_score, enhanced_quality)

            return ContentEnhancement(
                original_content=content,
                enhanced_content=enhanced_content,
                improvements=improvements,
                quality_score=enhanced_quality,
                summary=summary,
                metadata={
                    "enhancement_type": enhancement_type,
                    "content_type": content_type.value,
                    "original_quality": quality_score.overall_score,
                    "enhanced_quality": enhanced_quality.overall_score,
                    "quality_improvement": enhanced_quality.overall_score - quality_score.overall_score
                }
            )

        except Exception as e:
            logger.error(f"Content enhancement failed: {e}")
            return ContentEnhancement(
                original_content=content,
                enhanced_content=content,
                improvements=[],
                quality_score=await self.analyzer.analyze_quality(content)
            )

    def _detect_content_type(self, content: str) -> ContentType:
        """检测内容类型"""
        # 代码检测
        if re.search(r'```[\s\S]*```|def |function |class |import |#include', content):
            return ContentType.CODE

        # JSON检测
        if content.strip().startswith('{') and content.strip().endswith('}'):
            try:
                json.loads(content)
                return ContentType.JSON
            except:
                pass

        # Markdown检测
        if re.search(r'#{1,6}\s|*\s|[-]\s|\[.*\]\(.*\)', content):
            return ContentType.MARKDOWN

        return ContentType.TEXT

    async def _generate_enhanced_content(
        self,
        content: str,
        enhancement_type: str,
        quality_score: QualityScore,
        target_length: Optional[int],
        style: Optional[str]
    ) -> str:
        """生成增强内容"""
        try:
            manager = await model_manager
            model_id = await manager.get_best_model(TaskType.CREATIVE)

            if not model_id:
                return self._fallback_enhancement(content, enhancement_type)

            # 构建增强提示
            enhancement_prompt = self._build_enhancement_prompt(
                content, enhancement_type, quality_score, target_length, style
            )

            # 调用AI增强
            from backend.core.ai_service import ai_manager
            service = await ai_manager.get_service("openrouter")
            response = await service.generate_response(enhancement_prompt, model=model_id)

            # 提取增强内容
            return self._extract_enhanced_content(response)

        except Exception as e:
            logger.error(f"AI content enhancement failed: {e}")
            return self._fallback_enhancement(content, enhancement_type)

    def _build_enhancement_prompt(
        self,
        content: str,
        enhancement_type: str,
        quality_score: QualityScore,
        target_length: Optional[int],
        style: Optional[str]
    ) -> str:
        """构建增强提示"""
        enhancement_instructions = {
            "quality": "请提升内容整体质量，包括清晰度、连贯性和准确性",
            "clarity": "请提升内容的清晰度，使表达更加清楚易懂",
            "completeness": "请补充内容，使其更加完整和全面",
            "conciseness": "请精简内容，去除冗余，保持核心信息"
        }

        style_instructions = {
            "formal": "请使用正式的商务语言风格",
            "casual": "请使用轻松随意的语言风格",
            "professional": "请使用专业的技术语言风格",
            "academic": "请使用学术性的严谨语言风格"
        }

        instruction = enhancement_instructions.get(enhancement_type, enhancement_instructions["quality"])
        style_instruction = style_instructions.get(style, "") if style else ""

        length_instruction = f"目标长度：{target_length}字" if target_length else ""

        prompt = f"""
请根据以下要求增强内容：

原始内容：
{content}

质量评估：
- 总体评分：{quality_score.overall_score:.2f}
- 主要问题：{', '.join(quality_score.issues[:3])}

增强要求：
{instruction}
{style_instruction}
{length_instruction}

请直接返回增强后的内容，不要包含解释或说明。
"""

        return prompt

    def _extract_enhanced_content(self, response: str) -> str:
        """提取增强内容"""
        # 清理响应，移除可能的解释
        lines = response.split('\n')
        content_lines = []
        skip_explanations = False

        for line in lines:
            line = line.strip()
            if line.startswith(('增强后', '以下是', 'Here is', 'Enhanced')):
                skip_explanations = True
                continue
            if skip_explanations and not line:
                skip_explanations = False
                continue
            if not skip_explanations and line:
                content_lines.append(line)

        return '\n'.join(content_lines) if content_lines else response.strip()

    def _fallback_enhancement(self, content: str, enhancement_type: str) -> str:
        """备用内容增强"""
        if enhancement_type == "clarity":
            # 简单的清晰度改进
            sentences = re.split(r'[.!?。！？]', content)
            improved_sentences = []

            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    # 移除重复词语
                    words = sentence.split()
                    filtered_words = []
                    last_word = None
                    for word in words:
                        if word != last_word:
                            filtered_words.append(word)
                        last_word = word
                    improved_sentences.append(' '.join(filtered_words))

            return '。'.join(improved_sentences)

        elif enhancement_type == "conciseness":
            # 简单的精简
            # 移除常见的冗余词
            redundant_words = ['非常', '十分', '极其', '特别', '相当', '比较']
            result = content
            for word in redundant_words:
                result = result.replace(word, '')

            return result.strip()

        return content

    def _calculate_improvements(
        self,
        original_quality: QualityScore,
        enhanced_quality: QualityScore
    ) -> List[str]:
        """计算改进点"""
        improvements = []

        # 整体质量改进
        overall_improvement = enhanced_quality.overall_score - original_quality.overall_score
        if overall_improvement > 0.1:
            improvements.append(f"整体质量提升 {overall_improvement:.1%}")

        # 各项指标改进
        for metric in QualityMetric:
            original_score = original_quality.metrics.get(metric, 0)
            enhanced_score = enhanced_quality.metrics.get(metric, 0)
            improvement = enhanced_score - original_score

            if improvement > 0.1:
                metric_names = {
                    QualityMetric.CLARITY: "清晰度",
                    QualityMetric.COHERENCE: "连贯性",
                    QualityMetric.COMPLETENESS: "完整性",
                    QualityMetric.ACCURACY: "准确性",
                    QualityMetric.RELEVANCE: "相关性",
                    QualityMetric.CONCISENESS: "简洁性"
                }
                improvements.append(f"{metric_names[metric]}提升 {improvement:.1%}")

        # 问题解决情况
        resolved_issues = set(original_quality.issues) - set(enhanced_quality.issues)
        if resolved_issues:
            improvements.append(f"解决了 {len(resolved_issues)} 个问题")

        return improvements if improvements else ["内容已优化"]


# 全局内容增强器实例
content_enhancer = ContentEnhancer()


async def get_content_enhancer() -> ContentEnhancer:
    """获取内容增强器实例"""
    return content_enhancer


# 内容增强装饰器
def enhance_response(
    enhancement_type: str = "quality",
    target_length: Optional[int] = None,
    style: Optional[str] = None
):
    """内容增强装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 获取原始响应
            original_response = await func(*args, **kwargs)

            try:
                # 提取文本内容
                if isinstance(original_response, dict):
                    content = original_response.get('content', '') or original_response.get('response', '')
                elif isinstance(original_response, str):
                    content = original_response
                else:
                    content = str(original_response)

                if not content or len(content) < 50:
                    return original_response

                # 增强内容
                enhancer = await get_content_enhancer()
                enhancement = await enhancer.enhance_content(
                    content, enhancement_type, target_length, style
                )

                # 返回增强后的响应
                if isinstance(original_response, dict):
                    enhanced_response = original_response.copy()
                    enhanced_response['content'] = enhancement.enhanced_content
                    enhanced_response['enhancement'] = enhancement.to_dict()
                    return enhanced_response
                else:
                    return enhancement.enhanced_content

            except Exception as e:
                logger.error(f"Response enhancement failed: {e}")
                return original_response

        return wrapper
    return decorator