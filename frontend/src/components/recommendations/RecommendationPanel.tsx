'use client';

import { useState, useEffect } from 'react';
import {
  FadeIn,
  SlideIn,
  StaggeredList,
  LoadingState,
  Notification
} from '@/components/ui/Animations';

interface RecommendationItem {
  item_id: string;
  item_type: string;
  score: number;
  reason: string;
  confidence: float;
  metadata: Record<string, any>;
  item_details?: {
    title: string;
    description: string;
    category: string;
    tags: string[];
    popularity_score: number;
    rating_avg: number;
    rating_count: number;
  };
}

interface RecommendationPanelProps {
  userId: string;
  className?: string;
}

export default function RecommendationPanel({ userId, className = '' }: RecommendationPanelProps) {
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [recType, setRecType] = useState<string>('hybrid');
  const [context, setContext] = useState<Record<string, any>>({});
  const [notification, setNotification] = useState<{
    show: boolean;
    message: string;
    type: 'success' | 'error' | 'warning' | 'info';
  }>({ show: false, message: '', type: 'info' });

  const recommendationTypes = [
    { value: 'hybrid', label: '智能推荐', description: '综合多种算法的个性化推荐' },
    { value: 'collaborative', label: '协同过滤', description: '基于相似用户的推荐' },
    { value: 'content_based', label: '内容推荐', description: '基于项目特征的推荐' },
    { value: 'context_aware', label: '场景推荐', description: '基于当前场景的推荐' },
    { value: 'popular', label: '热门推荐', description: '最受欢迎的项目' }
  ];

  useEffect(() => {
    // 自动检测上下文
    const detectedContext = {
      time_of_day: new Date().getHours(),
      device_type: /Mobile|Android|iPhone|iPad/.test(navigator.userAgent) ? 'mobile' : 'desktop',
      user_agent: navigator.userAgent,
      referrer: document.referrer,
      screen_resolution: `${window.screen.width}x${window.screen.height}`
    };
    setContext(detectedContext);
  }, []);

  useEffect(() => {
    fetchRecommendations();
  }, [userId, recType, context]);

  const fetchRecommendations = async () => {
    try {
      setLoading(true);

      const response = await fetch('/api/v1/recommendations/recommendations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          user_id: userId,
          rec_type: recType,
          n: 10,
          context: context,
          filters: {}
        })
      });

      if (!response.ok) {
        throw new Error('Failed to fetch recommendations');
      }

      const data = await response.json();
      setRecommendations(data.recommendations);
    } catch (error) {
      console.error('Error fetching recommendations:', error);
      showNotification('获取推荐失败', 'error');
    } finally {
      setLoading(false);
    }
  };

  const showNotification = (message: string, type: 'success' | 'error' | 'warning' | 'info') => {
    setNotification({ show: true, message, type });
    setTimeout(() => setNotification(prev => ({ ...prev, show: false })), 3000);
  };

  const handleItemClick = async (item: RecommendationItem) => {
    try {
      // 记录点击行为
      await fetch('/api/v1/recommendations/behavior', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          user_id: userId,
          item_id: item.item_id,
          item_type: item.item_type,
          action: 'click',
          metadata: { recommendation_score: item.score, reason: item.reason }
        })
      });

      showNotification('已记录您的选择', 'success');
    } catch (error) {
      console.error('Error recording behavior:', error);
    }
  };

  const handleFeedback = async (item: RecommendationItem, feedbackType: string) => {
    try {
      await fetch('/api/v1/recommendations/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          user_id: userId,
          item_id: item.item_id,
          feedback_type: feedbackType
        })
      });

      showNotification('感谢您的反馈', 'success');

      // 重新获取推荐
      fetchRecommendations();
    } catch (error) {
      console.error('Error recording feedback:', error);
      showNotification('反馈失败', 'error');
    }
  };

  const getItemIcon = (itemType: string) => {
    const icons = {
      'ai_model': '🤖',
      'api_endpoint': '🔌',
      'workflow': '⚙️',
      'document': '📄',
      'template': '📋'
    };
    return icons[itemType] || '📦';
  };

  const getScoreColor = (score: number) => {
    if (score >= 4.0) return 'text-green-600';
    if (score >= 3.0) return 'text-blue-600';
    if (score >= 2.0) return 'text-yellow-600';
    return 'text-gray-600';
  };

  if (loading) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 ${className}`}>
        <LoadingState message="获取个性化推荐中..." />
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 ${className}`}>
      <Notification
        isVisible={notification.show}
        onClose={() => setNotification(prev => ({ ...prev, show: false }))}
        type={notification.type}
      >
        {notification.message}
      </Notification>

      {/* 标题和控制栏 */}
      <FadeIn>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">个性化推荐</h2>
            <p className="text-sm text-gray-600 mt-1">基于您的使用习惯和偏好为您推荐</p>
          </div>
          <button
            onClick={fetchRecommendations}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            刷新推荐
          </button>
        </div>
      </FadeIn>

      {/* 推荐类型选择 */}
      <FadeIn delay={100}>
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-3">推荐算法</label>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {recommendationTypes.map((type) => (
              <button
                key={type.value}
                onClick={() => setRecType(type.value)}
                className={`p-3 rounded-lg border-2 transition-all text-left ${
                  recType === type.value
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="font-medium text-sm text-gray-900">{type.label}</div>
                <div className="text-xs text-gray-500 mt-1">{type.description}</div>
              </button>
            ))}
          </div>
        </div>
      </FadeIn>

      {/* 推荐列表 */}
      {recommendations.length > 0 ? (
        <StaggeredList staggerDelay={100}>
          <div className="space-y-4">
            {recommendations.map((item, index) => (
              <SlideIn key={item.item_id} direction="up" delay={index * 100}>
                <div className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center mb-2">
                        <span className="text-2xl mr-3">{getItemIcon(item.item_type)}</span>
                        <div>
                          <h3 className="font-medium text-gray-900">
                            {item.item_details?.title || item.item_id}
                          </h3>
                          <p className="text-sm text-gray-600">
                            {item.item_details?.category || item.item_type}
                          </p>
                        </div>
                      </div>

                      {item.item_details?.description && (
                        <p className="text-sm text-gray-700 mb-3 line-clamp-2">
                          {item.item_details.description}
                        </p>
                      )}

                      {/* 标签 */}
                      {item.item_details?.tags && item.item_details.tags.length > 0 && (
                        <div className="flex flex-wrap gap-2 mb-3">
                          {item.item_details.tags.slice(0, 3).map((tag, tagIndex) => (
                            <span
                              key={tagIndex}
                              className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* 推荐原因 */}
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm text-gray-600">
                            <span className="font-medium">推荐理由：</span>
                            {item.reason}
                          </p>
                          <div className="flex items-center mt-1 text-xs text-gray-500">
                            <span className={`font-medium ${getScoreColor(item.score)}`}>
                              匹配度: {item.score.toFixed(1)}
                            </span>
                            <span className="mx-2">•</span>
                            <span>置信度: {(item.confidence * 100).toFixed(0)}%</span>
                            {item.item_details?.rating_count > 0 && (
                              <>
                                <span className="mx-2">•</span>
                                <span>
                                  ⭐ {item.item_details.rating_avg.toFixed(1)}
                                  ({item.item_details.rating_count})
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 操作按钮 */}
                    <div className="flex flex-col gap-2 ml-4">
                      <button
                        onClick={() => handleItemClick(item)}
                        className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                      >
                        查看
                      </button>
                      <div className="flex gap-1">
                        <button
                          onClick={() => handleFeedback(item, 'like')}
                          className="p-1 text-gray-400 hover:text-green-600 transition-colors"
                          title="喜欢"
                        >
                          👍
                        </button>
                        <button
                          onClick={() => handleFeedback(item, 'dislike')}
                          className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                          title="不喜欢"
                        >
                          👎
                        </button>
                        <button
                          onClick={() => handleFeedback(item, 'ignore')}
                          className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
                          title="忽略"
                        >
                          🚫
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </SlideIn>
            ))}
          </div>
        </StaggeredList>
      ) : (
        <FadeIn>
          <div className="text-center py-12">
            <div className="text-gray-400 text-4xl mb-4">📝</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">暂无推荐</h3>
            <p className="text-gray-600">
              推荐系统需要更多使用数据来为您生成个性化推荐
            </p>
            <button
              onClick={fetchRecommendations}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              重新获取
            </button>
          </div>
        </FadeIn>
      )}
    </div>
  );
}