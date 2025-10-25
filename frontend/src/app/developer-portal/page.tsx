'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { PageTransition, FadeIn, SlideIn, StaggeredList } from '@/components/ui/Animations';

interface Resource {
  id: string;
  title: string;
  description: string;
  type: 'guide' | 'tutorial' | 'reference' | 'example';
  category: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  tags: string[];
  url: string;
  author: string;
  readTime: string;
  rating: number;
  viewCount: number;
  createdAt: string;
}

interface Plugin {
  id: string;
  name: string;
  description: string;
  author: string;
  version: string;
  downloads: number;
  rating: number;
  tags: string[];
  category: string;
  createdAt: string;
}

export default function DeveloperPortal() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'overview' | 'guides' | 'plugins' | 'community' | 'tools'>('overview');
  const [loading, setLoading] = useState(true);

  // 模拟数据
  const [resources] = useState<Resource[]>([
    {
      id: '1',
      title: 'AI Hub 快速入门指南',
      description: '学习如何快速开始使用AI Hub平台，包括环境配置、基本概念和第一个项目。',
      type: 'guide',
      category: 'getting-started',
      difficulty: 'beginner',
      tags: ['getting-started', 'tutorial', 'quickstart'],
      url: '/docs/getting-started',
      author: 'AI Hub Team',
      readTime: '10分钟',
      rating: 4.8,
      viewCount: 15234,
      createdAt: '2024-01-15'
    },
    {
      id: '2',
      title: '插件开发完整教程',
      description: '从零开始学习如何为AI Hub平台开发插件，包括接口规范、开发工具和最佳实践。',
      type: 'tutorial',
      category: 'plugin-development',
      difficulty: 'intermediate',
      tags: ['plugins', 'development', 'tutorial'],
      url: '/docs/plugin-development',
      author: 'AI Hub Team',
      readTime: '45分钟',
      rating: 4.9,
      viewCount: 8921,
      createdAt: '2024-01-20'
    },
    {
      id: '3',
      title: 'API 参考文档',
      description: '完整的AI Hub API参考文档，包含所有端点的详细说明和示例代码。',
      type: 'reference',
      category: 'api',
      difficulty: 'intermediate',
      tags: ['api', 'reference', 'documentation'],
      url: '/docs/api',
      author: 'AI Hub Team',
      readTime: '2小时',
      rating: 4.7,
      viewCount: 21543,
      createdAt: '2024-01-10'
    },
    {
      id: '4',
      title: '最佳实践指南',
      description: 'AI Hub平台开发最佳实践，包括代码规范、性能优化、安全考虑等。',
      type: 'guide',
      category: 'best-practices',
      difficulty: 'advanced',
      tags: ['best-practices', 'optimization', 'security'],
      url: '/docs/best-practices',
      author: 'AI Hub Team',
      readTime: '30分钟',
      rating: 4.6,
      viewCount: 6789,
      createdAt: '2024-01-25'
    }
  ]);

  const [plugins] = useState<Plugin[]>([
    {
      id: 'utility-plugin',
      name: 'Utility Tools Plugin',
      description: '提供常用工具功能的插件，包括数据处理、格式转换等。',
      author: 'AI Hub Team',
      version: '1.2.0',
      downloads: 5432,
      rating: 4.5,
      tags: ['utility', 'tools', 'data-processing'],
      category: 'utility',
      createdAt: '2024-01-15'
    },
    {
      id: 'enhanced-chat',
      name: 'Enhanced Chat Interface',
      description: '增强的聊天界面插件，提供更丰富的交互体验。',
      author: 'John Doe',
      version: '2.0.1',
      downloads: 3210,
      rating: 4.7,
      tags: ['chat', 'ui', 'enhancement'],
      category: 'ui_component',
      createdAt: '2024-01-20'
    },
    {
      id: 'analytics-pro',
      name: 'Analytics Pro',
      description: '高级分析插件，提供详细的用户行为分析和报表功能。',
      author: 'Jane Smith',
      version: '1.5.0',
      downloads: 1897,
      rating: 4.8,
      tags: ['analytics', 'reporting', 'metrics'],
      category: 'analytics',
      createdAt: '2024-01-25'
    }
  ]);

  useEffect(() => {
    setTimeout(() => setLoading(false), 500);
  }, []);

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'beginner': return 'bg-green-100 text-green-800';
      case 'intermediate': return 'bg-blue-100 text-blue-800';
      case 'advanced': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'guide': return 'bg-purple-100 text-purple-800';
      case 'tutorial': return 'bg-orange-100 text-orange-800';
      case 'reference': return 'bg-blue-100 text-blue-800';
      case 'example': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载开发者门户中...</p>
        </div>
      </div>
    );
  }

  return (
    <PageTransition>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="py-8">
              <FadeIn>
                <h1 className="text-4xl font-bold text-gray-900 mb-4">
                  AI Hub 开发者门户
                </h1>
                <p className="text-xl text-gray-600 max-w-3xl">
                  欢迎来到AI Hub开发者社区！这里有完整的文档、工具、插件和最佳实践，帮助您构建出色的AI应用。
                </p>
              </FadeIn>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex space-x-8">
              {[
                { id: 'overview', label: '概览', icon: '🏠' },
                { id: 'guides', label: '文档指南', icon: '📚' },
                { id: 'plugins', label: '插件市场', icon: '🔌' },
                { id: 'community', label: '社区', icon: '👥' },
                { id: 'tools', label: '开发工具', icon: '🛠️' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-8">
              <FadeIn delay={100}>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  {[
                    {
                      title: '快速开始',
                      description: '5分钟内开始您的第一个AI Hub项目',
                      icon: '🚀',
                      color: 'bg-blue-500',
                      link: '/docs/getting-started'
                    },
                    {
                      title: 'API文档',
                      description: '完整的API参考和示例代码',
                      icon: '📖',
                      color: 'bg-green-500',
                      link: '/docs/api'
                    },
                    {
                      title: '插件开发',
                      description: '学习如何创建和发布插件',
                      icon: '🔌',
                      color: 'bg-purple-500',
                      link: '/docs/plugin-development'
                    },
                    {
                      title: '最佳实践',
                      description: '开发规范和性能优化建议',
                      icon: '✨',
                      color: 'bg-orange-500',
                      link: '/docs/best-practices'
                    }
                  ].map((card, index) => (
                    <SlideIn key={card.title} direction="up" delay={index * 100}>
                      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow cursor-pointer">
                        <div className={`w-12 h-12 ${card.color} rounded-lg flex items-center justify-center text-white text-2xl mb-4`}>
                          {card.icon}
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">{card.title}</h3>
                        <p className="text-gray-600 text-sm">{card.description}</p>
                      </div>
                    </SlideIn>
                  ))}
                </div>
              </FadeIn>

              <FadeIn delay={300}>
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-8 border border-blue-200">
                  <h2 className="text-2xl font-bold text-gray-900 mb-4">开始您的开发之旅</h2>
                  <p className="text-gray-700 mb-6">
                    无论您是初学者还是经验丰富的开发者，AI Hub都提供了完整的工具和资源来帮助您成功。
                  </p>
                  <div className="flex flex-wrap gap-4">
                    <button className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
                      创建项目
                    </button>
                    <button className="px-6 py-3 bg-white text-blue-600 border border-blue-600 rounded-md hover:bg-blue-50 transition-colors">
                      浏览文档
                    </button>
                  </div>
                </div>
              </FadeIn>
            </div>
          )}

          {/* Guides Tab */}
          {activeTab === 'guides' && (
            <div className="space-y-6">
              <FadeIn>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-2xl font-bold text-gray-900">文档指南</h2>
                  <div className="flex gap-2">
                    <select className="px-4 py-2 border border-gray-300 rounded-md">
                      <option>所有类型</option>
                      <option>指南</option>
                      <option>教程</option>
                      <option>参考</option>
                      <option>示例</option>
                    </select>
                    <select className="px-4 py-2 border border-gray-300 rounded-md">
                      <option>所有难度</option>
                      <option>初学者</option>
                      <option>中级</option>
                      <option>高级</option>
                    </select>
                  </div>
                </div>
              </FadeIn>

              <StaggeredList staggerDelay={100}>
                <div className="space-y-4">
                  {resources.map((resource, index) => (
                    <SlideIn key={resource.id} direction="up" delay={index * 100}>
                      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center mb-3">
                              <span className={`px-2 py-1 text-xs font-medium rounded-full ${getTypeColor(resource.type)}`}>
                                {resource.type}
                              </span>
                              <span className={`ml-2 px-2 py-1 text-xs font-medium rounded-full ${getDifficultyColor(resource.difficulty)}`}>
                                {resource.difficulty}
                              </span>
                            </div>
                            <h3 className="text-lg font-semibold text-gray-900 mb-2">
                              <a href={resource.url} className="hover:text-blue-600 transition-colors">
                                {resource.title}
                              </a>
                            </h3>
                            <p className="text-gray-600 mb-3">{resource.description}</p>
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-4 text-sm text-gray-500">
                                <span>作者: {resource.author}</span>
                                <span>阅读时间: {resource.readTime}</span>
                                <span>阅读: {resource.viewCount.toLocaleString()}</span>
                              </div>
                              <div className="flex items-center">
                                <span className="text-yellow-500 mr-1">⭐</span>
                                <span className="text-sm font-medium">{resource.rating}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </SlideIn>
                  ))}
                </div>
              </StaggeredList>
            </div>
          )}

          {/* Plugins Tab */}
          {activeTab === 'plugins' && (
            <div className="space-y-6">
              <FadeIn>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-2xl font-bold text-gray-900">插件市场</h2>
                  <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
                    发布插件
                  </button>
                </div>
              </FadeIn>

              <StaggeredList staggerDelay={100}>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {plugins.map((plugin, index) => (
                    <SlideIn key={plugin.id} direction="up" delay={index * 100}>
                      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
                        <div className="flex items-start justify-between mb-4">
                          <h3 className="text-lg font-semibold text-gray-900">{plugin.name}</h3>
                          <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                            v{plugin.version}
                          </span>
                        </div>
                        <p className="text-gray-600 mb-4 text-sm">{plugin.description}</p>
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center space-x-4 text-sm text-gray-500">
                            <span>作者: {plugin.author}</span>
                            <span>下载: {plugin.downloads.toLocaleString()}</span>
                          </div>
                          <div className="flex items-center">
                            <span className="text-yellow-500 mr-1">⭐</span>
                            <span className="text-sm font-medium">{plugin.rating}</span>
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2 mb-4">
                          {plugin.tags.map((tag, tagIndex) => (
                            <span key={tagIndex} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full">
                              {tag}
                            </span>
                          ))}
                        </div>
                        <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
                          安装插件
                        </button>
                      </div>
                    </SlideIn>
                  ))}
                </div>
              </StaggeredList>
            </div>
          )}

          {/* Community Tab */}
          {activeTab === 'community' && (
            <div className="space-y-8">
              <FadeIn>
                <h2 className="text-2xl font-bold text-gray-900 mb-6">社区</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">🎯 讨论论坛</h3>
                    <p className="text-gray-600 mb-4">
                      与其他开发者交流经验，提问并分享您的知识。
                    </p>
                    <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
                      加入讨论
                    </button>
                  </div>
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">💬 实时聊天</h3>
                    <p className="text-gray-600 mb-4">
                      加入我们的Discord/Slack社区，实时与其他开发者交流。
                    </p>
                    <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
                      加入聊天
                    </button>
                  </div>
                </div>
              </FadeIn>

              <FadeIn delay={200}>
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">🏆 贡献者</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                      { name: 'AI Hub Team', avatar: '🤖', contributions: 125 },
                      { name: 'John Doe', avatar: '👨‍💻', contributions: 89 },
                      { name: 'Jane Smith', avatar: '👩‍💻', contributions: 76 },
                      { name: 'Mike Johnson', avatar: '🧑‍💻', contributions: 54 }
                    ].map((contributor, index) => (
                      <div key={index} className="text-center">
                        <div className="text-4xl mb-2">{contributor.avatar}</div>
                        <div className="font-medium text-gray-900">{contributor.name}</div>
                        <div className="text-sm text-gray-500">{contributor.contributions} 贡献</div>
                      </div>
                    ))}
                  </div>
                </div>
              </FadeIn>
            </div>
          )}

          {/* Tools Tab */}
          {activeTab === 'tools' && (
            <div className="space-y-8">
              <FadeIn>
                <h2 className="text-2xl font-bold text-gray-900 mb-6">开发工具</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {[
                    {
                      title: 'AI Hub CLI',
                      description: '命令行工具，用于项目创建、构建和部署',
                      icon: '⌨️',
                      command: 'aihub --help',
                      install: 'pip install aihub-cli'
                    },
                    {
                      title: '插件生成器',
                      description: '快速生成插件项目脚手架',
                      icon: '🔧',
                      command: 'aihub plugin create',
                      install: '内置工具'
                    },
                    {
                      title: 'API 测试工具',
                      description: '在线API测试和调试工具',
                      icon: '🧪',
                      command: '访问 /api-docs',
                      install: 'Web工具'
                    },
                    {
                      title: '代码生成器',
                      description: '基于AI的代码生成工具',
                      icon: '✨',
                      command: 'aihub generate',
                      install: 'AI功能'
                    }
                  ].map((tool, index) => (
                    <SlideIn key={tool.title} direction="up" delay={index * 100}>
                      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <div className="flex items-center mb-4">
                          <span className="text-3xl mr-4">{tool.icon}</span>
                          <div>
                            <h3 className="text-lg font-semibold text-gray-900">{tool.title}</h3>
                            <p className="text-gray-600 text-sm">{tool.description}</p>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center text-sm">
                            <span className="font-medium text-gray-700 mr-2">命令:</span>
                            <code className="bg-gray-100 px-2 py-1 rounded text-gray-800">
                              {tool.command}
                            </code>
                          </div>
                          <div className="flex items-center text-sm">
                            <span className="font-medium text-gray-700 mr-2">安装:</span>
                            <span className="text-gray-600">{tool.install}</span>
                          </div>
                        </div>
                      </div>
                    </SlideIn>
                  ))}
                </div>
              </FadeIn>
            </div>
          )}
        </div>
      </div>
    </PageTransition>
  );
}