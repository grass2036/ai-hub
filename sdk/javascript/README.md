# AI Hub Platform JavaScript SDK

[![npm version](https://badge.fury.io/js/%40ai-hub%2Fjavascript.svg)](https://badge.fury.io/js/%40ai-hub%2Fjavascript)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![TypeScript](https://img.shields.io/badge/%3C%2F%3E-TypeScript-%230074c1.svg)](http://www.typescriptlang.org/)

AI Hub Platform官方JavaScript SDK，为浏览器和Node.js环境提供企业级AI应用开发的完整工具包。

## 🚀 快速开始

### 安装

```bash
# npm
npm install @ai-hub/javascript

# yarn
yarn add @ai-hub/javascript

# pnpm
pnpm add @ai-hub/javascript
```

### 基础使用

```javascript
// ES6 模块
import { AIHubClient } from '@ai-hub/javascript';

// CommonJS
const { AIHubClient } = require('@ai-hub/javascript');

// 初始化客户端
const client = new AIHubClient({
  apiKey: process.env.AIHUB_API_KEY,
  baseURL: 'https://api.aihub.com/api/v1' // 可选，默认值
});

// 创建对话完成
async function chat() {
  try {
    const response = await client.chat.create({
      model: 'gpt-4o-mini',
      messages: [
        { role: 'user', content: '你好，请介绍一下你自己' }
      ],
      maxTokens: 150
    });

    console.log(response.content);
    // 输出: 你好！我是AI Hub平台的AI助手...
  } catch (error) {
    console.error('请求失败:', error.message);
  }
}

// 流式对话
async function streamChat() {
  try {
    console.log('流式回复:');

    for await (const chunk of client.chat.stream({
      model: 'gpt-4o-mini',
      messages: [
        { role: 'user', content: '请写一首关于编程的短诗' }
      ]
    })) {
      if (chunk.content) {
        process.stdout.write(chunk.content);
      }
    }
    console.log(); // 换行
  } catch (error) {
    console.error('流式请求失败:', error.message);
  }
}

chat();
streamChat();
```

## 📋 主要功能

- ✅ **对话完成**: 支持同步和流式对话
- ✅ **多模型支持**: 接入20+主流AI模型
- ✅ **跨平台**: 同时支持浏览器和Node.js环境
- ✅ **TypeScript**: 完整的类型定义和智能提示
- ✅ **错误处理**: 完善的异常处理体系
- ✅ **自动重试**: 内置智能重试机制
- ✅ **使用统计**: API使用量和配额管理
- ✅ **密钥管理**: API密钥的创建和管理

## 🛠️ 详细使用

### 对话API

```javascript
// 基础对话
const response = await client.chat.create({
  model: 'gpt-4o-mini',
  messages: [
    { role: 'system', content: '你是一个专业的编程助手' },
    { role: 'user', content: '如何用JavaScript实现快速排序？' }
  ],
  temperature: 0.7,
  maxTokens: 500
});

// 访问响应数据
console.log('回复内容:', response.content);
console.log('使用token数:', response.usage.totalTokens);
console.log('模型:', response.model);
console.log('成本:', response.cost);

// 流式对话
console.log('流式回复:');
for await (const chunk of client.chat.stream({
  model: 'gpt-4o-mini',
  messages: [
    { role: 'user', content: '解释一下什么是人工智能' }
  ]
})) {
  if (chunk.content) {
    process.stdout.write(chunk.content);
  }
}
```

### 模型管理

```javascript
// 获取可用模型列表
const models = await client.models.list();
models.forEach(model => {
  console.log(`模型: ${model.id} - ${model.name}`);
});

// 获取特定模型信息
const model = await client.models.retrieve('gpt-4o-mini');
console.log(`模型详情: ${model.description}`);
```

### 使用统计

```javascript
// 查看配额信息
const quota = await client.usage.quota();
console.log(`月度配额: ${quota.monthlyQuota}`);
console.log(`已使用: ${quota.monthlyUsed}`);
console.log(`剩余: ${quota.monthlyRemaining}`);
console.log(`使用率: ${quota.monthlyUsagePercent}%`);

// 获取详细使用统计
const stats = await client.usage.stats(30); // 最近30天
console.log(`30天内总请求: ${stats.totalRequests}`);
console.log(`30天内总token: ${stats.totalTokens}`);
console.log(`成功率: ${stats.successRate}%`);
```

### API密钥管理

```javascript
// 获取API密钥列表
const keys = await client.keys.list();
keys.forEach(key => {
  console.log(`密钥: ${key.name} (${key.keyPrefix})`);
});

// 创建新的API密钥
const newKey = await client.keys.create({
  name: '我的新密钥',
  permissions: ['chat.completions', 'chat.models'],
  rateLimit: 100,
  expiresDays: 30
});
console.log(`新密钥: ${newKey.apiKey}`); // 只在创建时显示

// 删除API密钥
const success = await client.keys.delete('key_id_here');
console.log(`删除成功: ${success}`);
```

## 🌐 浏览器使用

### HTML 示例

```html
<!DOCTYPE html>
<html>
<head>
    <title>AI Hub JavaScript SDK 示例</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .chat-container { border: 1px solid #ddd; border-radius: 8px; padding: 20px; }
        .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .user { background: #e3f2fd; margin-left: auto; text-align: right; }
        .assistant { background: #f3e5f5; }
        .input-area { display: flex; margin-top: 20px; }
        input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-right: 10px; }
        button { padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; }
        .loading { color: #666; font-style: italic; }
    </style>
</head>
<body>
    <div class="chat-container">
        <h1>AI Hub Chat Demo</h1>
        <div id="chatMessages"></div>
        <div class="input-area">
            <input type="text" id="messageInput" placeholder="输入你的消息...">
            <button id="sendButton">发送</button>
        </div>
    </div>

    <script type="module">
        import { AIHubClient } from 'https://cdn.skypack.dev/@ai-hub/javascript';

        // 初始化客户端
        const client = new AIHubClient({
            apiKey: 'your_api_key_here', // 请替换为实际的API密钥
            baseURL: 'https://api.aihub.com/api/v1'
        });

        let conversationHistory = [];

        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const chatMessages = document.getElementById('chatMessages');

        // 添加消息到聊天界面
        function addMessage(role, content) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            messageDiv.textContent = content;
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        // 显示加载状态
        function showLoading() {
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message assistant loading';
            loadingDiv.id = 'loadingMessage';
            loadingDiv.textContent = 'AI正在思考...';
            chatMessages.appendChild(loadingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        // 隐藏加载状态
        function hideLoading() {
            const loadingMessage = document.getElementById('loadingMessage');
            if (loadingMessage) {
                loadingMessage.remove();
            }
        }

        // 发送消息到AI
        async function sendToAI(message) {
            try {
                // 添加用户消息到历史记录
                conversationHistory.push({ role: 'user', content: message });

                const response = await client.chat.create({
                    model: 'gpt-4o-mini',
                    messages: conversationHistory,
                    maxTokens: 500
                });

                // 添加AI回复到历史记录
                conversationHistory.push({
                    role: 'assistant',
                    content: response.content
                });

                return response.content;
            } catch (error) {
                console.error('发送失败:', error);
                return '抱歉，发生了错误，请稍后重试。';
            }
        }

        // 处理发送按钮点击
        async function handleSend() {
            const message = messageInput.value.trim();
            if (!message) return;

            // 禁用输入
            sendButton.disabled = true;
            messageInput.disabled = true;

            // 添加用户消息
            addMessage('user', message);
            messageInput.value = '';

            // 显示加载状态
            showLoading();

            // 发送到AI
            const response = await sendToAI(message);

            // 隐藏加载状态
            hideLoading();

            // 添加AI回复
            addMessage('assistant', response);

            // 重新启用输入
            sendButton.disabled = false;
            messageInput.disabled = false;
            messageInput.focus();
        }

        // 事件监听
        sendButton.addEventListener('click', handleSend);
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleSend();
            }
        });

        // 初始化欢迎消息
        addMessage('assistant', '你好！我是AI Hub的AI助手，请问有什么可以帮助你的？');
    </script>
</body>
</html>
```

### React Hook 示例

```jsx
import { useState, useCallback } from 'react';
import { AIHubClient } from '@ai-hub/javascript';

const client = new AIHubClient({
  apiKey: process.env.REACT_APP_AIHUB_API_KEY
});

export function useAIChat() {
  const [loading, setLoading] = useState(false);
  const [conversation, setConversation] = useState([]);

  const sendMessage = useCallback(async (message) => {
    setLoading(true);

    try {
      // 添加用户消息
      const newConversation = [
        ...conversation,
        { role: 'user', content: message }
      ];

      const response = await client.chat.create({
        model: 'gpt-4o-mini',
        messages: newConversation,
        maxTokens: 500
      });

      // 添加AI回复
      setConversation([
        ...newConversation,
        { role: 'assistant', content: response.content }
      ]);

      return response.content;
    } catch (error) {
      console.error('AI请求失败:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [conversation]);

  const resetConversation = useCallback(() => {
    setConversation([]);
  }, []);

  return {
    sendMessage,
    resetConversation,
    conversation,
    loading
  };
}

// 使用示例
function ChatComponent() {
  const { sendMessage, conversation, loading } = useAIChat();
  const [input, setInput] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    try {
      await sendMessage(input.trim());
      setInput('');
    } catch (error) {
      alert('发送失败: ' + error.message);
    }
  };

  return (
    <div className="chat">
      <div className="messages">
        {conversation.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            {msg.content}
          </div>
        ))}
        {loading && <div className="message assistant loading">AI正在思考...</div>}
      </div>

      <form onSubmit={handleSubmit} className="input-form">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入消息..."
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          发送
        </button>
      </form>
    </div>
  );
}
```

## ⚙️ 高级配置

### 自定义配置

```javascript
const client = new AIHubClient({
  apiKey: 'your_api_key',
  baseURL: 'https://api.aihub.com/api/v1',
  timeout: 30000,        // 请求超时时间（毫秒）
  maxRetries: 3,         // 最大重试次数
  userAgent: 'MyApp/1.0' // 自定义User-Agent
});
```

### 错误处理

```javascript
import {
  AIHubClient,
  APIError,
  AuthenticationError,
  RateLimitError,
  InsufficientQuotaError,
  ModelNotFoundError
} from '@ai-hub/javascript';

const client = new AIHubClient({ apiKey: 'your_api_key' });

try {
  const response = await client.chat.create({
    model: 'gpt-4o-mini',
    messages: [{ role: 'user', content: 'Hello' }]
  });
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.log('API密钥无效，请检查密钥是否正确');
  } else if (error instanceof RateLimitError) {
    console.log(`请求过于频繁，请在${error.retryAfter}秒后重试`);
  } else if (error instanceof InsufficientQuotaError) {
    console.log('配额不足，请升级套餐或等待重置');
  } else if (error instanceof ModelNotFoundError) {
    console.log(`模型不存在: ${error.model}`);
  } else if (error instanceof APIError) {
    console.log(`API错误: ${error.message} (代码: ${error.errorCode})`);
  } else {
    console.log('未知错误:', error.message);
  }
}
```

## 🎯 使用示例

### 翻译助手

```javascript
async function translateText(text, targetLanguage = 'English') {
  const client = new AIHubClient({ apiKey: process.env.AIHUB_API_KEY });

  const response = await client.chat.create({
    model: 'gpt-4o-mini',
    messages: [
      {
        role: 'system',
        content: `You are a professional translator. Translate the given text to ${targetLanguage}.`
      },
      {
        role: 'user',
        content: text
      }
    ],
    temperature: 0.3
  });

  return response.content;
}

// 使用示例
const translation = await translateText('你好，世界！', 'English');
console.log(translation);
```

### 代码生成器

```javascript
async function generateCode(description, language = 'JavaScript') {
  const client = new AIHubClient({ apiKey: process.env.AIHUB_API_KEY });

  const response = await client.chat.create({
    model: 'gpt-4o',
    messages: [
      {
        role: 'system',
        content: `You are an expert ${language} programmer. Generate clean, well-commented code based on the description.`
      },
      {
        role: 'user',
        content: `Write ${language} code to: ${description}`
      }
    ],
    temperature: 0.2,
    maxTokens: 1000
  });

  return response.content;
}

// 使用示例
const code = await generateCode('implement a binary search algorithm', 'JavaScript');
console.log(code);
```

### 流式聊天机器人

```javascript
class ChatBot {
  constructor(apiKey, systemPrompt = null) {
    this.client = new AIHubClient({ apiKey });
    this.conversation = [];

    if (systemPrompt) {
      this.conversation.push({
        role: 'system',
        content: systemPrompt
      });
    }
  }

  async chat(userMessage) {
    // 添加用户消息
    this.conversation.push({
      role: 'user',
      content: userMessage
    });

    // 获取AI回复
    const response = await this.client.chat.create({
      model: 'gpt-4o-mini',
      messages: this.conversation,
      temperature: 0.7
    });

    const aiMessage = response.content;

    // 添加AI回复到对话历史
    this.conversation.push({
      role: 'assistant',
      content: aiMessage
    });

    return aiMessage;
  }

  async *streamChat(userMessage) {
    // 添加用户消息
    this.conversation.push({
      role: 'user',
      content: userMessage
    });

    process.stdout.write('AI: ');

    // 流式获取回复
    let fullResponse = '';
    for await (const chunk of this.client.chat.stream({
      model: 'gpt-4o-mini',
      messages: this.conversation,
      temperature: 0.7
    })) {
      if (chunk.content) {
        process.stdout.write(chunk.content);
        fullResponse += chunk.content;
      }
    }

    // 添加完整回复到对话历史
    this.conversation.push({
      role: 'assistant',
      content: fullResponse
    });

    console.log(); // 换行
  }
}

// 使用示例
const bot = new ChatBot(
  process.env.AIHUB_API_KEY,
  '你是一个友好、专业的AI助手。'
);

await bot.streamChat('你好！请介绍一下你的功能');
await bot.streamChat('你能帮我写一个JavaScript函数吗？');
```

## 🧪 开发和测试

### 安装开发依赖

```bash
git clone https://github.com/ai-hub/platform.git
cd platform/sdk/javascript
npm install
```

### 运行测试

```bash
# 运行所有测试
npm test

# 运行测试并生成覆盖率报告
npm run test:coverage

# 监视模式运行测试
npm run test:watch
```

### 构建项目

```bash
# 构建生产版本
npm run build

# 开发模式构建
npm run dev
```

### 代码检查和格式化

```bash
# ESLint检查
npm run lint

# 自动修复ESLint问题
npm run lint:fix

# Prettier格式化
npm run format

# TypeScript类型检查
npm run type-check
```

## 📚 文档

- [完整API文档](https://docs.aihub.com)
- [开发者指南](https://docs.aihub.com/developer-guide)
- [API参考](https://docs.aihub.com/api-reference)
- [示例代码](https://github.com/ai-hub/platform/tree/main/sdk/javascript/examples)

## 🤝 贡献

欢迎贡献代码！请查看 [贡献指南](../../CONTRIBUTING.md) 了解详细信息。

## 📄 许可证

本项目采用 MIT 许可证。详情请见 [LICENSE](../../LICENSE) 文件。

## 🆘 支持

- 📧 技术支持: support@aihub.com
- 💬 开发者社区: https://community.aihub.com
- 🐛 问题反馈: https://github.com/ai-hub/platform/issues
- 📖 文档: https://docs.aihub.com

---

**AI Hub Platform** - 企业级AI应用平台 🚀