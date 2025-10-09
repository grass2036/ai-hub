'use client';

import { useState, useEffect } from 'react';

interface AIModel {
  id: string;
  name: string;
  provider: string;
  description: string;
  capabilities: string[];
  pricing: {
    input: string;
    output: string;
  };
  speed: 'fast' | 'medium' | 'slow';
  quality: 'basic' | 'standard' | 'premium';
  isFree?: boolean;
  maxTokens?: number;
  contextWindow?: number;
}

interface ModelSelectorProps {
  selectedModel: string;
  onModelChange: (modelId: string) => void;
  className?: string;
}

export default function ModelSelector({ selectedModel, onModelChange, className = '' }: ModelSelectorProps) {
  const [models, setModels] = useState<AIModel[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterProvider, setFilterProvider] = useState<string>('all');
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    // 模拟加载可用模型
    const availableModels: AIModel[] = [
      {
        id: 'gpt-4-turbo',
        name: 'GPT-4 Turbo',
        provider: 'OpenAI',
        description: '最新的GPT-4模型，性能强劲，适合复杂任务',
        capabilities: ['对话', '代码生成', '推理', '多语言'],
        pricing: { input: '$0.01', output: '$0.03' },
        speed: 'medium',
        quality: 'premium',
        maxTokens: 128000,
        contextWindow: 128000
      },
      {
        id: 'gpt-3.5-turbo',
        name: 'GPT-3.5 Turbo',
        provider: 'OpenAI',
        description: '快速、经济的模型，适合日常对话和简单任务',
        capabilities: ['对话', '代码生成', '文本生成'],
        pricing: { input: '$0.001', output: '$0.002' },
        speed: 'fast',
        quality: 'standard',
        maxTokens: 4096,
        contextWindow: 16384
      },
      {
        id: 'claude-3-opus',
        name: 'Claude-3 Opus',
        provider: 'Anthropic',
        description: '最强大的Claude模型，擅长复杂推理和分析',
        capabilities: ['对话', '分析', '写作', '编程', '数学'],
        pricing: { input: '$0.015', output: '$0.075' },
        speed: 'medium',
        quality: 'premium',
        maxTokens: 4096,
        contextWindow: 200000
      },
      {
        id: 'claude-3-sonnet',
        name: 'Claude-3 Sonnet',
        provider: 'Anthropic',
        description: '平衡性能和成本的Claude模型',
        capabilities: ['对话', '写作', '分析', '编程'],
        pricing: { input: '$0.003', output: '$0.015' },
        speed: 'fast',
        quality: 'standard',
        maxTokens: 4096,
        contextWindow: 200000
      },
      {
        id: 'gemini-1.5-pro',
        name: 'Gemini 1.5 Pro',
        provider: 'Google',
        description: 'Google最新的多模态大模型，支持超长上下文',
        capabilities: ['对话', '多模态', '长文本', '推理'],
        pricing: { input: '$0.0025', output: '$0.0075' },
        speed: 'medium',
        quality: 'premium',
        maxTokens: 8192,
        contextWindow: 1000000
      },
      {
        id: 'gemini-1.0-pro',
        name: 'Gemini 1.0 Pro',
        provider: 'Google',
        description: '稳定的Google模型，适合一般任务',
        capabilities: ['对话', '文本生成', '翻译'],
        pricing: { input: '$0.0005', output: '$0.0015' },
        speed: 'fast',
        quality: 'standard',
        maxTokens: 30720,
        contextWindow: 32768
      },
      {
        id: 'grok-4-fast',
        name: 'Grok-4 Fast',
        provider: 'xAI',
        description: '快速响应的Grok模型，免费使用',
        capabilities: ['对话', '实时信息', '分析'],
        pricing: { input: 'Free', output: 'Free' },
        speed: 'fast',
        quality: 'standard',
        isFree: true,
        maxTokens: 8192,
        contextWindow: 8192
      },
      {
        id: 'deepseek-chat-v3.1',
        name: 'DeepSeek Chat v3.1',
        provider: 'DeepSeek',
        description: '高性能中文模型，免费使用',
        capabilities: ['对话', '中文处理', '编程', '推理'],
        pricing: { input: 'Free', output: 'Free' },
        speed: 'fast',
        quality: 'standard',
        isFree: true,
        maxTokens: 4096,
        contextWindow: 32768
      }
    ];

    setModels(availableModels);
  }, []);

  const filteredModels = models.filter(model => {
    const matchesSearch = model.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         model.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         model.capabilities.some(cap => cap.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesProvider = filterProvider === 'all' || model.provider === filterProvider;
    return matchesSearch && matchesProvider;
  });

  const getSpeedColor = (speed: string) => {
    switch (speed) {
      case 'fast': return 'text-green-600 bg-green-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'slow': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'premium': return 'text-purple-600 bg-purple-100';
      case 'standard': return 'text-blue-600 bg-blue-100';
      case 'basic': return 'text-gray-600 bg-gray-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getProviderColor = (provider: string) => {
    const colors: Record<string, string> = {
      'OpenAI': 'bg-green-500',
      'Anthropic': 'bg-orange-500',
      'Google': 'bg-blue-500',
      'xAI': 'bg-red-500',
      'DeepSeek': 'bg-purple-500'
    };
    return colors[provider] || 'bg-gray-500';
  };

  const selectedModelData = models.find(m => m.id === selectedModel);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 当前选择的模型 */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {selectedModelData && (
              <>
                <div className={`w-3 h-3 rounded-full ${getProviderColor(selectedModelData.provider)}`}></div>
                <div>
                  <h3 className="font-semibold text-gray-900">{selectedModelData.name}</h3>
                  <p className="text-sm text-gray-600">{selectedModelData.provider}</p>
                </div>
              </>
            )}
          </div>
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-blue-600 hover:text-blue-800 text-sm"
          >
            {showDetails ? '收起' : '更换模型'}
          </button>
        </div>
      </div>

      {/* 模型选择面板 */}
      {showDetails && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-lg">
          {/* 搜索和筛选 */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="flex-1 relative">
                <input
                  type="text"
                  placeholder="搜索模型..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <svg className="w-5 h-5 text-gray-400 absolute left-3 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <select
                value={filterProvider}
                onChange={(e) => setFilterProvider(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">所有提供商</option>
                <option value="OpenAI">OpenAI</option>
                <option value="Anthropic">Anthropic</option>
                <option value="Google">Google</option>
                <option value="xAI">xAI</option>
                <option value="DeepSeek">DeepSeek</option>
              </select>
            </div>
          </div>

          {/* 模型列表 */}
          <div className="max-h-96 overflow-y-auto">
            <div className="grid grid-cols-1 gap-3 p-4">
              {filteredModels.map((model) => (
                <div
                  key={model.id}
                  onClick={() => {
                    onModelChange(model.id);
                    setShowDetails(false);
                  }}
                  className={`border rounded-lg p-4 cursor-pointer transition-all hover:shadow-md ${
                    selectedModel === model.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <div className={`w-2 h-2 rounded-full ${getProviderColor(model.provider)}`}></div>
                        <h4 className="font-semibold text-gray-900">{model.name}</h4>
                        {model.isFree && (
                          <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">免费</span>
                        )}
                        <span className={`px-2 py-1 text-xs rounded-full ${getSpeedColor(model.speed)}`}>
                          {model.speed === 'fast' ? '快速' : model.speed === 'medium' ? '中等' : '慢速'}
                        </span>
                        <span className={`px-2 py-1 text-xs rounded-full ${getQualityColor(model.quality)}`}>
                          {model.quality === 'premium' ? '高级' : model.quality === 'standard' ? '标准' : '基础'}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{model.description}</p>
                      <div className="flex flex-wrap gap-1 mb-2">
                        {model.capabilities.slice(0, 3).map((capability, index) => (
                          <span key={index} className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                            {capability}
                          </span>
                        ))}
                        {model.capabilities.length > 3 && (
                          <span className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                            +{model.capabilities.length - 3}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <span>定价: {model.pricing.input}/{model.pricing.output}</span>
                        <span>上下文: {(model.contextWindow || 0).toLocaleString()}</span>
                      </div>
                    </div>
                    {selectedModel === model.id && (
                      <div className="ml-3">
                        <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 提示信息 */}
          <div className="p-4 bg-gray-50 border-t border-gray-200">
            <div className="flex items-start space-x-2">
              <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="text-sm text-gray-600">
                <p>💡 提示：不同模型适用于不同任务。免费模型适合日常使用，付费模型性能更强。</p>
                <p>切换模型可能会影响对话的连贯性，建议在同一对话中保持使用相同模型。</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}