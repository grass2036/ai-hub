'use client';

import { useState, useRef, useEffect } from 'react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  isLoading?: boolean;
}

export default function ChatInput({ onSendMessage, disabled = false, isLoading = false }: ChatInputProps) {
  const [inputValue, setInputValue] = useState('');
  const [isPreviewMode, setIsPreviewMode] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 自动调整textarea高度
  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [inputValue]);

  // 快捷键支持
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (inputValue.trim() && !disabled) {
        onSendMessage(inputValue);
        setInputValue('');
        setIsPreviewMode(false);
      }
    } else if (e.key === 'Enter' && e.shiftKey) {
      // Shift+Enter换行，不做处理
    } else if (e.key === 'Escape') {
      setIsPreviewMode(false);
    }
  };

  // Markdown预览
  const renderMarkdownPreview = (text: string) => {
    // 简单的Markdown渲染
    let html = text
      // 标题
      .replace(/^### (.*$)/gim, '<h3 class="text-lg font-bold text-gray-900 mb-2">$1</h3>')
      .replace(/^## (.*$)/gim, '<h2 class="text-xl font-bold text-gray-900 mb-3">$1</h2>')
      .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold text-gray-900 mb-4">$1</h1>')
      // 粗体
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      // 斜体
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      // 行内代码
      .replace(/`(.*?)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-sm">$1</code>')
      // 换行
      .replace(/\n\n/g, '</p><p class="mb-4">')
      .replace(/\n/g, '<br>');

    // 代码块
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre class="bg-gray-900 text-gray-100 p-4 rounded-lg mb-4 overflow-x-auto"><code class="language-${lang}">${code}</code></pre>`;
    });

    return `<p class="mb-4">${html}</p>`;
  };

  // 常用提示词模板
  const promptTemplates = [
    { label: '代码生成', prompt: '帮我写一个Python函数，用于计算斐波那契数列' },
    { label: '数据分析', prompt: '帮我分析这份数据的趋势和关键信息' },
    {   label: '文档写作', prompt: '帮我写一份关于人工智能发展趋势的报告' },
    { label: '创意写作', prompt: '帮我写一个关于AI助手的短故事' },
    { label: '技术支持', prompt: '我的电脑出现蓝屏错误，帮我分析和解决' }
  ];

  return (
    <div className="border border-gray-200 rounded-lg bg-white">
      {/* 工具栏 */}
      <div className="flex items-center justify-between p-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsPreviewMode(!isPreviewMode)}
            className={`px-3 py-1 text-sm rounded-md transition-colors ${
              isPreviewMode
                ? 'bg-blue-600 text-white'
                : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            {isPreviewMode ? '编辑' : '预览'}
          </button>
          <span className="text-xs text-gray-500">
            {isPreviewMode ? 'Markdown预览' : '支持Markdown格式'}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500">
            {inputValue.length} 字符
          </span>
          <span className="text-xs text-gray-500">
            Enter发送 | Shift+Enter换行
          </span>
        </div>
      </div>

      {/* 输入区域 */}
      <div className="p-3">
        {!isPreviewMode ? (
          <>
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入你的问题... 支持Markdown格式"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none font-mono text-sm"
              rows={1}
              style={{ minHeight: '60px', maxHeight: '200px' }}
              disabled={disabled}
            />
          </>
        ) : (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 min-h-[120px] max-h-[300px] overflow-y-auto">
            {inputValue ? (
              <div
                className="prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{ __html: renderMarkdownPreview(inputValue) }}
              />
            ) : (
              <div className="text-gray-400 text-center">
                输入内容后可在此预览Markdown效果
              </div>
            )}
          </div>
        )}
      </div>

      {/* 快捷模板 */}
      <div className="border-t border-gray-200 p-3">
        <div className="flex flex-wrap gap-2">
          {promptTemplates.map((template, index) => (
            <button
              key={index}
              onClick={() => {
                setInputValue(template.prompt);
                setIsPreviewMode(false);
                textareaRef.current?.focus();
              }}
              className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors whitespace-nowrap"
            >
              {template.label}
            </button>
          ))}
        </div>
      </div>

      {/* 发送按钮 */}
      <div className="border-t border-gray-200 p-3">
        <div className="flex items-center justify-between">
          <div className="text-xs text-gray-500">
            <span>💡 提示：使用 **粗体**、*斜体*、`代码`等Markdown格式</span>
          </div>
          <button
            onClick={() => {
              if (inputValue.trim() && !disabled) {
                onSendMessage(inputValue);
                setInputValue('');
                setIsPreviewMode(false);
              }
            }}
            disabled={!inputValue.trim() || disabled || isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                发送中...
              </>
            ) : (
              <>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18" />
                </svg>
                发送
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}