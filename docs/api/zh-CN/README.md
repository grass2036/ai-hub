# AI Hub API 文档

欢迎使用 AI Hub API 文档。本综合指南将帮助您将我们强大的 AI 功能集成到您的应用程序中。

## 目录

1. [API 概览](#api-概览)
2. [身份验证](#身份验证)
3. [基础 URL](#基础-url)
4. [可用端点](#可用端点)
5. [速率限制](#速率限制)
6. [错误处理](#错误处理)
7. [代码示例](#代码示例)
8. [SDK 和库](#sdk-和库)

## API 概览

AI Hub API 通过统一的 RESTful 接口提供对 140+ AI 模型的编程访问。我们的 API 支持：

- **多个 AI 模型** - 访问 GPT-4、Claude、Gemini 等
- **流式响应** - 实时响应流式传输
- **会话管理** - 持久化对话上下文
- **成本跟踪** - 透明的使用监控
- **全球可用性** - 多区域端点

### 主要功能

- 🔑 **简单身份验证** - Bearer 令牌认证
- 📊 **使用分析** - 实时使用跟踪
- 🌍 **多语言支持** - 国际化响应格式
- 🔄 **流式和非流式** - 选择您的响应模式
- 📝 **丰富上下文** - 维护对话历史
- ⚡ **高性能** - 为速度和可靠性优化

## 身份验证

所有 API 请求都需要使用 Bearer 令牌进行身份验证。

### 获取您的 API 密钥

1. 登录您的 [AI Hub 仪表板](https://dashboard.ai-hub.com)
2. 导航到 **API 密钥** 部分
3. 点击 **生成新密钥**
4. 立即复制您的 API 密钥

### 使用您的 API 密钥

在 `Authorization` 头中包含您的 API 密钥：

```http
Authorization: Bearer your-api-key-here
```

**⚠️ 安全提示**：永远不要在客户端代码或公共存储库中暴露您的 API 密钥。

## 基础 URL

我们的 API 在多个区域可用，以获得最佳性能：

### 主要端点

- **全球**：`https://api.ai-hub.com/v1`
- **美国东部**：`https://api-us-east.ai-hub.com/v1`
- **欧洲**：`https://api-eu.ai-hub.com/v1`
- **亚太地区**：`https://api-ap-southeast.ai-hub.com/v1`

### 区域选择

选择离您的用户最近的端点以获得更好的性能。所有端点提供相同的功能。

## 可用端点

### 聊天补全

使用各种 AI 模型创建聊天补全。

#### 非流式聊天

```http
POST /chat/completions
```

**请求体：**
```json
{
  "model": "gpt-4",
  "messages": [
    {
      "role": "system",
      "content": "你是一个有用的助手。"
    },
    {
      "role": "user",
      "content": "你好，AI Hub！"
    }
  ],
  "max_tokens": 1000,
  "temperature": 0.7,
  "stream": false
}
```

**响应：**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好！我在这里帮助您使用 AI Hub。今天我能为您做些什么？"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 18,
    "total_tokens": 30
  }
}
```

#### 流式聊天

```http
POST /chat/stream
```

**请求体：**
```json
{
  "model": "gpt-4",
  "messages": [
    {
      "role": "user",
      "content": "给我讲个故事"
    }
  ],
  "stream": true
}
```

**响应（服务器发送事件）：**
```
data: {"id": "chatcmpl-123", "choices": [{"delta": {"content": "从前"}}]}

data: {"id": "chatcmpl-123", "choices": [{"delta": {"content": "，"}}]}

data: {"id": "chatcmpl-123", "choices": [{"delta": {"content": "有"}}]}

data: [DONE]
```

### 模型

列出所有可用的 AI 模型。

```http
GET /models
```

**响应：**
```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-4",
      "object": "model",
      "created": 1677652288,
      "owned_by": "openai"
    },
    {
      "id": "claude-3-opus",
      "object": "model",
      "created": 1677652288,
      "owned_by": "anthropic"
    }
  ]
}
```

### 使用情况

获取您当前的使用统计信息。

```http
GET /usage
```

**响应：**
```json
{
  "period": {
    "start": "2024-12-01T00:00:00Z",
    "end": "2024-12-31T23:59:59Z"
  },
  "usage": {
    "total_requests": 1250,
    "total_tokens": 125000,
    "total_cost": 25.50,
    "models": {
      "gpt-4": {
        "requests": 800,
        "tokens": 80000,
        "cost": 20.00
      },
      "claude-3": {
        "requests": 450,
        "tokens": 45000,
        "cost": 5.50
      }
    }
  }
}
```

### 会话

管理对话会话以实现上下文持久化。

#### 创建会话

```http
POST /sessions
```

**请求体：**
```json
{
  "title": "客户支持聊天",
  "model": "gpt-4",
  "system_prompt": "你是一个有用的客户支持助手。"
}
```

#### 获取会话

```http
GET /sessions/{session_id}
```

#### 更新会话

```http
PUT /sessions/{session_id}
```

#### 删除会话

```http
DELETE /sessions/{session_id}
```

## 速率限制

为确保公平使用和系统稳定性，我们实施速率限制：

### 速率限制层级

| 计划 | 每分钟请求数 | 每分钟令牌数 |
|------|-------------|-------------|
| 免费 | 10 | 10,000 |
| 开发者 | 100 | 100,000 |
| 专业 | 500 | 500,000 |
| 企业 | 无限制 | 无限制 |

### 速率限制头

所有 API 响应都包含速率限制头：

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

### 处理速率限制

当您达到速率限制时，您将收到 `429 Too Many Requests` 响应：

```json
{
  "error": {
    "message": "超出速率限制。请在 60 秒后重试。",
    "type": "rate_limit_exceeded",
    "retry_after": 60
  }
}
```

## 错误处理

我们的 API 返回标准的 HTTP 状态代码和详细的错误消息。

### HTTP 状态代码

- `200 OK` - 请求成功
- `400 Bad Request` - 无效的请求参数
- `401 Unauthorized` - 无效的 API 密钥
- `403 Forbidden` - API 密钥没有权限
- `404 Not Found` - 资源未找到
- `429 Too Many Requests` - 超出速率限制
- `500 Internal Server Error` - 服务器错误

### 错误响应格式

```json
{
  "error": {
    "message": "指定的模型无效",
    "type": "invalid_request_error",
    "param": "model",
    "code": "model_not_found"
  }
}
```

### 错误类型

- `invalid_request_error` - 无效的请求参数
- `authentication_error` - 身份验证失败
- `permission_error` - 权限不足
- `rate_limit_error` - 超出速率限制
- `api_error` - API 相关错误
- `model_error` - 模型特定错误

## 代码示例

### Python

```python
import requests
import json

# 配置
API_KEY = "your-api-key-here"
BASE_URL = "https://api.ai-hub.com/v1"

# 头部
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 非流式聊天补全
def chat_completion(message, model="gpt-4"):
    url = f"{BASE_URL}/chat/completions"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "max_tokens": 1000,
        "temperature": 0.7
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# 流式聊天补全
def stream_chat(message, model="gpt-4"):
    url = f"{BASE_URL}/chat/stream"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": True
    }

    response = requests.post(url, json=payload, headers=headers, stream=True)

    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]  # 移除 'data: ' 前缀
                if data == '[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                    if 'choices' in chunk and len(chunk['choices']) > 0:
                        delta = chunk['choices'][0].get('delta', {})
                        if 'content' in delta:
                            print(delta['content'], end='', flush=True)
                except json.JSONDecodeError:
                    continue

# 使用
if __name__ == "__main__":
    # 非流式示例
    result = chat_completion("你好，AI Hub！")
    print(result['choices'][0]['message']['content'])

    # 流式示例
    print("\n--- 流式响应 ---")
    stream_chat("给我讲个短故事")
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

// 配置
const API_KEY = 'your-api-key-here';
const BASE_URL = 'https://api.ai-hub.com/v1';

// 头部
const headers = {
  'Authorization': `Bearer ${API_KEY}`,
  'Content-Type': 'application/json'
};

// 非流式聊天补全
async function chatCompletion(message, model = 'gpt-4') {
  try {
    const response = await axios.post(`${BASE_URL}/chat/completions`, {
      model: model,
      messages: [{ role: 'user', content: message }],
      max_tokens: 1000,
      temperature: 0.7
    }, { headers });

    return response.data;
  } catch (error) {
    console.error('错误:', error.response?.data || error.message);
    throw error;
  }
}

// 流式聊天补全
async function streamChat(message, model = 'gpt-4') {
  try {
    const response = await axios.post(`${BASE_URL}/chat/stream`, {
      model: model,
      messages: [{ role: 'user', content: message }],
      stream: true
    }, {
      headers,
      responseType: 'stream'
    });

    response.data.on('data', (chunk) => {
      const lines = chunk.toString().split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            process.exit(0);
          }
          try {
            const parsed = JSON.parse(data);
            if (parsed.choices && parsed.choices[0]?.delta?.content) {
              process.stdout.write(parsed.choices[0].delta.content);
            }
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
    });

  } catch (error) {
    console.error('错误:', error.response?.data || error.message);
    throw error;
  }
}

// 使用
(async () => {
  // 非流式示例
  const result = await chatCompletion('你好，AI Hub！');
  console.log(result.choices[0].message.content);

  // 流式示例
  console.log('\n--- 流式响应 ---');
  await streamChat('给我讲个短故事');
})();
```

### cURL

```bash
# 非流式聊天补全
curl -X POST "https://api.ai-hub.com/v1/chat/completions" \
  -H "Authorization: Bearer your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "你好，AI Hub！"}
    ],
    "max_tokens": 1000,
    "temperature": 0.7
  }'

# 流式聊天补全
curl -X POST "https://api.ai-hub.com/v1/chat/stream" \
  -H "Authorization: Bearer your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "给我讲个故事"}
    ],
    "stream": true
  }'

# 列出模型
curl -X GET "https://api.ai-hub.com/v1/models" \
  -H "Authorization: Bearer your-api-key-here"

# 获取使用统计
curl -X GET "https://api.ai-hub.com/v1/usage" \
  -H "Authorization: Bearer your-api-key-here"
```

## SDK 和库

我们为流行的编程语言提供官方 SDK：

### Python SDK

```bash
pip install ai-hub
```

```python
from ai_hub import AIHubClient

client = AIHubClient(api_key="your-api-key-here")

# 简单聊天
response = client.chat.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "你好！"}]
)

print(response.choices[0].message.content)
```

### JavaScript SDK

```bash
npm install @ai-hub/client
```

```javascript
import { AIHubClient } from '@ai-hub/client';

const client = new AIHubClient({
  apiKey: 'your-api-key-here'
});

// 简单聊天
const response = await client.chat.create({
  model: 'gpt-4',
  messages: [{ role: 'user', content: '你好！' }]
});

console.log(response.choices[0].message.content);
```

### Go SDK

```bash
go get github.com/ai-hub/go-sdk
```

```go
package main

import (
    "fmt"
    "github.com/ai-hub/go-sdk"
)

func main() {
    client := aihub.NewClient("your-api-key-here")

    response, err := client.CreateChatCompletion(&aihub.ChatCompletionRequest{
        Model: "gpt-4",
        Messages: []aihub.ChatMessage{
            {Role: "user", Content: "你好！"},
        },
    })

    if err != nil {
        panic(err)
    }

    fmt.Println(response.Choices[0].Message.Content)
}
```

## 其他资源

- **交互式 API 控制台**：[console.ai-hub.com](https://console.ai-hub.com)
- **社区论坛**：[community.ai-hub.com](https://community.ai-hub.com)
- **状态页面**：[status.ai-hub.com](https://status.ai-hub.com)
- **支持**：support@ai-hub.com

---

*API 文档定期更新。最后更新：2024年12月*