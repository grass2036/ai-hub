# AI Hub Docker 开发环境

使用Docker可以避免本地环境配置问题，提供一致的开发体验。

## 🚀 快速开始

### 1. 安装Docker

确保你已经安装了Docker和Docker Compose：

- **macOS**: [Docker Desktop for Mac](https://docs.docker.com/docker-for-mac/install/)
- **Windows**: [Docker Desktop for Windows](https://docs.docker.com/docker-for-windows/install/)
- **Linux**: 安装Docker Engine和Docker Compose

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量文件，填入你的API密钥
nano .env
```

### 3. 启动开发环境

#### 方法1: 使用启动脚本（推荐）
```bash
# 运行交互式菜单
./scripts/docker-dev.sh

# 或者直接启动
./scripts/docker-dev.sh start
```

#### 方法2: 手动使用Docker Compose
```bash
# 构建并启动服务
docker-compose -f docker-compose.dev.yml up --build -d

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f

# 停止服务
docker-compose -f docker-compose.dev.yml down
```

## 🌐 访问地址

启动成功后，你可以访问：

- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8001
- **API文档**: http://localhost:8001/docs
- **健康检查**: http://localhost:8001/health

## 📱 测试认证功能

1. 访问注册页面: http://localhost:3000/register
2. 填写注册信息:
   - 姓名: 测试用户
   - 邮箱: test@example.com
   - 密码: test123456
   - 确认密码: test123456
3. 注册成功后访问登录页面: http://localhost:3000/login
4. 使用注册的邮箱和密码登录

## 🔧 常用命令

```bash
# 启动服务
docker-compose -f docker-compose.dev.yml up -d

# 停止服务
docker-compose -f docker-compose.dev.yml down

# 重新构建并启动
docker-compose -f docker-compose.dev.yml up --build -d

# 查看服务状态
docker-compose -f docker-compose.dev.yml ps

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f

# 进入后端容器
docker-compose -f docker-compose.dev.yml exec backend-dev bash

# 进入前端容器
docker-compose -f docker-compose.dev.yml exec frontend-dev sh

# 清理所有数据
docker-compose -f docker-compose.dev.yml down -v
```

## 🛠️ 开发工作流

### 前端开发
1. 修改`frontend/`目录下的代码
2. Docker会自动检测文件变化并热重载
3. 在浏览器中查看实时效果

### 后端开发
1. 修改`backend/`目录下的代码
2. Docker会自动检测文件变化并重启服务
3. 在 http://localhost:8001/docs 查看API变化

### 调试
```bash
# 查看后端日志
docker-compose -f docker-compose.dev.yml logs -f backend-dev

# 查看前端日志
docker-compose -f docker-compose.dev.yml logs -f frontend-dev
```

## 🔍 故障排除

### 端口冲突
如果端口被占用，修改`docker-compose.dev.yml`中的端口映射：
```yaml
ports:
  - "3001:3000"  # 将前端改为3001端口
  - "8002:8000"  # 将后端改为8002端口
```

### 依赖问题
如果遇到依赖安装问题，重新构建镜像：
```bash
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up --build --force-recreate
```

### 权限问题
如果遇到权限问题，确保脚本有执行权限：
```bash
chmod +x scripts/docker-dev.sh
```

### 容器无法启动
检查Docker日志：
```bash
# 查看详细错误信息
docker-compose -f docker-compose.dev.yml logs

# 查看容器状态
docker-compose -f docker-compose.dev.yml ps
```

## 📁 项目结构

```
AI Hub/
├── backend/                 # 后端代码
│   ├── main.py             # FastAPI应用入口
│   ├── simple_main.py      # 简化版后端（用于测试）
│   └── requirements.txt    # Python依赖
├── frontend/               # 前端代码
│   ├── src/                # Next.js源码
│   ├── package.json        # Node.js依赖
│   └── next.config.js      # Next.js配置
├── deployment/
│   └── docker/             # Docker配置文件
│       ├── Dockerfile.backend
│       ├── Dockerfile.frontend
│       └── Dockerfile.frontend.dev
├── scripts/
│   └── docker-dev.sh       # Docker启动脚本
├── docker-compose.dev.yml  # 开发环境配置
├── docker-compose.yml      # 生产环境配置
└── .env.example           # 环境变量模板
```

## 🎯 Docker的优势

### 1. 环境一致性
- 所有开发者使用相同的环境
- 避免"在我机器上能运行"的问题
- 简化新员工上手流程

### 2. 依赖管理
- 自动安装和管理所有依赖
- 避免本地Python/Node.js版本冲突
- 提供可复现的构建环境

### 3. 开发效率
- 一键启动完整开发环境
- 快速切换项目
- 简化部署流程

### 4. 资源隔离
- 每个项目使用独立的容器
- 避免不同项目间的干扰
- 方便清理和管理

## 🚀 下一步

1. 使用Docker启动开发环境
2. 测试认证功能
3. 开始开发新功能
4. 提交代码和Docker配置

---

**记住**: Docker只是开发工具，重点是构建出色的AI Hub应用！🎉