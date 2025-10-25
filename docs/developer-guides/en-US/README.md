# AI Hub Developer Guide

Welcome to the AI Hub Developer Guide! This comprehensive resource will help you build powerful AI-powered applications using our platform.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Quick Start Tutorial](#quick-start-tutorial)
3. [Advanced Integration](#advanced-integration)
4. [Best Practices](#best-practices)
5. [Troubleshooting](#troubleshooting)
6. [Examples and Templates](#examples-and-templates)

## Getting Started

### Prerequisites

Before you start building with AI Hub, make sure you have:

- **AI Hub Account** - Sign up at [ai-hub.com](https://ai-hub.com)
- **API Key** - Generate from your dashboard
- **Development Environment** - Your preferred IDE and tools
- **Basic Programming Knowledge** - Understanding of REST APIs

### Development Setup

#### Environment Variables

Never hardcode your API key! Use environment variables:

```bash
# .env file
AI_HUB_API_KEY=your-api-key-here
AI_HUB_BASE_URL=https://api.ai-hub.com/v1
```

#### Recommended Libraries

**Python:**
```bash
pip install requests python-dotenv ai-hub
```

**Node.js:**
```bash
npm install axios dotenv @ai-hub/client
```

**Go:**
```bash
go get github.com/ai-hub/go-sdk
```

### API Key Security

- 🔐 **Store securely** - Use environment variables or secret management
- 🔄 **Rotate regularly** - Update keys every 90 days
- 📍 **Scope permissions** - Use minimum required permissions
- 📊 **Monitor usage** - Track API key usage in dashboard
- 🚫 **Never commit** - Keep API keys out of version control

## Quick Start Tutorial

Let's build a simple AI chatbot application step by step.

### Step 1: Initialize Your Project

#### Python Project

```bash
mkdir ai-hub-chatbot
cd ai-hub-chatbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install requests python-dotenv streamlit
```

#### Node.js Project

```bash
mkdir ai-hub-chatbot
cd ai-hub-chatbot

# Initialize npm project
npm init -y

# Install dependencies
npm install express axios dotenv cors
```

### Step 2: Create the Chat Function

#### Python Implementation

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
            raise ValueError("AI_HUB_API_KEY environment variable is required")

    def chat(self, message, model="gpt-4", conversation_history=None):
        """Send a message to AI and get response"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Build messages array
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
            print(f"Error calling AI Hub API: {e}")
            return "Sorry, I'm having trouble connecting right now."

    def stream_chat(self, message, model="gpt-4", conversation_history=None):
        """Stream chat responses"""
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
            print(f"Error in streaming: {e}")
            yield "Error: Could not stream response"

# Usage example
if __name__ == "__main__":
    chat_service = AIHubChatService()

    # Simple chat
    response = chat_service.chat("Hello, AI Hub!")
    print(f"AI: {response}")

    # Streaming chat
    print("AI (streaming): ", end="")
    for chunk in chat_service.stream_chat("Tell me a short story"):
        print(chunk, end="", flush=True)
    print()
```

#### Node.js Implementation

```javascript
// chatService.js
require('dotenv').config();
const axios = require('axios');

class AIHubChatService {
    constructor() {
        this.apiKey = process.env.AI_HUB_API_KEY;
        this.baseURL = process.env.AI_HUB_BASE_URL || 'https://api.ai-hub.com/v1';

        if (!this.apiKey) {
            throw new Error('AI_HUB_API_KEY environment variable is required');
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
            console.error('Error calling AI Hub API:', error.response?.data || error.message);
            return 'Sorry, I\'m having trouble connecting right now.';
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
                            // Ignore parsing errors
                        }
                    }
                }
            }

        } catch (error) {
            console.error('Error in streaming:', error.response?.data || error.message);
            yield 'Error: Could not stream response';
        }
    }
}

module.exports = AIHubChatService;

// Usage example
if (require.main === module) {
    const chatService = new AIHubChatService();

    // Simple chat
    (async () => {
        const response = await chatService.chat('Hello, AI Hub!');
        console.log(`AI: ${response}`);

        // Streaming chat
        console.log('AI (streaming): ');
        for await (const chunk of chatService.streamChat('Tell me a short story')) {
            process.stdout.write(chunk);
        }
        console.log();
    })();
}
```

### Step 3: Build a Web Interface

#### Python with Streamlit

```python
# app.py
import streamlit as st
from chat_service import AIHubChatService
import time

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'chat_service' not in st.session_state:
    st.session_state.chat_service = AIHubChatService()

st.title("🤖 AI Hub Chatbot")
st.caption("Powered by AI Hub API")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What would you like to know?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate AI response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        # Stream response
        for chunk in st.session_state.chat_service.stream_chat(
            prompt,
            conversation_history=st.session_state.messages[:-1]
        ):
            full_response += chunk
            message_placeholder.markdown(full_response + "▌")
            time.sleep(0.01)

        message_placeholder.markdown(full_response)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Sidebar with controls
with st.sidebar:
    st.header("Settings")

    # Model selection
    model = st.selectbox(
        "Choose Model",
        ["gpt-4", "claude-3-opus", "gemini-pro"],
        index=0
    )

    # Temperature control
    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        value=0.7,
        step=0.1
    )

    # Clear chat button
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    # Display usage info
    st.header("Usage Info")
    st.info("Check your dashboard for detailed usage statistics")
```

#### Node.js with Express

```javascript
// server.js
const express = require('express');
const path = require('path');
const cors = require('cors');
const AIHubChatService = require('./chatService');

const app = express();
const PORT = process.env.PORT || 3000;
const chatService = new AIHubChatService();

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Store conversations in memory (in production, use a database)
const conversations = new Map();

// API Routes
app.post('/api/chat', async (req, res) => {
    try {
        const { message, sessionId, model = 'gpt-4' } = req.body;

        // Get or create conversation history
        if (!conversations.has(sessionId)) {
            conversations.set(sessionId, []);
        }

        const history = conversations.get(sessionId);

        // Get AI response
        const response = await chatService.chat(message, model, history);

        // Update conversation history
        history.push({ role: 'user', content: message });
        history.push({ role: 'assistant', content: response });

        // Limit history to last 10 messages
        if (history.length > 10) {
            history.splice(0, history.length - 10);
        }

        res.json({ response });

    } catch (error) {
        console.error('Chat error:', error);
        res.status(500).json({ error: 'Failed to process chat request' });
    }
});

app.post('/api/chat/stream', async (req, res) => {
    try {
        const { message, sessionId, model = 'gpt-4' } = req.body;

        // Set SSE headers
        res.writeHead(200, {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        });

        // Get conversation history
        if (!conversations.has(sessionId)) {
            conversations.set(sessionId, []);
        }
        const history = conversations.get(sessionId);

        let fullResponse = '';

        // Stream response
        for await (const chunk of chatService.streamChat(message, model, history)) {
            fullResponse += chunk;
            res.write(`data: ${JSON.stringify({ chunk })}\n\n`);
        }

        // Update conversation history
        history.push({ role: 'user', content: message });
        history.push({ role: 'assistant', content: fullResponse });

        if (history.length > 10) {
            history.splice(0, history.length - 10);
        }

        res.write('data: [DONE]\n\n');
        res.end();

    } catch (error) {
        console.error('Stream chat error:', error);
        res.write(`data: ${JSON.stringify({ error: 'Streaming failed' })}\n\n`);
        res.end();
    }
});

// Clear conversation
app.delete('/api/conversation/:sessionId', (req, res) => {
    const { sessionId } = req.params;
    conversations.delete(sessionId);
    res.json({ success: true });
});

// Serve the main page
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
```

```html
<!-- public/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Hub Chatbot</title>
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
            <h1>🤖 AI Hub Chatbot</h1>
            <p>Powered by AI Hub API</p>
        </div>

        <div id="chatContainer" class="chat-container"></div>

        <div class="input-container">
            <input type="text" id="messageInput" placeholder="Type your message..." onkeypress="handleKeyPress(event)">
            <button id="sendButton" onclick="sendMessage()">Send</button>
        </div>

        <div class="controls">
            <select id="modelSelect">
                <option value="gpt-4">GPT-4</option>
                <option value="claude-3-opus">Claude-3 Opus</option>
                <option value="gemini-pro">Gemini Pro</option>
            </select>
            <button onclick="clearChat()">Clear Chat</button>
            <label>
                <input type="checkbox" id="streamCheckbox" checked> Stream Response
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

            // Add user message
            addMessage('user', message);
            input.value = '';
            sendButton.disabled = true;

            const model = modelSelect.value;

            if (streamCheckbox.checked) {
                // Streaming request
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
                                    // Ignore parsing errors
                                }
                            }
                        }
                    }
                } catch (error) {
                    assistantMessage.textContent = 'Error: Could not get response';
                }
            } else {
                // Non-streaming request
                try {
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message, sessionId, model })
                    });

                    const result = await response.json();
                    addMessage('assistant', result.response);
                } catch (error) {
                    addMessage('assistant', 'Error: Could not get response');
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

            // Clear conversation on server
            fetch(`/api/conversation/${sessionId}`, { method: 'DELETE' });
        }

        // Initialize
        document.getElementById('messageInput').focus();
    </script>
</body>
</html>
```

### Step 4: Run Your Application

#### Python/Streamlit

```bash
streamlit run app.py
```

#### Node.js/Express

```bash
npm start
# or
node server.js
```

Visit `http://localhost:3000` to see your chatbot in action!

## Advanced Integration

### Session Management

Implement persistent conversation sessions:

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
            "title": title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
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

### Error Handling and Retry Logic

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

                # Exponential backoff with jitter
                delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
                continue

    def _make_request(self, message, model):
        # Implementation of actual API call
        pass
```

### Response Caching

```python
# cache_manager.py
import hashlib
import json
import time
from typing import Optional

class SimpleCache:
    def __init__(self, ttl=3600):  # 1 hour TTL
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

## Best Practices

### 1. Prompt Engineering

- **Be specific and clear** in your requests
- **Provide context** when needed
- **Use examples** to show desired format
- **Set appropriate temperature** for creativity vs. consistency

### 2. Cost Optimization

- **Choose the right model** for your use case
- **Implement caching** for repeated requests
- **Monitor usage** with the usage API
- **Set limits** to control costs

### 3. Performance

- **Use streaming** for long responses
- **Implement async/await** for concurrent requests
- **Add timeout handling** for robust applications
- **Use connection pooling** for high-volume applications

### 4. Security

- **Never expose API keys** in client-side code
- **Validate inputs** before sending to API
- **Implement rate limiting** on your application
- **Log and monitor** API usage

## Troubleshooting

### Common Issues

#### "Invalid API Key"
- Check that your API key is correct
- Ensure the key is active and not expired
- Verify you're using the correct environment

#### "Rate Limit Exceeded"
- Implement exponential backoff
- Consider upgrading your plan
- Add request queuing for high-volume applications

#### "Model Not Available"
- Check the models endpoint for available models
- Try alternative models
- Monitor our status page for service updates

#### "Timeout Errors"
- Increase timeout values
- Implement retry logic
- Check your network connectivity

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add debug logging to your API calls
logger.debug(f"Making request to {url}")
logger.debug(f"Payload: {payload}")
logger.debug(f"Response: {response.status_code}")
```

## Examples and Templates

### Template Repository

Find complete examples in our GitHub repository:
[github.com/ai-hub/examples](https://github.com/ai-hub/examples)

### Popular Use Cases

1. **Customer Service Bot** - Automated customer support
2. **Content Generation** - Blog posts, articles, marketing copy
3. **Code Assistant** - Code generation and debugging
4. **Data Analysis** - Processing and analyzing text data
5. **Translation Service** - Multi-language translation
6. **Creative Writing** - Stories, scripts, poetry
7. **Educational Tool** - Personalized learning experiences

---

Need more help? Check out our [community forum](https://community.ai-hub.com) or contact our support team at developers@ai-hub.com.

Happy building! 🚀