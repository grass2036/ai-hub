# AI Hub Platform Python SDK

[![PyPI version](https://badge.fury.io/py/ai-hub-python.svg)](https://badge.fury.io/py/ai-hub-python)
[![Python versions](https://img.shields.io/pypi/pyversions/ai-hub-python.svg)](https://pypi.org/project/ai-hub-python/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

AI Hub Platform官方Python SDK，为企业级AI应用开发提供简单易用的API接口。

## 🚀 快速开始

### 安装

```bash
pip install ai-hub-python
```

### 基础使用

```python
import os
from ai_hub import AIHubClient

# 初始化客户端
client = AIHubClient(
    api_key=os.getenv("AIHUB_API_KEY"),
    base_url="https://api.aihub.com/api/v1"  # 可选，默认值
)

# 创建对话完成
response = client.chat.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "你好，请介绍一下你自己"}
    ],
    max_tokens=150
)

print(response.content)
# 输出: 你好！我是AI Hub平台的AI助手...

# 流式对话
for chunk in client.chat.stream(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "请写一首关于编程的短诗"}
    ]
):
    if chunk.content:
        print(chunk.content, end="", flush=True)
```

## 📋 主要功能

- ✅ **对话完成**: 支持同步和流式对话
- ✅ **多模型支持**: 接入20+主流AI模型
- ✅ **自动重试**: 内置智能重试机制
- ✅ **错误处理**: 完善的异常处理体系
- ✅ **类型提示**: 完整的类型注解支持
- ✅ **使用统计**: API使用量和配额管理
- ✅ **密钥管理**: API密钥的创建和管理

## 🛠️ 详细使用

### 对话API

```python
# 基础对话
response = client.chat.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "你是一个专业的编程助手"},
        {"role": "user", "content": "如何用Python实现快速排序？"}
    ],
    temperature=0.7,
    max_tokens=500
)

# 访问响应数据
print(f"回复内容: {response.content}")
print(f"使用token数: {response.usage.total_tokens}")
print(f"模型: {response.model}")

# 流式对话
print("流式回复:")
for chunk in client.chat.stream(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "解释一下什么是人工智能"}
    ]
):
    if chunk.content:
        print(chunk.content, end="", flush=True)
```

### 模型管理

```python
# 获取可用模型列表
models = client.models.list()
for model in models:
    print(f"模型: {model.id} - {model.name}")

# 获取特定模型信息
model = client.models.retrieve("gpt-4o-mini")
print(f"模型详情: {model.description}")
```

### 使用统计

```python
# 查看配额信息
quota = client.usage.quota()
print(f"月度配额: {quota.month_quota}")
print(f"已使用: {quota.month_used}")
print(f"剩余: {quota.month_remaining}")
print(f"使用率: {quota.month_usage_percent}%")

# 获取详细使用统计
stats = client.usage.stats(days=30)
print(f"30天内总请求: {stats.total_requests}")
print(f"30天内总token: {stats.total_tokens}")
print(f"成功率: {stats.success_rate}%")
```

### API密钥管理

```python
# 获取API密钥列表
keys = client.keys.list()
for key in keys:
    print(f"密钥: {key.name} ({key.key_prefix})")

# 创建新的API密钥
new_key = client.keys.create(
    name="我的新密钥",
    permissions=["chat.completions", "chat.models"],
    rate_limit=100,
    expires_days=30
)
print(f"新密钥: {new_key.api_key}")  # 只在创建时显示

# 删除API密钥
success = client.keys.delete("key_id_here")
print(f"删除成功: {success}")
```

## ⚙️ 高级配置

### 自定义配置

```python
from ai_hub import AIHubClient

client = AIHubClient(
    api_key="your_api_key",
    base_url="https://api.aihub.com/api/v1",
    timeout=30,          # 请求超时时间（秒）
    max_retries=3,       # 最大重试次数
    user_agent="MyApp/1.0"  # 自定义User-Agent
)
```

### 错误处理

```python
from ai_hub import AIHubClient
from ai_hub.exceptions import (
    APIError, AuthenticationError, RateLimitError,
    InsufficientQuotaError, ModelNotFoundError
)

client = AIHubClient(api_key="your_api_key")

try:
    response = client.chat.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}]
    )
except AuthenticationError:
    print("API密钥无效，请检查密钥是否正确")
except RateLimitError as e:
    print(f"请求过于频繁，请在{e.retry_after}秒后重试")
except InsufficientQuotaError:
    print("配额不足，请升级套餐或等待重置")
except ModelNotFoundError as e:
    print(f"模型不存在: {e}")
except APIError as e:
    print(f"API错误: {e.message} (代码: {e.error_code})")
```

### 上下文管理器

```python
# 使用上下文管理器自动关闭连接
with AIHubClient(api_key="your_api_key") as client:
    response = client.chat.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}]
    )
    print(response.content)
# 连接会自动关闭
```

## 🎯 使用示例

### 翻译助手

```python
def translate_text(text: str, target_language: str = "English") -> str:
    client = AIHubClient(api_key=os.getenv("AIHUB_API_KEY"))

    response = client.chat.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"You are a professional translator. Translate the given text to {target_language}."
            },
            {
                "role": "user",
                "content": text
            }
        ],
        temperature=0.3
    )

    return response.content

# 使用示例
chinese_text = "你好，世界！"
english_translation = translate_text(chinese_text, "English")
print(english_translation)
```

### 代码生成器

```python
def generate_code(description: str, language: str = "Python") -> str:
    client = AIHubClient(api_key=os.getenv("AIHUB_API_KEY"))

    response = client.chat.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": f"You are an expert {language} programmer. Generate clean, well-commented code based on the description."
            },
            {
                "role": "user",
                "content": f"Write {language} code to: {description}"
            }
        ],
        temperature=0.2,
        max_tokens=1000
    )

    return response.content

# 使用示例
code = generate_code("implement a binary search algorithm", "Python")
print(code)
```

### 流式聊天机器人

```python
class ChatBot:
    def __init__(self, api_key: str, system_prompt: str = None):
        self.client = AIHubClient(api_key=api_key)
        self.conversation = []

        if system_prompt:
            self.conversation.append({
                "role": "system",
                "content": system_prompt
            })

    def chat(self, user_message: str) -> str:
        # 添加用户消息
        self.conversation.append({
            "role": "user",
            "content": user_message
        })

        # 获取AI回复
        response = self.client.chat.create(
            model="gpt-4o-mini",
            messages=self.conversation,
            temperature=0.7
        )

        ai_message = response.content

        # 添加AI回复到对话历史
        self.conversation.append({
            "role": "assistant",
            "content": ai_message
        })

        return ai_message

    def stream_chat(self, user_message: str):
        # 添加用户消息
        self.conversation.append({
            "role": "user",
            "content": user_message
        })

        print("AI: ", end="", flush=True)

        # 流式获取回复
        full_response = ""
        for chunk in self.client.chat.stream(
            model="gpt-4o-mini",
            messages=self.conversation,
            temperature=0.7
        ):
            if chunk.content:
                content = chunk.content
                print(content, end="", flush=True)
                full_response += content

        # 添加完整回复到对话历史
        self.conversation.append({
            "role": "assistant",
            "content": full_response
        })

        print()  # 换行

# 使用示例
bot = ChatBot(
    api_key=os.getenv("AIHUB_API_KEY"),
    system_prompt="你是一个友好、专业的AI助手。"
)

bot.stream_chat("你好！请介绍一下你的功能")
bot.stream_chat("你能帮我写一个Python函数吗？")
```

## 🧪 开发和测试

### 安装开发依赖

```bash
git clone https://github.com/ai-hub/platform.git
cd platform/sdk/python
pip install -e ".[dev]"
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=ai_hub --cov-report=html

# 运行特定测试
pytest tests/test_chat.py
```

### 代码格式化

```bash
# 格式化代码
black ai_hub/

# 检查代码风格
flake8 ai_hub/

# 类型检查
mypy ai_hub/
```

## 📚 文档

- [完整API文档](https://docs.aihub.com)
- [开发者指南](https://docs.aihub.com/developer-guide)
- [API参考](https://docs.aihub.com/api-reference)
- [示例代码](https://github.com/ai-hub/platform/tree/main/sdk/python/examples)

## 🤝 贡献

欢迎贡献代码！请查看 [贡献指南](CONTRIBUTING.md) 了解详细信息。

## 📄 许可证

本项目采用 MIT 许可证。详情请见 [LICENSE](LICENSE) 文件。

## 🆘 支持

- 📧 技术支持: support@aihub.com
- 💬 开发者社区: https://community.aihub.com
- 🐛 问题反馈: https://github.com/ai-hub/platform/issues
- 📖 文档: https://docs.aihub.com

---

**AI Hub Platform** - 企业级AI应用平台 🚀