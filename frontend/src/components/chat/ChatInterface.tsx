'use client';

import { useState, useEffect, useRef } from 'react';
import { apiClient } from '@/lib/api';
import MessageBubble from './MessageBubble';
import ChatInput from './ChatInput';
import ModelSelector from '@/components/ModelSelector';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
}

interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: Message[];
}

export default function ChatInterface({ className = '' }: { className?: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const [showSessionPanel, setShowSessionPanel] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>('gpt-3.5-turbo');
  const [showModelSelector, setShowModelSelector] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // 初始化新会话
  const createNewSession = () => {
    const newSession: ChatSession = {
      id: Date.now().toString(),
      title: '新对话',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: []
    };

    setSessions(prev => [newSession, ...prev]);
    setCurrentSessionId(newSession.id);
    setMessages([]);
    saveSessionsToLocalStorage([newSession, ...sessions]);
  };

  // 从localStorage加载会话
  const loadSessionsFromLocalStorage = () => {
    try {
      const stored = localStorage.getItem('chat_sessions');
      if (stored) {
        const parsedSessions = JSON.parse(stored);
        setSessions(parsedSessions);
        if (parsedSessions.length > 0) {
          setCurrentSessionId(parsedSessions[0].id);
          setMessages(parsedSessions[0].messages);
        }
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  };

  // 保存会话到localStorage
  const saveSessionsToLocalStorage = (sessionData: ChatSession[]) => {
    try {
      localStorage.setItem('chat_sessions', JSON.stringify(sessionData));
    } catch (error) {
      console.error('Failed to save sessions:', error);
    }
  };

  // 切换会话
  const switchSession = (sessionId: string) => {
    const session = sessions.find(s => s.id === sessionId);
    if (session) {
      setCurrentSessionId(sessionId);
      setMessages(session.messages);
    }
  };

  // 删除会话
  const deleteSession = (sessionId: string) => {
    const updatedSessions = sessions.filter(s => s.id !== sessionId);
    setSessions(updatedSessions);
    saveSessionsToLocalStorage(updatedSessions);

    if (currentSessionId === sessionId && updatedSessions.length > 0) {
      switchSession(updatedSessions[0].id);
    }
  };

  // 更新会话标题
  const updateSessionTitle = (sessionId: string, title: string) => {
    const updatedSessions = sessions.map(session =>
      session.id === sessionId
        ? { ...session, title, updatedAt: new Date().toISOString() }
        : session
    );
    setSessions(updatedSessions);
    saveSessionsToLocalStorage(updatedSessions);
  };

  // 发送消息
  const sendMessage = async (message?: string) => {
    const content = message || inputValue;
    if (!content.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString()
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInputValue('');
    setIsLoading(true);
    setIsStreaming(true);

    // 如果是新会话的第一条消息，根据内容设置标题
    if (messages.length === 0 && sessions.find(s => s.id === currentSessionId)) {
      const title = content.length > 30
        ? content.substring(0, 30) + '...'
        : content;
      updateSessionTitle(currentSessionId, title);
    }

    try {
      // 关闭之前的连接
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      // 创建新的SSE连接用于流式响应
      const eventSource = new EventSource(
        `http://localhost:8002/api/v1/chat/stream?prompt=${encodeURIComponent(content)}&model=${selectedModel}`
      );

      eventSourceRef.current = eventSource;

      let assistantMessage: Message | null = null;
      let messageId = Date.now().toString();

      eventSource.onmessage = (event) => {
        try {
          const chunk = event.data;

          if (chunk === '[DONE]') {
            // 流式响应结束
            setIsStreaming(false);
            setIsLoading(false);
            eventSource.close();

            // 保存消息到会话
            const finalMessages = assistantMessage
              ? [...newMessages, assistantMessage]
              : newMessages;

            const updatedSessions = sessions.map(session =>
              session.id === currentSessionId
                ? { ...session, messages: finalMessages, updatedAt: new Date().toISOString() }
                : session
            );
            setSessions(updatedSessions);
            saveSessionsToLocalStorage(updatedSessions);
            return;
          }

          // 解析响应数据
          const data = JSON.parse(chunk);

          if (data.choices && data.choices[0]) {
            const content = data.choices[0].message?.content || '';

            if (!assistantMessage) {
              assistantMessage = {
                id: messageId,
                role: 'assistant',
                content: content,
                timestamp: new Date().toISOString(),
                isStreaming: true
              };
              setMessages([...newMessages, assistantMessage]);
            } else {
              assistantMessage.content += content;
              setMessages([...newMessages.slice(0, -1), assistantMessage]);
            }
          }
        } catch (error) {
          console.error('Error parsing SSE data:', error);
        }
      };

      eventSource.onerror = () => {
        console.error('SSE connection error');
        setIsStreaming(false);
        setIsLoading(false);
        eventSource.close();

        // 创建错误消息
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: '抱歉，连接AI服务时出现了问题。请稍后重试。',
          timestamp: new Date().toISOString()
        };

        setMessages([...newMessages, errorMessage]);

        // 保存到会话
        const finalMessages = [...newMessages, errorMessage];
        const updatedSessions = sessions.map(session =>
          session.id === currentSessionId
            ? { ...session, messages: finalMessages, updatedAt: new Date().toISOString() }
            : session
        );
        setSessions(updatedSessions);
        saveSessionsToLocalStorage(updatedSessions);
      };

    } catch (error) {
      console.error('Error sending message:', error);
      setIsLoading(false);
      setIsStreaming(false);
    }
  };

  // 清空当前对话
  const clearCurrentChat = () => {
    setMessages([]);
    if (currentSessionId) {
      const updatedSessions = sessions.map(session =>
        session.id === currentSessionId
          ? { ...session, messages: [], updatedAt: new Date().toISOString() }
          : session
      );
      setSessions(updatedSessions);
      saveSessionsToLocalStorage(updatedSessions);
    }
  };

  // 初始化
  useEffect(() => {
    loadSessionsFromLocalStorage();
    if (sessions.length === 0) {
      createNewSession();
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className={`flex h-full bg-white ${className}`}>
      {/* 会话列表侧边栏 */}
      <div className={`${showSessionPanel ? 'block' : 'hidden'} md:block w-80 border-r border-gray-200 bg-gray-50 flex flex-col`}>
        {/* 侧边栏头部 */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">聊天记录</h2>
            <button
              onClick={() => setShowSessionPanel(false)}
              className="md:hidden p-2 rounded-md hover:bg-gray-200"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <button
            onClick={createNewSession}
            className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            新建对话
          </button>
        </div>

        {/* 会话列表 */}
        <div className="flex-1 overflow-y-auto p-2">
          {sessions.map((session) => (
            <div
              key={session.id}
              className={`p-3 mb-2 rounded-lg cursor-pointer transition-colors ${
                currentSessionId === session.id
                  ? 'bg-blue-100 border-blue-300 border'
                  : 'bg-white hover:bg-gray-100 border border-gray-200'
              }`}
              onClick={() => switchSession(session.id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-medium text-gray-900 truncate">
                    {session.title}
                  </h3>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(session.updatedAt).toLocaleString('zh-CN', {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteSession(session.id);
                  }}
                  className="p-1 rounded hover:bg-red-100 text-red-600"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6a2 2 0 002 2h6a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v-6a2 2 0 012-2h6a2 2 0 012 2v6a2 2 0 01-2 2H9a2 2 0 01-2-2v-6a2 2 0 012-2h6a2 2 0 012 2v6a2 2 0 01-2 2H9a2 2 0 01-2-2v-6a2 2 0 012-2h6a2 2 0 012 2v6a2 2 0 01-2 2H9z" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 主聊天区域 */}
      <div className="flex-1 flex flex-col">
        {/* 聊天头部 */}
        <div className="border-b border-gray-200 p-4 bg-white">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setShowSessionPanel(!showSessionPanel)}
              className="md:hidden p-2 rounded-md hover:bg-gray-100 mr-4"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div className="flex-1 min-w-0">
              <h1 className="text-xl font-semibold text-gray-900 truncate">
                {sessions.find(s => s.id === currentSessionId)?.title || 'AI 对话'}
              </h1>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setShowModelSelector(!showModelSelector)}
                className="p-2 rounded-md hover:bg-gray-100 text-gray-600"
                title="选择模型"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </button>
              <button
                onClick={clearCurrentChat}
                className="p-2 rounded-md hover:bg-gray-100 text-gray-600"
                title="清空对话"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6a2 2 0 002 2h6a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v-6a2 2 0 012-2h6a2 2 0 012 2v6a2 2 0 01-2 2H9a2 2 0 01-2-2v-6a2 2 0 012-2h6a2 2 0 012 2v6a2 2 0 01-2 2H9z" />
                </svg>
              </button>
              <button
                className="p-2 rounded-md hover:bg-gray-100 text-gray-600"
                title="导出对话"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </button>
              <button
                className="p-2 rounded-md hover:bg-gray-100 text-gray-600"
                title="设置"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>
            </div>
          </div>

          {/* 模型选择器 */}
          {showModelSelector && (
            <div className="mt-4 border-t border-gray-200 pt-4">
              <ModelSelector
                selectedModel={selectedModel}
                onModelChange={setSelectedModel}
                className="mb-0"
              />
            </div>
          )}
        </div>

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto p-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <div className="text-6xl mb-4">💬</div>
              <p className="text-lg mb-2">开始与AI对话吧！</p>
              <p className="text-sm mb-8">输入你的问题，AI助手会为你提供帮助</p>

              {/* 快捷操作按钮 */}
              <div className="flex flex-col sm:flex-row gap-3 mb-6">
                <button
                  onClick={() => setInputValue('帮我写一个Python函数，用于计算斐波那契数列')}
                  className="px-4 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors"
                >
                  💻 代码生成示例
                </button>
                <button
                  onClick={() => setInputValue('请介绍一下人工智能的发展历史')}
                  className="px-4 py-2 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors"
                >
                  📚 知识问答
                </button>
                <button
                  onClick={() => setInputValue('帮我分析一下最近的科技发展趋势')}
                  className="px-4 py-2 bg-purple-50 text-purple-700 rounded-lg hover:bg-purple-100 transition-colors"
                >
                  📊 数据分析
                </button>
              </div>

              {/* 常用问题 */}
              <div className="max-w-md">
                <p className="text-xs text-gray-400 mb-3">常用问题：</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  <button
                    onClick={() => setInputValue('今天天气怎么样？')}
                    className="text-xs px-3 py-1 bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 transition-colors"
                  >
                    天气查询
                  </button>
                  <button
                    onClick={() => setInputValue('推荐一些学习编程的资源')}
                    className="text-xs px-3 py-1 bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 transition-colors"
                  >
                    学习资源
                  </button>
                  <button
                    onClick={() => setInputValue('如何提高工作效率？')}
                    className="text-xs px-3 py-1 bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 transition-colors"
                  >
                    效率提升
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              {isStreaming && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 text-gray-900 px-4 py-2 rounded-lg max-w-3xl">
                    <div className="flex items-center">
                      <div className="animate-pulse">AI正在思考...</div>
                      <div className="ml-2 flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* 输入区域 */}
        <div className="border-t border-gray-200 bg-white">
          <ChatInput
            onSendMessage={sendMessage}
            disabled={isLoading}
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  );
}