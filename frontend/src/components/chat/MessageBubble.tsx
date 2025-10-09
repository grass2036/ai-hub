'use client';

import { useState } from 'react';

interface MessageBubbleProps {
  message: {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    isStreaming?: boolean;
  };
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const [isCopied, setIsCopied] = useState(false);

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  // 渲染消息内容，支持代码高亮
  const renderContent = (content: string) => {
    // 处理代码块
    const codeBlockRegex = /```(\w*)\n([\s\S]*?)```/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = codeBlockRegex.exec(content)) !== null) {
      // 添加代码块前的文本
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: content.substring(lastIndex, match.index)
        });
      }

      // 添加代码块
      parts.push({
        type: 'code',
        language: match[1],
        content: match[2]
      });

      lastIndex = match.index + match[0].length;
    }

    // 添加剩余文本
    if (lastIndex < content.length) {
      parts.push({
        type: 'text',
        content: content.substring(lastIndex)
      });
    }

    return parts.map((part, index) => {
      if (part.type === 'code') {
        return (
          <div key={index} className="relative group">
            <div className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto my-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-400">
                  {part.language || 'plaintext'}
                </span>
                <button
                  onClick={() => copyToClipboard(part.content)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-gray-700 rounded"
                  title="复制代码"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2h-2z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8l-8 8-8-8" />
                  </svg>
                  {isCopied && (
                    <span className="absolute -top-8 -right-8 text-xs bg-green-600 text-white px-2 py-1 rounded">
                      已复制
                    </span>
                  )}
                </button>
              </div>
              <pre className="text-sm">
                <code>{part.content}</code>
              </pre>
            </div>
          </div>
        );
      } else {
        // 处理普通文本中的行内代码
        const processedText = part.content
          .replace(/`([^`]+)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">$1</code>')
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/\*(.*?)\*/g, '<em>$1</em>');

        return (
          <div key={index} className="whitespace-pre-wrap">
            <div dangerouslySetInnerHTML={{ __html: processedText }} />
          </div>
        );
      }
    });
  };

  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-3xl relative ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-white border border-gray-200 text-gray-900'
        } rounded-lg shadow-sm overflow-hidden`}
      >
        {/* 消息内容 */}
        <div className="p-4">
          {renderContent(message.content)}

          {/* 流式响应指示器 */}
          {message.isStreaming && (
            <div className="flex items-center mt-2 text-xs">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          )}
        </div>

        {/* 时间戳和操作按钮 */}
        <div className={`px-4 py-2 border-t ${
          isUser ? 'border-blue-500 bg-blue-700' : 'border-gray-200 bg-gray-50'
        } flex items-center justify-between`}>
          <span className={`text-xs ${
            isUser ? 'text-blue-100' : 'text-gray-500'
          }`}>
            {new Date(message.timestamp).toLocaleTimeString('zh-CN')}
          </span>

          {!isUser && (
            <div className="flex items-center space-x-2">
              <button
                onClick={() => copyToClipboard(message.content)}
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-gray-200 rounded"
                title="复制消息"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2h-2z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8l-8 8-8-8" />
                </svg>
                {isCopied && (
                  <span className="absolute -top-8 -right-8 text-xs bg-green-600 text-white px-2 py-1 rounded shadow-lg">
                    已复制
                  </span>
                )}
              </button>
              <button
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-gray-200 rounded"
                title="重新生成"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 15.356M12 15h8m-8 0v-4" />
                </svg>
              </button>
              <button
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-gray-200 rounded"
                title="点赞"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                </svg>
              </button>
              <button
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-gray-200 rounded"
                title="踩"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018c.163 0 .326.02.485.06L17 4m-7 10v5a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                </svg>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}