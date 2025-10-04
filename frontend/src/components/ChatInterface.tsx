'use client'

import { useState, useRef, useEffect } from 'react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  model?: string
  images?: string[]
  attachments?: File[]
}

interface Model {
  id: string
  name: string
  description: string
  pricing?: {
    prompt: string
    completion: string
  }
  context_length?: number
}

interface Service {
  id: string
  name: string
  models: Model[]
}

interface ChatInterfaceProps {
  className?: string
}

export default function ChatInterface({ className = '' }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedService, setSelectedService] = useState('openrouter')
  const [selectedModel, setSelectedModel] = useState('x-ai/grok-4-fast:free')
  const [services, setServices] = useState<Service[]>([])
  const [models, setModels] = useState<Model[]>([])
  const [temperature, setTemperature] = useState(0.7)
  const [showSettings, setShowSettings] = useState(false)
  const [enableStreaming, setEnableStreaming] = useState(true)
  const [uploadedImages, setUploadedImages] = useState<string[]>([])
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files) return

    Array.from(files).forEach(file => {
      if (file.type.startsWith('image/')) {
        const reader = new FileReader()
        reader.onload = (e) => {
          const base64 = e.target?.result as string
          setUploadedImages(prev => [...prev, base64])
        }
        reader.readAsDataURL(file)
      } else {
        setUploadedFiles(prev => [...prev, file])
      }
    })
  }

  const removeImage = (index: number) => {
    setUploadedImages(prev => prev.filter((_, i) => i !== index))
  }

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index))
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Load available services and models
  useEffect(() => {
    loadServices()
    loadModels(selectedService)
  }, [])

  useEffect(() => {
    loadModels(selectedService)
  }, [selectedService])

  // Load session from localStorage on page load
  useEffect(() => {
    const loadInitialData = async () => {
      const savedSessionId = localStorage.getItem('currentSessionId')
      if (savedSessionId) {
        setCurrentSessionId(savedSessionId)
        await loadSessionMessages(savedSessionId)
      }
    }
    loadInitialData()
  }, [])

  // Save session to localStorage when it changes
  useEffect(() => {
    if (currentSessionId) {
      localStorage.setItem('currentSessionId', currentSessionId)
    }
  }, [currentSessionId])

  const loadServices = async () => {
    try {
      const response = await fetch('/api/v1/chat/services')
      const data = await response.json()
      
      const serviceList: Service[] = [
        {
          id: 'openrouter',
          name: 'OpenRouter (多模型)',
          models: []
        },
        {
          id: 'gemini',
          name: 'Google Gemini (备用)',
          models: []
        }
      ]
      
      setServices(serviceList)
    } catch (error) {
      console.error('Error loading services:', error)
    }
  }

  const loadModels = async (service: string) => {
    try {
      const response = await fetch(`/api/v1/chat/models?service=${service}`)
      const data = await response.json()
      
      if (data.models) {
        setModels(data.models)
        
        // Set default model based on service
        if (service === 'openrouter' && data.models.length > 0) {
          // Find a free model or use the first one
          const freeModel = data.models.find((m: Model) => 
            m.id.includes(':free') || 
            (m.pricing?.prompt === '0' && m.pricing?.completion === '0')
          )
          setSelectedModel(freeModel?.id || data.models[0].id)
        } else if (service === 'gemini' && data.models.length > 0) {
          setSelectedModel(data.models[0].id)
        }
      }
    } catch (error) {
      console.error('Error loading models:', error)
    }
  }

  const handleServiceChange = (service: string) => {
    setSelectedService(service)
  }

  const handleModelChange = (modelId: string) => {
    setSelectedModel(modelId)
  }

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
      images: uploadedImages.length > 0 ? uploadedImages : undefined,
      attachments: uploadedFiles.length > 0 ? uploadedFiles : undefined
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setUploadedImages([])
    setUploadedFiles([])
    setIsLoading(true)

    // Create empty assistant message for streaming
    const assistantMessageId = (Date.now() + 1).toString()
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      model: `${selectedService}:${selectedModel}`
    }

    setMessages(prev => [...prev, assistantMessage])

    try {
      if (enableStreaming) {
        // Streaming response
        await handleStreamingResponse(userMessage, assistantMessageId)
      } else {
        // Regular response
        await handleRegularResponse(userMessage, assistantMessageId)
      }
    } catch (error) {
      console.error('Error sending message:', error)
      await handleErrorWithFallback(error, userMessage, assistantMessageId)
    } finally {
      setIsLoading(false)
    }
  }

  const handleStreamingResponse = async (userMessage: Message, assistantMessageId: string) => {
    const response = await fetch('/api/v1/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: userMessage.content,
        service: selectedService,
        model: selectedModel,
        temperature: temperature,
        session_id: currentSessionId,
        images: uploadedImages.length > 0 ? uploadedImages : undefined
      })
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to send message')
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) {
      throw new Error('No response stream available')
    }

    let accumulatedContent = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              if (data.type === 'content') {
                accumulatedContent += data.content
                
                // Update the assistant message with accumulated content
                setMessages(prev => prev.map(msg => 
                  msg.id === assistantMessageId 
                    ? { ...msg, content: accumulatedContent, model: data.model || msg.model }
                    : msg
                ))
              } else if (data.type === 'session') {
                // Update session ID if returned from backend
                if (data.session_id && !currentSessionId) {
                  setCurrentSessionId(data.session_id)
                }
              } else if (data.type === 'done') {
                // Stream completed
                return
              } else if (data.type === 'error') {
                throw new Error(data.error)
              }
            } catch (parseError) {
              // Skip invalid JSON lines
              continue
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  }

  const handleRegularResponse = async (userMessage: Message, assistantMessageId: string) => {
    const response = await fetch('/api/v1/chat/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: userMessage.content,
        service: selectedService,
        model: selectedModel,
        temperature: temperature,
        session_id: currentSessionId
      })
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to send message')
    }

    const data = await response.json()
    
    // Update session ID if returned from backend
    if (data.session_id && !currentSessionId) {
      setCurrentSessionId(data.session_id)
    }
    
    // Update the assistant message with the complete response
    setMessages(prev => prev.map(msg => 
      msg.id === assistantMessageId 
        ? { ...msg, content: data.message, model: data.model }
        : msg
    ))
  }

  const handleErrorWithFallback = async (error: any, userMessage: Message, assistantMessageId: string) => {
    // If OpenRouter fails with rate limit, try Gemini as fallback
    if (selectedService === 'openrouter' && error.message.includes('429')) {
      try {
        const fallbackResponse = await fetch('/api/v1/chat/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: userMessage.content,
            service: 'gemini',
            model: 'gemini-2.5-flash'
          })
        })

        if (fallbackResponse.ok) {
          const fallbackData = await fallbackResponse.json()
          setMessages(prev => prev.map(msg => 
            msg.id === assistantMessageId 
              ? { 
                  ...msg, 
                  content: `⚠️ OpenRouter暂时不可用，使用Gemini作为备用：\n\n${fallbackData.message}`,
                  model: fallbackData.model
                }
              : msg
          ))
          return
        }
      } catch (fallbackError) {
        console.error('Fallback also failed:', fallbackError)
      }
    }
    
    // Show error message
    setMessages(prev => prev.map(msg => 
      msg.id === assistantMessageId 
        ? { 
            ...msg, 
            content: `抱歉，发送消息时出现错误：${error.message}。请稍后重试。`
          }
        : msg
    ))
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const getCurrentModel = () => {
    return models.find(m => m.id === selectedModel)
  }

  const isModelFree = (model: Model) => {
    return model.id.includes(':free') || 
           (model.pricing?.prompt === '0' && model.pricing?.completion === '0')
  }

  const loadSessionMessages = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/v1/sessions/${sessionId}/messages`)
      if (response.ok) {
        const messagesData = await response.json()
        const formattedMessages = messagesData.map((msg: any) => ({
          id: msg.id,
          content: msg.content,
          role: msg.role as 'user' | 'assistant',
          timestamp: new Date(msg.timestamp),
          model: msg.model,
          usage: msg.usage,
          images: msg.images,
          attachments: msg.attachments
        }))
        setMessages(formattedMessages)
      }
    } catch (error) {
      console.error('Failed to load session messages:', error)
    }
  }

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">AI Hub 对话平台</h1>
            {currentSessionId && (
              <span className="text-sm text-gray-500 dark:text-gray-400">
                会话ID: {currentSessionId.slice(0, 8)}...
              </span>
            )}
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Service Selection */}
            <select
              value={selectedService}
              onChange={(e) => handleServiceChange(e.target.value)}
              className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              {services.map(service => (
                <option key={service.id} value={service.id}>
                  {service.name}
                </option>
              ))}
            </select>

            {/* Model Selection */}
            <select
              value={selectedModel}
              onChange={(e) => handleModelChange(e.target.value)}
              className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white max-w-xs"
            >
              {models.map(model => (
                <option key={model.id} value={model.id}>
                  {model.name} {isModelFree(model) ? '(免费)' : ''}
                </option>
              ))}
            </select>

            {/* Settings Button */}
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              title="设置"
            >
              ⚙️
            </button>
          </div>
        </div>

        {/* Settings Panel */}
        {showSettings && (
          <div className="mt-3 p-3 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <label className="block text-gray-700 dark:text-gray-300 mb-1">
                  Temperature: {temperature}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="streaming"
                  checked={enableStreaming}
                  onChange={(e) => setEnableStreaming(e.target.checked)}
                />
                <label htmlFor="streaming" className="text-gray-700 dark:text-gray-300">
                  启用流式响应
                </label>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 dark:text-gray-400 mt-8">
            <div className="mb-4 text-4xl">💬</div>
            <h3 className="text-lg font-medium mb-2">欢迎使用 AI Hub</h3>
            <p className="text-sm">
              支持多种 AI 模型和联网搜索功能<br/>
              尝试输入 "搜索最新AI新闻" 或 "search latest technology news"
            </p>
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-3xl rounded-lg px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-200 dark:border-gray-600'
              }`}
            >
              {/* Message content */}
              <div className="whitespace-pre-wrap">{message.content}</div>
              
              {/* Message metadata */}
              <div className={`text-xs mt-2 opacity-70 ${
                message.role === 'user' ? 'text-blue-100' : 'text-gray-500 dark:text-gray-400'
              }`}>
                {message.timestamp.toLocaleTimeString()}
                {message.model && ` • ${message.model}`}
              </div>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-3">
              <div className="flex items-center space-x-2">
                <div className="animate-spin h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full"></div>
                <span className="text-gray-600 dark:text-gray-300">AI正在思考...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Upload Preview */}
      {(uploadedImages.length > 0 || uploadedFiles.length > 0) && (
        <div className="border-t border-gray-200 dark:border-gray-700 p-4">
          <div className="flex flex-wrap gap-2">
            {uploadedImages.map((image, index) => (
              <div key={index} className="relative">
                <img
                  src={image}
                  alt={`Upload ${index + 1}`}
                  className="w-20 h-20 object-cover rounded border"
                />
                <button
                  onClick={() => removeImage(index)}
                  className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 text-xs"
                >
                  ×
                </button>
              </div>
            ))}
            {uploadedFiles.map((file, index) => (
              <div key={index} className="relative bg-gray-100 dark:bg-gray-700 p-2 rounded border">
                <span className="text-sm">{file.name}</span>
                <button
                  onClick={() => removeFile(index)}
                  className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 text-xs"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-end space-x-2">
          <div className="flex-1">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="输入消息... (支持搜索功能，试试 '搜索最新AI新闻')"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              rows={1}
              disabled={isLoading}
            />
          </div>
          
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/*,.txt,.pdf,.doc,.docx"
            onChange={handleFileUpload}
            className="hidden"
          />
          
          <button
            onClick={() => fileInputRef.current?.click()}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            title="上传文件"
          >
            📎
          </button>
          
          <button
            onClick={handleSendMessage}
            disabled={!input.trim() || isLoading}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  )
}