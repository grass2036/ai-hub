# AI Hub - 企业级AI应用平台

> 基于现代化技术栈构建的智能AI应用平台，支持多AI模型集成、流式响应、成本跟踪等企业级功能。

## 🎯 项目概述

AI Hub是一个面向开发者的AI API服务平台，通过渐进式开发实现：

- **第1个月**: 多AI模型智能问答系统 ✅ **已完成核心功能**
- **第2个月**: 开发者API服务平台 🎯 **商业化转型**  
- **第3个月**: 企业级API服务解决方案
- **第4个月+**: 高级AI功能API扩展

> **💡 商业定位**: 为开发者提供统一的多AI模型API接口，支持免费试用、按量付费和企业定制服务

## 🏗️ 技术架构

```
AI Hub Platform
├── FastAPI Backend         # 后端API服务 (主架构) ✅
├── Next.js Frontend        # 现代化前端界面 ✅
├── OpenRouter Integration  # 多AI模型API平台 ✅
├── Gemini API Support      # Google AI备用服务 ✅
├── Session Management      # 对话历史持久化 ✅
├── Cost Tracking System    # 使用成本跟踪 ✅
└── Production Ready        # 生产环境部署
```

> **架构决策**: 采用 FastAPI + Next.js 现代化技术栈，OpenRouter为主力AI服务

## 🚀 核心功能

### ✅ 已完成功能
- [x] **多AI模型支持** - OpenRouter多模型平台集成，支持Grok、DeepSeek、Claude等20+模型
- [x] **流式响应系统** - 实时流式对话，支持Server-Sent Events (SSE)
- [x] **智能模型切换** - 自动降级和备用服务（OpenRouter → Gemini）
- [x] **对话历史持久化** - 完整的会话管理和消息存储系统
- [x] **成本跟踪统计** - 精确的Token计数和成本估算
- [x] **现代化UI界面** - 基于Next.js的响应式聊天界面
- [x] **多模态支持** - 支持图片和文件上传
- [x] **配置化设置** - 温度调节、模型选择、流式开关

### 🔄 开发中功能
- [ ] 会话列表显示和切换
- [ ] 使用统计可视化图表
- [ ] 批量对话导出功能

### 📋 计划功能
- [ ] RAG文档问答系统
- [ ] 向量数据库集成
- [ ] 智能客服工作流
- [ ] 企业级管理后台

## 🛠️ 快速开始

### 环境要求
- Python 3.9+
- Node.js 18+
- Docker (可选)

### 安装步骤

1. **克隆项目**
```bash
git clone --recursive git@github.com:grass2036/ai-hub.git
cd ai-hub
```

2. **后端setup**
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的API密钥
```

3. **启动开发服务器**
```bash
# 启动后端
python backend/main.py

# 启动前端 (另一个终端)
cd frontend
npm install
npm run dev
```

4. **访问应用**
- 后端API: http://localhost:8001
- API文档: http://localhost:8001/api/docs  
- 前端界面: http://localhost:3001/chat
- 聊天界面: http://localhost:3001/chat

## 📚 项目文档

- [开发指南](docs/development/setup.md)
- [API文档](docs/api/v1.md)
- [架构说明](docs/development/architecture.md)
- [部署指南](docs/deployment/docker.md)

## 🗂️ 项目结构

```
ai-hub/
├── backend/                # FastAPI后端应用
│   ├── api/v1/            # API v1路由 (chat, sessions, stats)
│   ├── core/              # 核心业务逻辑
│   │   ├── ai_service.py     # AI服务管理器
│   │   ├── session_manager.py # 会话管理
│   │   ├── cost_tracker.py   # 成本跟踪
│   │   └── providers/        # AI服务提供商
│   ├── config/            # 配置管理
│   └── main.py            # 应用入口
├── frontend/              # Next.js前端
│   ├── src/
│   │   ├── components/       # React组件
│   │   │   └── ChatInterface.tsx # 主聊天界面
│   │   └── app/             # App Router
│   └── next.config.js       # Next.js配置
├── data/                  # 数据存储
│   ├── sessions/          # 会话历史JSON文件
│   ├── usage_records/     # 使用记录
│   └── sessions_index.json # 会话索引
├── learning/              # 学习文档和计划
└── agentflow-core/        # AgentFlow框架（已废弃）
```

## 🔧 开发工具

### 代码质量
```bash
# 格式化代码
black backend/
isort backend/

# 类型检查
mypy backend/

# 运行测试
pytest backend/tests/
```

### Docker部署
```bash
# 构建和启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f backend
```

## 📈 开发路线图

> **🚀 项目转型**: 从聊天应用升级为**开发者API服务平台** - [转型规划详情](API_SERVICE_TRANSFORMATION_PLAN.md)

### v1.0 - 智能问答基础 (第1月) ✅ **核心功能已完成**
- [x] 项目初始化和基础架构
- [x] OpenRouter多模型API集成 (主力)
- [x] Gemini API集成 (备用)
- [x] 流式响应系统
- [x] 现代化Web界面 (Next.js)
- [x] 对话历史持久化
- [x] 成本跟踪统计系统
- [ ] 会话列表和切换功能
- [ ] 使用统计可视化

### v2.0 - 开发者API服务 (第2月) 🎯 **商业化转型**
- [ ] API密钥认证系统
- [ ] 用量配额管理
- [ ] 速率限制机制
- [ ] 开发者API文档
- [ ] 用户注册和管理
- [ ] 订阅计费系统

### v3.0 - 企业级API平台 (第3月)  
- [ ] 企业客户管理
- [ ] 批量API密钥管理
- [ ] 使用统计报表
- [ ] SLA保障机制
- [ ] 专属技术支持

### v4.0 - 高级功能扩展 (第4月+)
- [ ] RAG文档智能API
- [ ] 向量数据库集成
- [ ] 智能工作流API
- [ ] 多模态内容处理
- [ ] 企业级安全认证

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详情请查看 [LICENSE](LICENSE) 文件。

## 👥 作者

- **草草** - *项目创建者* - [@grass2036](https://github.com/grass2036)
- **Claude Code** - *技术指导* - AI技术导师

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化Web框架  
- [Next.js](https://nextjs.org/) - React应用框架
- [OpenRouter](https://openrouter.ai/) - AI模型API服务
- [Google Gemini](https://ai.google.dev/) - Google AI服务
- [TikToken](https://github.com/openai/tiktoken) - 精确Token计数

---

**⭐ 如果这个项目对你有帮助，请给个Star支持！**