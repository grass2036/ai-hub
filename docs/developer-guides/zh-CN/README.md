# AI Hub 开发者指南

欢迎使用 AI Hub 开发者指南！本综合资源将帮助您使用我们的平台构建强大的 AI 驱动应用程序。

## 目录

1. [入门指南](#入门指南)
2. [快速入门教程](#快速入门教程)
3. [高级集成](#高级集成)
4. [最佳实践](#最佳实践)
5. [故障排除](#故障排除)
6. [示例和模板](#示例和模板)

## 入门指南

### 前置条件

在开始使用 AI Hub 构建应用之前，请确保您具备：

- **AI Hub 账户** - 在 [ai-hub.com](https://ai-hub.com) 注册
- **API 密钥** - 从您的仪表板生成
- **开发环境** - 您首选的 IDE 和工具
- **基础编程知识** - 了解 REST API

### 开发环境设置

#### 环境变量

永远不要硬编码您的 API 密钥！使用环境变量：

```bash
# .env 文件
AI_HUB_API_KEY=your-api-key-here
AI_HUB_BASE_URL=https://api.ai-hub.com/v1
```

#### 推荐库

**Python：**
```bash
pip install requests python-dotenv ai-hub
```

**Node.js：**
```bash
npm install axios dotenv @ai-hub/client
```

**Go：**
```bash
go get github.com/ai-hub/go-sdk
```

### API 密钥安全

- 🔐 **安全存储** - 使用环境变量或密钥管理
- 🔄 **定期轮换** - 每 90 天更新密钥
- 📍 **权限范围** - 使用最小所需权限
- 📊 **监控使用情况** - 在仪表板中跟踪 API 密钥使用
- 🚫 **永远不要提交** - 将 API 密钥排除在版本控制之外

## 快速入门教程

让我们一步步构建一个简单的 AI 聊天机器人应用程序。

### 步骤 1：初始化您的项目

#### Python 项目

```bash
mkdir ai-hub-chatbot
cd ai-hub-chatbot

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install requests python-dotenv streamlit
```

#### Node.js 项目

```bash
mkdir ai-hub-chatbot
cd ai-hub-chatbot

# 初始化 npm 项目
npm init -y

# 安装依赖
npm install express axios dotenv cors
```

### 步骤 2：创建聊天功能

#### Python 实现

```python
# chat_service.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

class AIHubChatService:
    def __init__(self):
        self.api_key = os.getenv('AI_HUB_API_KEY')
        self.base_url = os.getenv('AI_HUB_BASE_URL', 'https://api.ai-hub.com/v1')

        if not self.api_key:
            raise ValueError("需要 AI_HUB_API_KEY 环境变量")

    def chat(self, message, model="gpt-4", conversation_history=None):
        """向 AI 发送消息并获取响应"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 构建消息数组
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()

            result = response.json()
            return result['choices'][0]['message']['content']

        except requests.exceptions.RequestException as e:
            print(f"调用 AI Hub API 时出错：{e}")
            return "抱歉，我现在无法连接。"

    def stream_chat(self, message, model="gpt-4", conversation_history=None):
        """流式聊天响应"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})

        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/stream",
                json=payload,
                headers=headers,
                stream=True
            )
            response.raise_for_status()

            full_response = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        try:
                            import json
                            chunk = json.loads(data)
                            if 'choices' in chunk and len(chunk['choices']) > 0:
                                delta = chunk['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    full_response += content
                                    yield content
                        except json.JSONDecodeError:
                            continue

            return full_response

        except requests.exceptions.RequestException as e:
            print(f"流式传输错误：{e}")
            yield "错误：无法流式传输响应"

# 使用示例
if __name__ == "__main__":
    chat_service = AIHubChatService()

    # 简单聊天
    response = chat_service.chat("你好，AI Hub！")
    print(f"AI：{response}")

    # 流式聊天
    print("AI（流式）：", end="")
    for chunk in chat_service.stream_chat("给我讲个短故事"):
        print(chunk, end="", flush=True)
    print()
```

#### Node.js 实现

```javascript
// chatService.js
require('dotenv').config();
const axios = require('axios');

class AIHubChatService {
    constructor() {
        this.apiKey = process.env.AI_HUB_API_KEY;
        this.baseURL = process.env.AI_HUB_BASE_URL || 'https://api.ai-hub.com/v1';

        if (!this.apiKey) {
            throw new Error('需要 AI_HUB_API_KEY 环境变量');
        }
    }

    async chat(message, model = 'gpt-4', conversationHistory = []) {
        const headers = {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json'
        };

        const messages = [...conversationHistory, { role: 'user', content: message }];

        const payload = {
            model,
            messages,
            max_tokens: 1000,
            temperature: 0.7
        };

        try {
            const response = await axios.post(
                `${this.baseURL}/chat/completions`,
                payload,
                { headers }
            );

            return response.data.choices[0].message.content;

        } catch (error) {
            console.error('调用 AI Hub API 时出错：', error.response?.data || error.message);
            return '抱歉，我现在无法连接。';
        }
    }

    async* streamChat(message, model = 'gpt-4', conversationHistory = []) {
        const headers = {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json'
        };

        const messages = [...conversationHistory, { role: 'user', content: message }];

        const payload = {
            model,
            messages,
            stream: true
        };

        try {
            const response = await axios.post(
                `${this.baseURL}/chat/stream`,
                payload,
                {
                    headers,
                    responseType: 'stream'
                }
            );

            let fullResponse = '';

            for await (const chunk of response.data) {
                const lines = chunk.toString().split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') {
                            return fullResponse;
                        }
                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.choices && parsed.choices[0]?.delta?.content) {
                                const content = parsed.choices[0].delta.content;
                                fullResponse += content;
                                yield content;
                            }
                        } catch (e) {
                            // 忽略解析错误
                        }
                    }
                }
            }

        } catch (error) {
            console.error('流式传输错误：', error.response?.data || error.message);
            yield '错误：无法流式传输响应';
        }
    }
}

module.exports = AIHubChatService;

// 使用示例
if (require.main === module) {
    const chatService = new AIHubChatService();

    // 简单聊天
    (async () => {
        const response = await chatService.chat('你好，AI Hub！');
        console.log(`AI：${response}`);

        // 流式聊天
        console.log('AI（流式）：');
        for await (const chunk of chatService.streamChat('给我讲个短故事')) {
            process.stdout.write(chunk);
        }
        console.log();
    })();
}
```

### 步骤 3：构建 Web 界面

#### Python 与 Streamlit

```python
# app.py
import streamlit as st
from chat_service import AIHubChatService
import time

# 初始化会话状态
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'chat_service' not in st.session_state:
    st.session_state.chat_service = AIHubChatService()

st.title("🤖 AI Hub 聊天机器人")
st.caption("由 AI Hub API 驱动")

# 显示聊天消息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 聊天输入
if prompt := st.chat_input("您想了解什么？"):
    # 将用户消息添加到聊天历史
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 生成 AI 响应
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        # 流式响应
        for chunk in st.session_state.chat_service.stream_chat(
            prompt,
            conversation_history=st.session_state.messages[:-1]
        ):
            full_response += chunk
            message_placeholder.markdown(full_response + "▌")
            time.sleep(0.01)

        message_placeholder.markdown(full_response)

    # 将助手响应添加到聊天历史
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# 侧边栏控件
with st.sidebar:
    st.header("设置")

    # 模型选择
    model = st.selectbox(
        "选择模型",
        ["gpt-4", "claude-3-opus", "gemini-pro"],
        index=0
    )

    # 温度控制
    temperature = st.slider(
        "温度",
        min_value=0.0,
        max_value=2.0,
        value=0.7,
        step=0.1
    )

    # 清除聊天按钮
    if st.button("清除聊天"):
        st.session_state.messages = []
        st.rerun()

    # 显示使用信息
    st.header("使用信息")
    st.info("查看您的仪表板以获取详细的使用统计信息")
```

#### Node.js 与 Express

```javascript
// server.js
const express = require('express');
const path = require('path');
const cors = require('cors');
const AIHubChatService = require('./chatService');

const app = express();
const PORT = process.env.PORT || 3000;
const chatService = new AIHubChatService();

// 中间件
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// 在内存中存储对话（生产环境中使用数据库）
const conversations = new Map();

// API 路由
app.post('/api/chat', async (req, res) => {
    try {
        const { message, sessionId, model = 'gpt-4' } = req.body;

        // 获取或创建对话历史
        if (!conversations.has(sessionId)) {
            conversations.set(sessionId, []);
        }

        const history = conversations.get(sessionId);

        // 获取 AI 响应
        const response = await chatService.chat(message, model, history);

        // 更新对话历史
        history.push({ role: 'user', content: message });
        history.push({ role: 'assistant', content: response });

        // 限制历史记录为最近 10 条消息
        if (history.length > 10) {
            history.splice(0, history.length - 10);
        }

        res.json({ response });

    } catch (error) {
        console.error('聊天错误：', error);
        res.status(500).json({ error: '无法处理聊天请求' });
    }
});

app.post('/api/chat/stream', async (req, res) => {
    try {
        const { message, sessionId, model = 'gpt-4' } = req.body;

        // 设置 SSE 头
        res.writeHead(200, {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        });

        // 获取对话历史
        if (!conversations.has(sessionId)) {
            conversations.set(sessionId, []);
        }
        const history = conversations.get(sessionId);

        let fullResponse = '';

        // 流式响应
        for await (const chunk of chatService.streamChat(message, model, history)) {
            fullResponse += chunk;
            res.write(`data: ${JSON.stringify({ chunk })}\n\n`);
        }

        // 更新对话历史
        history.push({ role: 'user', content: message });
        history.push({ role: 'assistant', content: fullResponse });

        if (history.length > 10) {
            history.splice(0, history.length - 10);
        }

        res.write('data: [DONE]\n\n');
        res.end();

    } catch (error) {
        console.error('流式聊天错误：', error);
        res.write(`data: ${JSON.stringify({ error: '流式传输失败' })}\n\n`);
        res.end();
    }
});

// 清除对话
app.delete('/api/conversation/:sessionId', (req, res) => {
    const { sessionId } = req.params;
    conversations.delete(sessionId);
    res.json({ success: true });
});

// 提供主页面
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
    console.log(`服务器运行在 http://localhost:${PORT}`);
});
```

```html
<!-- public/index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Hub 聊天机器人</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: #4CAF50; color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center; }
        .chat-container { height: 400px; overflow-y: auto; padding: 20px; border-bottom: 1px solid #ddd; }
        .message { margin-bottom: 15px; padding: 10px; border-radius: 10px; max-width: 80%; }
        .user { background: #e3f2fd; margin-left: auto; text-align: right; }
        .assistant { background: #f3e5f5; }
        .input-container { padding: 20px; display: flex; gap: 10px; }
        #messageInput { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        #sendButton { padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; }
        #sendButton:disabled { background: #ccc; cursor: not-allowed; }
        .controls { padding: 20px; background: #f9f9f9; border-radius: 0 0 10px 10px; }
        .controls select, .controls button { margin-right: 10px; padding: 5px 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI Hub 聊天机器人</h1>
            <p>由 AI Hub API 驱动</p>
        </div>

        <div id="chatContainer" class="chat-container"></div>

        <div class="input-container">
            <input type="text" id="messageInput" placeholder="输入您的消息..." onkeypress="handleKeyPress(event)">
            <button id="sendButton" onclick="sendMessage()">发送</button>
        </div>

        <div class="controls">
            <select id="modelSelect">
                <option value="gpt-4">GPT-4</option>
                <option value="claude-3-opus">Claude-3 Opus</option>
                <option value="gemini-pro">Gemini Pro</option>
            </select>
            <button onclick="clearChat()">清除聊天</button>
            <label>
                <input type="checkbox" id="streamCheckbox" checked> 流式响应
            </label>
        </div>
    </div>

    <script>
        let sessionId = 'session_' + Date.now();
        let conversationHistory = [];

        function addMessage(role, content) {
            const chatContainer = document.getElementById('chatContainer');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            messageDiv.textContent = content;
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            const sendButton = document.getElementById('sendButton');
            const streamCheckbox = document.getElementById('streamCheckbox');
            const modelSelect = document.getElementById('modelSelect');

            if (!message) return;

            // 添加用户消息
            addMessage('user', message);
            input.value = '';
            sendButton.disabled = true;

            const model = modelSelect.value;

            if (streamCheckbox.checked) {
                // 流式请求
                addMessage('assistant', '');
                const assistantMessage = document.querySelector('.message.assistant:last-child');

                try {
                    const response = await fetch('/api/chat/stream', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message, sessionId, model })
                    });

                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();

                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        const chunk = decoder.decode(value);
                        const lines = chunk.split('\n');

                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                const data = line.slice(6);
                                if (data === '[DONE]') {
                                    return;
                                }
                                try {
                                    const parsed = JSON.parse(data);
                                    if (parsed.chunk) {
                                        assistantMessage.textContent += parsed.chunk;
                                    }
                                } catch (e) {
                                    // 忽略解析错误
                                }
                            }
                        }
                    }
                } catch (error) {
                    assistantMessage.textContent = '错误：无法获取响应';
                }
            } else {
                // 非流���请求
                try {
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message, sessionId, model })
                    });

                    const result = await response.json();
                    addMessage('assistant', result.response);
                } catch (error) {
                    addMessage('assistant', '错误：无法获取响应');
                }
            }

            sendButton.disabled = false;
        }

        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }

        function clearChat() {
            document.getElementById('chatContainer').innerHTML = '';
            conversationHistory = [];

            // 在服务器上清除对话
            fetch(`/api/conversation/${sessionId}`, { method: 'DELETE' });
        }

        // 初始化
        document.getElementById('messageInput').focus();
    </script>
</body>
</html>
```

### 步骤 4：运行您的应用程序

#### Python/Streamlit

```bash
streamlit run app.py
```

#### Node.js/Express

```bash
npm start
# 或者
node server.js
```

访问 `http://localhost:3000` 查看您的聊天机器人！

## 高级集成

### 会话管理

实现持久化对话会话：

```python
# session_manager.py
import json
import uuid
from datetime import datetime
from pathlib import Path

class SessionManager:
    def __init__(self, storage_path="data/sessions"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)

    def create_session(self, user_id, title=None):
        session_id = str(uuid.uuid4())
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "title": title or f"聊天 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": [],
            "model": "gpt-4",
            "settings": {
                "temperature": 0.7,
                "max_tokens": 1000
            }
        }

        self._save_session(session)
        return session_id

    def add_message(self, session_id, role, content):
        session = self.get_session(session_id)
        if session:
            session["messages"].append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
            session["updated_at"] = datetime.now().isoformat()
            self._save_session(session)

    def get_session(self, session_id):
        session_file = self.storage_path / f"{session_id}.json"
        if session_file.exists():
            with open(session_file, 'r') as f:
                return json.load(f)
        return None

    def _save_session(self, session):
        session_file = self.storage_path / f"{session['session_id']}.json"
        with open(session_file, 'w') as f:
            json.dump(session, f, indent=2)
```

### 错误处理和重试逻辑

```python
# robust_client.py
import time
import random
from requests.exceptions import RequestException

class RobustAIHubClient:
    def __init__(self, api_key, max_retries=3, base_delay=1):
        self.api_key = api_key
        self.max_retries = max_retries
        self.base_delay = base_delay

    def chat_with_retry(self, message, model="gpt-4"):
        for attempt in range(self.max_retries):
            try:
                return self._make_request(message, model)
            except RequestException as e:
                if attempt == self.max_retries - 1:
                    raise e

                # 指数退避与抖动
                delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
                continue

    def _make_request(self, message, model):
        # 实际 API 调用的实现
        pass
```

### 响应缓存

```python
# cache_manager.py
import hashlib
import json
import time
from typing import Optional

class SimpleCache:
    def __init__(self, ttl=3600):  # 1 小时 TTL
        self.cache = {}
        self.ttl = ttl

    def _get_key(self, message: str, model: str, **kwargs) -> str:
        key_data = {"message": message, "model": model, **kwargs}
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, message: str, model: str, **kwargs) -> Optional[str]:
        key = self._get_key(message, model, **kwargs)

        if key in self.cache:
            cached_data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return cached_data
            else:
                del self.cache[key]

        return None

    def set(self, message: str, model: str, response: str, **kwargs):
        key = self._get_key(message, model, **kwargs)
        self.cache[key] = (response, time.time())
```

## 最佳实践

### 1. 提示工程

- 在您的请求中**具体明确**
- 需要时**提供上下文**
- **使用示例**来显示所需格式
- **设置适当的温度**以平衡创造性与一致性

### 2. 成本优化

- 为您的用例**选择合适的模型**
- **实现缓存**以处理重复请求
- **监控使用情况**通过使用 API
- **设置限制**来控制成本

### 3. 性能

- 对长响应**使用流式传输**
- **实现异步/等待**以进行并发请求
- **添加超时处理**以确保应用程序的健壮性
- **使用连接池**进行高容量应用程序

### 4. 安全

- **永远不要在客户端代码中暴露 API 密钥**
- 在发送到 API 之前**验证输入**
- 在您的应用程序上**实施速率限制**
- **记录和监控** API 使用情况

## 故障排除

### 常见问题

#### "无效的 API 密钥"
- 检查您的 API 密钥是否正确
- 确保密钥是活跃的且未过期
- 验证您使用的是正确的环境

#### "超出速率限制"
- 实施指数退避
- 考虑升级您的计划
- 为高容量应用程序添加请求排队

#### "模型不可用"
- 检查模型端点以获取可用模型
- 尝试替代模型
- 监控我们的状态页面以获取服务更新

#### "超时错误"
- 增加超时值
- 实施重试逻辑
- 检查您的网络连接

### 调试模式

启用调试日志来排查问题：

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 向您的 API 调用添加调试日志
logger.debug(f"向 {url} 发出请求")
logger.debug(f"负载：{payload}")
logger.debug(f"响应：{response.status_code}")
```

## 示例和模板

### 模板仓库

在我们的 GitHub 仓库中找到完整的示例：
[github.com/ai-hub/examples](https://github.com/ai-hub/examples)

### 热门用例

1. **客户服务机器人** - 自动化客户支持
2. **内容生成** - 博客文章、文章、营销文案
3. **代码助手** - 代码生成和调试
4. **数据分析** - 处理和分析文本数据
5. **翻译服务** - 多语言翻译
6. **创意写作** - 故事、脚本、诗歌
7. **教育工具** - 个性化学习体验

---

需要更多帮助？查看我们的[社区论坛](https://community.ai-hub.com)或联系我们的支持团队 developers@ai-hub.com。

愉快构建！🚀