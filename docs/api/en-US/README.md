# AI Hub API Documentation

Welcome to the AI Hub API documentation. This comprehensive guide will help you integrate our powerful AI capabilities into your applications.

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication](#authentication)
3. [Base URLs](#base-urls)
4. [Available Endpoints](#available-endpoints)
5. [Rate Limits](#rate-limits)
6. [Error Handling](#error-handling)
7. [Code Examples](#code-examples)
8. [SDKs and Libraries](#sdks-and-libraries)

## API Overview

The AI Hub API provides programmatic access to 140+ AI models through a unified RESTful interface. Our API supports:

- **Multiple AI Models** - Access to GPT-4, Claude, Gemini, and more
- **Streaming Responses** - Real-time response streaming
- **Session Management** - Persistent conversation context
- **Cost Tracking** - Transparent usage monitoring
- **Global Availability** - Multi-region endpoints

### Key Features

- 🔑 **Simple Authentication** - Bearer token authentication
- 📊 **Usage Analytics** - Real-time usage tracking
- 🌍 **Multi-Language Support** - International response formats
- 🔄 **Streaming and Non-Streaming** - Choose your response mode
- 📝 **Rich Context** - Maintain conversation history
- ⚡ **High Performance** - Optimized for speed and reliability

## Authentication

All API requests require authentication using a Bearer token.

### Getting Your API Key

1. Log in to your [AI Hub Dashboard](https://dashboard.ai-hub.com)
2. Navigate to **API Keys** section
3. Click **Generate New Key**
4. Copy your API key immediately

### Using Your API Key

Include your API key in the `Authorization` header:

```http
Authorization: Bearer your-api-key-here
```

**⚠️ Security Note**: Never expose your API key in client-side code or public repositories.

## Base URLs

Our API is available in multiple regions for optimal performance:

### Primary Endpoints

- **Global**: `https://api.ai-hub.com/v1`
- **US East**: `https://api-us-east.ai-hub.com/v1`
- **Europe**: `https://api-eu.ai-hub.com/v1`
- **Asia Pacific**: `https://api-ap-southeast.ai-hub.com/v1`

### Regional Selection

Choose the endpoint closest to your users for better performance. All endpoints provide the same functionality.

## Available Endpoints

### Chat Completions

Create chat completions with various AI models.

#### Non-Streaming Chat

```http
POST /chat/completions
```

**Request Body:**
```json
{
  "model": "gpt-4",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Hello, AI Hub!"
    }
  ],
  "max_tokens": 1000,
  "temperature": 0.7,
  "stream": false
}
```

**Response:**
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
        "content": "Hello! I'm here to help you with AI Hub. How can I assist you today?"
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

#### Streaming Chat

```http
POST /chat/stream
```

**Request Body:**
```json
{
  "model": "gpt-4",
  "messages": [
    {
      "role": "user",
      "content": "Tell me a story"
    }
  ],
  "stream": true
}
```

**Response (Server-Sent Events):**
```
data: {"id": "chatcmpl-123", "choices": [{"delta": {"content": "Once"}}]}

data: {"id": "chatcmpl-123", "choices": [{"delta": {"content": " upon"}}]}

data: {"id": "chatcmpl-123", "choices": [{"delta": {"content": " a"}}]}

data: [DONE]
```

### Models

List all available AI models.

```http
GET /models
```

**Response:**
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

### Usage

Get your current usage statistics.

```http
GET /usage
```

**Response:**
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

### Sessions

Manage conversation sessions for context persistence.

#### Create Session

```http
POST /sessions
```

**Request Body:**
```json
{
  "title": "Customer Support Chat",
  "model": "gpt-4",
  "system_prompt": "You are a helpful customer support assistant."
}
```

#### Get Session

```http
GET /sessions/{session_id}
```

#### Update Session

```http
PUT /sessions/{session_id}
```

#### Delete Session

```http
DELETE /sessions/{session_id}
```

## Rate Limits

To ensure fair usage and system stability, we implement rate limits:

### Rate Limit Tiers

| Plan | Requests per Minute | Tokens per Minute |
|------|---------------------|-------------------|
| Free | 10 | 10,000 |
| Developer | 100 | 100,000 |
| Pro | 500 | 500,000 |
| Enterprise | Unlimited | Unlimited |

### Rate Limit Headers

All API responses include rate limit headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

### Handling Rate Limits

When you hit a rate limit, you'll receive a `429 Too Many Requests` response:

```json
{
  "error": {
    "message": "Rate limit exceeded. Try again in 60 seconds.",
    "type": "rate_limit_exceeded",
    "retry_after": 60
  }
}
```

## Error Handling

Our API returns standard HTTP status codes and detailed error messages.

### HTTP Status Codes

- `200 OK` - Request successful
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Invalid API key
- `403 Forbidden` - API key doesn't have permission
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

### Error Response Format

```json
{
  "error": {
    "message": "Invalid model specified",
    "type": "invalid_request_error",
    "param": "model",
    "code": "model_not_found"
  }
}
```

### Error Types

- `invalid_request_error` - Invalid request parameters
- `authentication_error` - Authentication failed
- `permission_error` - Insufficient permissions
- `rate_limit_error` - Rate limit exceeded
- `api_error` - API-related errors
- `model_error` - Model-specific errors

## Code Examples

### Python

```python
import requests
import json

# Configuration
API_KEY = "your-api-key-here"
BASE_URL = "https://api.ai-hub.com/v1"

# Headers
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Non-streaming chat completion
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

# Streaming chat completion
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
                data = line[6:]  # Remove 'data: ' prefix
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

# Usage
if __name__ == "__main__":
    # Non-streaming example
    result = chat_completion("Hello, AI Hub!")
    print(result['choices'][0]['message']['content'])

    # Streaming example
    print("\n--- Streaming Response ---")
    stream_chat("Tell me a short story")
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

// Configuration
const API_KEY = 'your-api-key-here';
const BASE_URL = 'https://api.ai-hub.com/v1';

// Headers
const headers = {
  'Authorization': `Bearer ${API_KEY}`,
  'Content-Type': 'application/json'
};

// Non-streaming chat completion
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
    console.error('Error:', error.response?.data || error.message);
    throw error;
  }
}

// Streaming chat completion
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
            // Ignore parsing errors
          }
        }
      }
    });

  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
    throw error;
  }
}

// Usage
(async () => {
  // Non-streaming example
  const result = await chatCompletion('Hello, AI Hub!');
  console.log(result.choices[0].message.content);

  // Streaming example
  console.log('\n--- Streaming Response ---');
  await streamChat('Tell me a short story');
})();
```

### cURL

```bash
# Non-streaming chat completion
curl -X POST "https://api.ai-hub.com/v1/chat/completions" \
  -H "Authorization: Bearer your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "Hello, AI Hub!"}
    ],
    "max_tokens": 1000,
    "temperature": 0.7
  }'

# Streaming chat completion
curl -X POST "https://api.ai-hub.com/v1/chat/stream" \
  -H "Authorization: Bearer your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "Tell me a story"}
    ],
    "stream": true
  }'

# List models
curl -X GET "https://api.ai-hub.com/v1/models" \
  -H "Authorization: Bearer your-api-key-here"

# Get usage statistics
curl -X GET "https://api.ai-hub.com/v1/usage" \
  -H "Authorization: Bearer your-api-key-here"
```

## SDKs and Libraries

We provide official SDKs for popular programming languages:

### Python SDK

```bash
pip install ai-hub
```

```python
from ai_hub import AIHubClient

client = AIHubClient(api_key="your-api-key-here")

# Simple chat
response = client.chat.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
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

// Simple chat
const response = await client.chat.create({
  model: 'gpt-4',
  messages: [{ role: 'user', content: 'Hello!' }]
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
            {Role: "user", Content: "Hello!"},
        },
    })

    if err != nil {
        panic(err)
    }

    fmt.Println(response.Choices[0].Message.Content)
}
```

## Additional Resources

- **Interactive API Console**: [console.ai-hub.com](https://console.ai-hub.com)
- **Community Forum**: [community.ai-hub.com](https://community.ai-hub.com)
- **Status Page**: [status.ai-hub.com](https://status.ai-hub.com)
- **Support**: support@ai-hub.com

---

*API documentation is regularly updated. Last updated: December 2024*