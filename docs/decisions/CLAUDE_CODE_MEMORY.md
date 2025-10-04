# Claude Code 项目记忆库

## 🎯 项目核心决策 (必须遵守)

### ✅ 确定的技术方案
- **后端**: FastAPI + Python (已工作)
- **前端**: Next.js + TypeScript (已工作)  
- **AI集成**: Google Gemini API (已集成)
- **数据库**: 暂时无需，未来考虑
- **部署**: 开发环境已配置

### ❌ 已放弃的方案
- **AgentFlow框架**: 模块问题，过于复杂，已放弃
- **复杂插件系统**: 不需要，过度设计
- **大量理论文档**: 实用功能优先

## 🏃‍♂️ 当前开发重点

### 立即要做的事情
1. **实现流式响应** - 用户体验关键改进
2. **对话历史管理** - 保存和显示聊天记录  
3. **UI/UX改进** - 让界面更友好
4. **错误处理** - 增强系统稳定性

### 暂时不做的事情
- AgentFlow 框架研究
- 复杂的架构设计
- OpenRouter 集成 (第二周再考虑)
- 过度的抽象设计

## 📁 项目结构 (当前状态)

```
ai-hub/
├── backend/                 # FastAPI 后端
│   ├── main.py             # 主应用 (运行在 :8001)
│   ├── api/v1/chat.py      # 聊天API
│   ├── core/ai_service.py  # Gemini集成
│   └── config/settings.py  # 配置管理
├── frontend/               # Next.js 前端  
│   ├── src/app/           # App Router
│   ├── src/components/    # 聊天组件
│   └── package.json       # 依赖配置
├── .env                   # 环境变量 (API keys)
├── PROJECT_DECISIONS.md   # 架构决策记录
└── CLAUDE_CODE_MEMORY.md  # 这个文件
```

## 🚀 服务状态

### 后端服务
- **地址**: http://localhost:8001
- **API文档**: http://localhost:8001/api/docs
- **健康检查**: http://localhost:8001/health
- **聊天接口**: POST /api/v1/chat/

### 前端服务  
- **地址**: http://localhost:3001 (端口3000被占用)
- **聊天页面**: http://localhost:3001/chat
- **API代理**: 自动代理到后端8001端口

## 🔑 重要配置信息

### 环境变量 (.env)
```bash
GEMINI_API_KEY=AIzaSyBZ-ro8NPZQJem8g1JVpsnM03_9YwizVug  # 已配置
OPENROUTER_API_KEY=sk-or-v1-xxx  # 已配置但暂不使用
ENVIRONMENT=development
DEBUG=true
```

### 运行命令
```bash
# 后端启动
cd ai-hub && source venv/bin/activate && python3 backend/main.py

# 前端启动  
cd ai-hub/frontend && npm run dev
```

## 💡 开发指导原则

### 优先级顺序
1. **功能实用性** > 架构完美性
2. **用户体验** > 技术炫技
3. **快速迭代** > 过度规划
4. **稳定可用** > 功能丰富

### 代码风格
- 后端：Python + FastAPI 标准
- 前端：TypeScript + React 标准
- 简洁明了，注释适量
- 错误处理完善

### 测试策略
- 优先手动测试验证功能
- 关键功能添加自动测试
- 性能测试在完成基本功能后

## 🎯 第一周目标 (剩余时间)

### Day 1 剩余
- [ ] 实现流式响应功能
- [ ] 改进聊天界面交互

### Day 2-3
- [ ] 对话历史管理
- [ ] 错误处理优化
- [ ] UI/UX 提升

### Day 4-7
- [ ] 系统稳定性
- [ ] 性能优化
- [ ] 第二周规划

## 🚫 避免的错误

1. **不要重新分析 AgentFlow** - 已确定放弃
2. **不要过度设计** - 简单实用优先
3. **不要写太多文档** - 代码和功能优先
4. **不要忽视用户体验** - 界面友好度很重要

## 📞 Quick Reference

### 测试聊天功能
```bash
curl -X POST "http://localhost:8001/api/v1/chat/" \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，测试一下聊天功能"}'
```

### 常见问题
- 前端端口冲突 → 使用3001端口
- 后端模块错误 → 检查虚拟环境激活
- API调用失败 → 检查环境变量配置

---

**🎯 记住：专注实用功能，快速迭代，用户价值优先！**