# AI Hub 开发者API文档

> 统一的多AI模型API接口，支持20+主流AI模型，提供流式响应、成本跟踪等企业级功能

## 🚀 快速开始

### 1. 获取API密钥

```bash
# 注册账户并获取API密钥
curl -X POST https://api.ai-hub.dev/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "your-password"}'

# 创建API密钥
curl -X POST https://api.ai-hub.dev/v1/developer/api-keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"name": "My App Key"}'
```

### 2. 发送第一个请求

```bash
curl -X POST https://api.ai-hub.dev/v1/developer/chat \
  -H "Authorization: Bearer ai-hub-xxx-xxx-xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, AI Hub!",
    "model": "x-ai/grok-beta",
    "max_tokens": 150
  }'
```

## 📋 API端点

### 基础URL
```
生产环境: https://api.ai-hub.dev/v1/developer
测试环境: https://dev-api.ai-hub.dev/v1/developer
```

### 认证
所有API请求都需要在头部包含API密钥：
```
Authorization: Bearer ai-hub-xxx-xxx-xxx
```

## 💬 聊天API

### POST /chat
发送消息并获取AI回复

**请求参数**:
```json
{
  "message": "用户消息内容",
  "model": "x-ai/grok-beta",           // 可选，默认grok-beta
  "service": "openrouter",             // 可选，openrouter|gemini
  "max_tokens": 1000,                  // 可选，最大输出长度
  "temperature": 0.7,                  // 可选，生成温度 0-1
  "stream": false,                     // 可选，是否流式响应
  "session_id": "session_123",         // 可选，会话ID
  "images": ["base64_image_data"],     // 可选，图片数据
  "context": {                         // 可选，额外上下文
    "system_prompt": "你是一个专业的AI助手"
  }
}
```

**响应**:
```json
{
  "message": "AI助手的回复内容",
  "model": "openrouter:x-ai/grok-beta",
  "session_id": "session_123",
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 150,
    "total_tokens": 175,
    "estimated_cost_usd": 0.00035
  },
  "metadata": {
    "response_time_ms": 1250,
    "service_used": "openrouter"
  }
}
```

### POST /chat/stream
流式聊天响应 (Server-Sent Events)

**请求参数**: 同上，`stream` 字段自动为 `true`

**响应流**:
```
data: {"type": "content", "content": "Hello", "model": "grok-beta"}

data: {"type": "content", "content": " there!", "model": "grok-beta"}

data: {"type": "session", "session_id": "session_123"}

data: {"type": "usage", "usage": {"total_tokens": 25, "estimated_cost_usd": 0.0001}}

data: {"type": "done"}
```

## 🤖 模型API

### GET /models
获取可用模型列表

**查询参数**:
- `service`: 可选，过滤特定服务 (openrouter|gemini)
- `category`: 可选，模型分类 (chat|completion|embedding)

**响应**:
```json
{
  "service": "openrouter",
  "models": [
    {
      "id": "x-ai/grok-beta",
      "name": "Grok Beta",
      "description": "X.AI的最新对话模型",
      "context_length": 131072,
      "pricing": {
        "prompt": 0.000002,
        "completion": 0.000002
      },
      "capabilities": ["chat", "multimodal"]
    }
  ],
  "total_count": 23
}
```

### GET /services
获取可用AI服务列表

**响应**:
```json
{
  "services": ["openrouter", "gemini"],
  "default": "openrouter",
  "capabilities": {
    "openrouter": {
      "text_generation": true,
      "streaming": true,
      "multi_model": true,
      "cost_efficient": true
    },
    "gemini": {
      "text_generation": true,
      "streaming": true,
      "multimodal": true
    }
  }
}
```

## 📊 使用统计API

### GET /usage
获取API使用统计

**查询参数**:
- `period`: 时间周期 (day|week|month|year)
- `start_date`: 开始日期 (YYYY-MM-DD)
- `end_date`: 结束日期 (YYYY-MM-DD)

**响应**:
```json
{
  "period": "month",
  "total_requests": 1250,
  "total_tokens": 125000,
  "total_cost_usd": 2.35,
  "quota_limit": 10000,
  "quota_used": 1250,
  "quota_remaining": 8750,
  "daily_breakdown": [
    {
      "date": "2025-09-01",
      "requests": 45,
      "tokens": 4500,
      "cost_usd": 0.09
    }
  ]
}
```

### GET /quota
获取当前配额信息

**响应**:
```json
{
  "plan": "professional",
  "quota_limit": 10000,
  "quota_used": 1250,
  "quota_remaining": 8750,
  "reset_date": "2025-10-01T00:00:00Z",
  "rate_limit": {
    "requests_per_minute": 60,
    "tokens_per_minute": 15000
  }
}
```

## 🔑 API密钥管理

### POST /api-keys
创建新的API密钥

**请求**:
```json
{
  "name": "My App Key",
  "permissions": ["chat", "models", "usage"],
  "rate_limit": {
    "requests_per_minute": 30
  }
}
```

**响应**:
```json
{
  "id": "key_123",
  "name": "My App Key",
  "key": "ai-hub-xxx-xxx-xxx",
  "created_at": "2025-09-29T10:00:00Z",
  "permissions": ["chat", "models", "usage"],
  "last_used": null
}
```

### GET /api-keys
列出所有API密钥

### DELETE /api-keys/{key_id}
删除指定API密钥

## ⚡ 速率限制

| 套餐 | 请求/分钟 | Token/分钟 | 并发请求 |
|------|-----------|------------|----------|
| 免费版 | 20 | 5,000 | 3 |
| 专业版 | 60 | 15,000 | 10 |
| 企业版 | 200 | 50,000 | 25 |

**速率限制响应头**:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1640995200
```

## 🚨 错误处理

### 错误格式
```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "invalid_api_key",
    "message": "Invalid API key provided",
    "details": {
      "parameter": "Authorization",
      "suggestion": "Check your API key format"
    }
  },
  "request_id": "req_123456"
}
```

### 常见错误码

| 状态码 | 错误类型 | 说明 |
|--------|----------|------|
| 400 | invalid_request_error | 请求参数错误 |
| 401 | authentication_error | API密钥无效或过期 |
| 403 | permission_error | 权限不足 |
| 429 | rate_limit_error | 请求频率超限 |
| 500 | api_error | 服务器内部错误 |

## 💰 计费说明

### 计费模式
- **Token计费**: 按输入+输出Token数量计费
- **模型差价**: 不同模型有不同单价
- **实时跟踪**: 每次请求返回精确成本

### 价格示例
```json
{
  "model_pricing": {
    "x-ai/grok-beta": {
      "input_token_price": 0.000002,
      "output_token_price": 0.000002,
      "currency": "USD"
    },
    "anthropic/claude-3-sonnet": {
      "input_token_price": 0.000003,
      "output_token_price": 0.000015,
      "currency": "USD"
    }
  }
}
```

## 🔧 SDK和工具

### Python SDK
```python
pip install ai-hub-python

from ai_hub import AIHub

client = AIHub(api_key="ai-hub-xxx-xxx-xxx")

response = client.chat.create(
    message="Hello, world!",
    model="x-ai/grok-beta",
    max_tokens=150
)

print(response.message)
```

### JavaScript SDK
```javascript
npm install ai-hub-js

import { AIHub } from 'ai-hub-js';

const client = new AIHub({ apiKey: 'ai-hub-xxx-xxx-xxx' });

const response = await client.chat.create({
  message: 'Hello, world!',
  model: 'x-ai/grok-beta',
  maxTokens: 150
});

console.log(response.message);
```

## 📚 示例代码

### 基础聊天
```python
import requests

response = requests.post(
    'https://api.ai-hub.dev/v1/developer/chat',
    headers={
        'Authorization': 'Bearer ai-hub-xxx-xxx-xxx',
        'Content-Type': 'application/json'
    },
    json={
        'message': '用Python写一个快速排序算法',
        'model': 'x-ai/grok-beta',
        'max_tokens': 500
    }
)

result = response.json()
print(result['message'])
```

### 流式响应
```python
import requests

response = requests.post(
    'https://api.ai-hub.dev/v1/developer/chat/stream',
    headers={
        'Authorization': 'Bearer ai-hub-xxx-xxx-xxx',
        'Content-Type': 'application/json'
    },
    json={
        'message': '讲一个关于AI的故事',
        'model': 'x-ai/grok-beta'
    },
    stream=True
)

for line in response.iter_lines():
    if line.startswith(b'data: '):
        data = json.loads(line[6:])
        if data['type'] == 'content':
            print(data['content'], end='')
```

### 多模态输入
```python
import base64

# 读取图片并转换为base64
with open('image.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode()

response = requests.post(
    'https://api.ai-hub.dev/v1/developer/chat',
    headers={
        'Authorization': 'Bearer ai-hub-xxx-xxx-xxx',
        'Content-Type': 'application/json'
    },
    json={
        'message': '这张图片里有什么？',
        'model': 'x-ai/grok-vision-beta',
        'images': [image_data]
    }
)
```

## 🛡️ 安全最佳实践

1. **API密钥安全**
   - 不要在客户端代码中暴露API密钥
   - 使用环境变量存储密钥
   - 定期轮换API密钥

2. **输入验证**
   - 验证用户输入内容
   - 过滤敏感信息
   - 限制输入长度

3. **监控使用**
   - 监控API使用量和成本
   - 设置使用阈值告警
   - 定期检查使用日志

## 📞 支持和反馈

- **技术文档**: https://docs.ai-hub.dev
- **状态页面**: https://status.ai-hub.dev
- **技术支持**: support@ai-hub.dev
- **社区论坛**: https://community.ai-hub.dev

---

*更新时间: 2025-09-29*
*版本: v2.0*