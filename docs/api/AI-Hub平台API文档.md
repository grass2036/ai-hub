# AI Hub 平台 API 文档

## 概述

AI Hub 平台提供全面的 REST API，用于通过统一接口访问多个 AI 模型。此 API 允许开发者将聊天补全、会话管理、使用跟踪和批处理功能集成到他们的应用程序中。

**基础 URL**: `https://api.aihub.com/api/v1`
**开发环境 URL**: `http://localhost:8001/api/v1`

## 身份验证

AI Hub API 使用 API 密钥进行开发者访问的身份验证。

### 获取您的 API 密钥

1. 在 [AI Hub 开发者门户](https://aihub.com/developers) 注册
2. 导航到 API 密钥部分
3. 创建具有所需权限的新 API 密钥
4. 在您的请求中包含 API 密钥：

```http
Authorization: Bearer your_api_key_here
```

### API 密钥权限

- `chat`: 访问聊天补全端点
- `usage`: 查看使用统计和分析
- `batch`: 创建和管理批处理作业
- `monitoring`: 访问系统监控端点

## 核心 API 端点

### 聊天补全

#### 流式聊天补全

用于聊天对话的实时流式响应。

```http
POST /chat/stream
```

**请求体**:
```json
{
  "message": "您的消息内容",
  "model": "gpt-4o",
  "session_id": "可选的会话 UUID",
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": true
}
```

**响应**: 服务器发送事件 (SSE) 流
```text
data: {"type": "start", "session_id": "uuid"}
data: {"type": "chunk", "content": "你好"}
data: {"type": "chunk", "content": "！"}
data: {"type": "end", "usage": {"tokens": 150, "cost": 0.002}}
```

**示例 (cURL)**:
```bash
curl -X POST "http://localhost:8001/api/v1/chat/stream" \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "解释量子计算",
    "model": "gpt-4o"
  }'
```

#### 标准聊天补全

用于简单请求-响应模式的非流式聊天补全。

```http
POST /chat/completions
```

**请求体**:
```json
{
  "message": "您的消息内容",
  "model": "gpt-4o",
  "session_id": "可选的会话 UUID",
  "temperature": 0.7,
  "max_tokens": 1000
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "content": "完整的回复内容...",
    "session_id": "uuid",
    "model": "gpt-4o",
    "usage": {
      "prompt_tokens": 50,
      "completion_tokens": 100,
      "total_tokens": 150,
      "estimated_cost": 0.002
    },
    "metadata": {
      "response_time": 1.23,
      "service": "openrouter"
    }
  }
}
```

### 可用模型

列出所有可用的 AI 模型及其功能和定价。

```http
GET /models
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": "gpt-4o",
      "name": "GPT-4o",
      "provider": "OpenRouter",
      "description": "高级多模态模型",
      "context_length": 128000,
      "pricing": {
        "input": 0.015,
        "output": 0.06
      },
      "capabilities": ["text", "vision", "code"],
      "is_free": false
    }
  ]
}
```

### 会话管理

#### 创建会话

创建新的对话会话。

```http
POST /sessions
```

**请求体**:
```json
{
  "title": "可选的会话标题",
  "model": "gpt-4o"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "session_id": "uuid",
    "title": "会话标题",
    "created_at": "2024-01-01T00:00:00Z",
    "model": "gpt-4o"
  }
}
```

#### 获取会话

检索会话详情和消息历史。

```http
GET /sessions/{session_id}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "session_id": "uuid",
    "title": "会话标题",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T01:00:00Z",
    "model": "gpt-4o",
    "message_count": 10,
    "total_tokens": 1500,
    "estimated_cost": 0.05,
    "messages": [
      {
        "role": "user",
        "content": "你好，你好吗？",
        "timestamp": "2024-01-01T00:30:00Z",
        "tokens": 10
      },
      {
        "role": "assistant",
        "content": "你好！我很好，谢谢...",
        "timestamp": "2024-01-01T00:30:05Z",
        "tokens": 25
      }
    ]
  }
}
```

#### 列出会话

获取认证开发者的所有会话。

```http
GET /sessions
```

**查询参数**:
- `limit`: 返回的会话数量（默认：20）
- `offset`: 分页偏移量（默认：0）
- `sort`: 排序字段（created_at, updated_at, message_count）
- `order`: 排序顺序（asc, desc）

#### 删除会话

删除会话及所有相关消息。

```http
DELETE /sessions/{session_id}
```

### 使用统计

#### 使用概览

获取全面的使用统计信息。

```http
GET /usage/overview
```

**查询参数**:
- `days`: 分析天数（默认：30）

**响应**:
```json
{
  "success": true,
  "data": {
    "period": {
      "start_date": "2024-01-01",
      "end_date": "2024-01-31"
    },
    "total_requests": 1500,
    "total_tokens": 150000,
    "total_cost": 25.50,
    "average_request_tokens": 100,
    "top_models": [
      {
        "model": "gpt-4o",
        "requests": 800,
        "tokens": 80000,
        "cost": 15.00
      }
    ],
    "daily_breakdown": [
      {
        "date": "2024-01-01",
        "requests": 50,
        "tokens": 5000,
        "cost": 0.85
      }
    ]
  }
}
```

#### 使用分析

包含图表和趋势的详细分析。

```http
GET /usage/analytics
```

**响应**:
```json
{
  "success": true,
  "data": {
    "usage_trends": {
      "daily": [
        {
          "date": "2024-01-01",
          "requests": 50,
          "tokens": 5000,
          "cost": 0.85
        }
      ],
      "hourly": [
        {
          "hour": "2024-01-01T00:00:00Z",
          "requests": 5,
          "tokens": 500,
          "cost": 0.085
        }
      ]
    },
    "model_distribution": {
      "gpt-4o": 60.5,
      "gpt-4o-mini": 25.2,
      "claude-3-haiku": 14.3
    },
    "cost_analysis": {
      "total_cost": 25.50,
      "average_cost_per_request": 0.017,
      "cost_trend": "increasing"
    }
  }
}
```

### 批处理

#### 创建批处理作业

为多个提示创建批处理作业。

```http
POST /batch/generation
```

**请求体**:
```json
{
  "name": "内容生成批处理",
  "model": "gpt-4o-mini",
  "prompts": [
    "为 iPhone 编写产品描述",
    "创建夏季促销营销邮件",
    "生成关于 AI 趋势的博客文章"
  ],
  "max_concurrent_tasks": 5,
  "temperature": 0.7,
  "max_tokens": 500
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "job_id": "batch_job_uuid",
    "name": "内容生成批处理",
    "status": "queued",
    "total_tasks": 3,
    "created_at": "2024-01-01T00:00:00Z",
    "estimated_completion": "2024-01-01T00:15:00Z"
  }
}
```

#### 获取批处理作业

列出认证开发者的所有批处理作业。

```http
GET /batch/jobs
```

#### 获取批处理作业状态

获取特定批处理作业的详细状态和结果。

```http
GET /batch/jobs/{job_id}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "job_id": "batch_job_uuid",
    "name": "内容生成批处理",
    "status": "completed",
    "progress": {
      "completed_tasks": 3,
      "failed_tasks": 0,
      "total_tasks": 3,
      "progress_percentage": 100
    },
    "results": [
      {
        "task_id": 1,
        "prompt": "为 iPhone 编写产品描述",
        "result": "产品描述内容...",
        "status": "completed",
        "tokens_used": 150,
        "cost": 0.002
      }
    ],
    "total_cost": 0.006,
    "created_at": "2024-01-01T00:00:00Z",
    "completed_at": "2024-01-01T00:12:30Z"
  }
}
```

#### 取消批处理作业

取消正在运行的批处理作业。

```http
POST /batch/jobs/{job_id}/cancel
```

### 开发者 API 密钥

#### 创建 API 密钥

为您的应用程序创建新的 API 密钥。

```http
POST /developer/keys
```

**请求体**:
```json
{
  "name": "生产环境 API 密钥",
  "permissions": ["chat", "usage"],
  "rate_limit": {
    "requests_per_minute": 1000,
    "tokens_per_minute": 100000
  }
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": "key_uuid",
    "name": "生产环境 API 密钥",
    "key": "sk_aihub_1234567890abcdef",
    "key_prefix": "sk_aihub_1234",
    "permissions": ["chat", "usage"],
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

#### 列出 API 密钥

获取您账户的所有 API 密钥。

```http
GET /developer/keys
```

#### 删除 API 密钥

删除 API 密钥。

```http
DELETE /developer/keys/{key_id}
```

### 系统监控

#### 系统指标

获取系统性能和健康指标。

```http
GET /monitoring/metrics
```

**响应**:
```json
{
  "success": true,
  "data": {
    "system": {
      "uptime": 86400,
      "cpu_usage": 45.2,
      "memory_usage": 68.5,
      "disk_usage": 32.1
    },
    "api": {
      "requests_per_minute": 150,
      "average_response_time": 0.85,
      "error_rate": 0.02
    },
    "services": {
      "openrouter": {
        "status": "healthy",
        "response_time": 0.65,
        "success_rate": 0.99
      },
      "gemini": {
        "status": "healthy",
        "response_time": 0.45,
        "success_rate": 0.98
      }
    }
  }
}
```

#### 系统状态

获取当前系统状态和任何正在进行的问题。

```http
GET /status
```

## 错误处理

### 标准错误响应格式

所有 API 错误都遵循此统一格式：

```json
{
  "success": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "请求无效",
    "details": {
      "field": "message",
      "reason": "此字段是必需的"
    },
    "request_id": "req_1234567890"
  }
}
```

### 常见 HTTP 状态码

| 状态码 | 含义 | 描述 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 400 | Bad Request | 请求参数无效 |
| 401 | Unauthorized | API 密钥无效或缺失 |
| 403 | Forbidden | 权限不足 |
| 404 | Not Found | 资源未找到 |
| 429 | Too Many Requests | 超过速率限制 |
| 500 | Internal Server Error | 服务器错误 |

### 速率限制

API 请求根据您的订阅计划进行速率限制：

- **免费层**：100 请求/分钟，10,000 tokens/分钟
- **开发者计划**：1,000 请求/分钟，100,000 tokens/分钟
- **专业计划**：5,000 请求/分钟，500,000 tokens/分钟
- **企业版**：自定义限制

速率限制头包含在响应中：
```http
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1640995200
X-RateLimit-Limit: 1000
```

## SDK 和库

### Python SDK

```python
from aihub import AIHubClient

client = AIHubClient(api_key="your_api_key")

# 聊天补全
response = client.chat.completions.create(
    message="解释量子计算",
    model="gpt-4o"
)
print(response.content)

# 流式
for chunk in client.chat.completions.stream(
    message="给我讲个故事",
    model="gpt-4o"
):
    print(chunk.content, end="")
```

### JavaScript SDK

```javascript
import { AIHubClient } from '@aihub/client';

const client = new AIHubClient('your_api_key');

// 聊天补全
const response = await client.chat.completions.create({
  message: '解释量子计算',
  model: 'gpt-4o'
});
console.log(response.content);

// 流式
const stream = await client.chat.completions.stream({
  message: '给我讲个故事',
  model: 'gpt-4o'
});

for await (const chunk of stream) {
  process.stdout.write(chunk.content);
}
```

### cURL 示例

请参见上面的端点文档了解具体的 cURL 示例。

## 最佳实践

### 1. API 密钥安全

- 永远不要在客户端代码中暴露 API 密钥
- 使用环境变量存储 API 密钥
- 定期轮换 API 密钥
- 为不同的应用程序使用作用域权限

### 2. 错误处理

```python
import aihub
from aihub.exceptions import APIError, RateLimitError

try:
    response = client.chat.completions.create(...)
except RateLimitError:
    # 实现指数退避
    time.sleep(2)
except APIError as e:
    print(f"API 错误：{e.message}")
```

### 3. 流式最佳实践

- 对长响应使用流式传输以改善用户体验
- 优雅地处理连接超时
- 对掉落的连接实施适当的错误处理
- 对于实时应用考虑使用 WebSocket

### 4. 成本优化

- 为您的用例选择合适的模型
- 对简单任务使用较小的模型
- 定期监控您的使用情况
- 在仪表板中设置使用警报

### 5. 性能

- 尽可能重用 HTTP 连接
- 对重复请求实施缓存
- 使用适当的超时值
- 对于多个请求考虑批处理

## 支持

- **文档**: https://docs.aihub.com
- **API 参考**: https://api.aihub.com/docs
- **状态页面**: https://status.aihub.com
- **支持邮箱**: support@aihub.com
- **开发者社区**: https://community.aihub.com

## 更新日志

### v1.0.0 (2024-01-01)
- 初始 API 发布
- 聊天补全（流式和非流式）
- 会话管理
- 使用统计
- 批处理
- 开发者 API 密钥

### v1.1.0 (即将推出)
- WebSocket 支持
- 函数调用
- 图像生成
- 向量搜索
- 微调支持