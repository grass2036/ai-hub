#!/bin/bash

# AI Hub 开发环境快速设置脚本
# Quick Development Environment Setup for AI Hub

set -e

echo "🚀 AI Hub Development Environment Setup"
echo "======================================"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查命令是否存在
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✅ $1 is installed${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  $1 is not installed${NC}"
        return 1
    fi
}

# 检查端口是否被占用
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${GREEN}✅ Port $1 is in use${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Port $1 is available${NC}"
        return 1
    fi
}

echo "📋 Checking system requirements..."

# 检查必要的命令
echo "Checking required commands..."
check_command python3
check_command node
check_command npm
check_command psql

# 检查可选命令
echo ""
echo "Checking optional commands..."
check_command docker
check_command redis-cli

# 检查端口状态
echo ""
echo "Checking port status..."
check_port 5432  # PostgreSQL
check_port 6379  # Redis
check_port 8000  # Backend
check_port 3000  # Frontend

# 检查环境文件
echo ""
echo "📁 Checking environment configuration..."
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ .env file exists${NC}"
else
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${GREEN}✅ .env file created from template${NC}"
    echo -e "${YELLOW}⚠️  Please edit .env file with your API keys${NC}"
fi

# Redis 安装和启动
echo ""
echo "🔄 Setting up Redis..."
if check_command redis-cli; then
    if check_port 6379; then
        echo -e "${GREEN}✅ Redis is already running${NC}"
    else
        echo "Starting Redis..."
        if command -v brew &> /dev/null; then
            brew services start redis
        else
            redis-server --daemonize yes
        fi
        sleep 2
        if check_port 6379; then
            echo -e "${GREEN}✅ Redis started successfully${NC}"
        else
            echo -e "${RED}❌ Failed to start Redis${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠️  Redis not found. Installing...${NC}"
    if command -v brew &> /dev/null; then
        brew install redis
        brew services start redis
        echo -e "${GREEN}✅ Redis installed and started${NC}"
    else
        echo -e "${RED}❌ Please install Redis manually${NC}"
        echo "Visit: https://redis.io/download"
    fi
fi

# 数据库设置
echo ""
echo "🗄️  Database setup..."
if check_port 5432; then
    echo -e "${GREEN}✅ PostgreSQL is running${NC}"

    # 检查数据库是否存在
    if psql -h localhost -U $USER -lqt | cut -d \| -f 1 | grep -qw ai_hub; then
        echo -e "${GREEN}✅ Database 'ai_hub' exists${NC}"
    else
        echo "Creating database 'ai_hub'..."
        createdb -h localhost -U $USER ai_hub
        echo -e "${GREEN}✅ Database 'ai_hub' created${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  PostgreSQL is not running on port 5432${NC}"
    echo "Please start PostgreSQL service"
fi

# Python 依赖安装
echo ""
echo "🐍 Setting up Python dependencies..."
if [ -d "backend" ]; then
    cd backend
    if [ -f "requirements.txt" ]; then
        echo "Installing Python dependencies..."
        python3 -m pip install -r requirements.txt
        echo -e "${GREEN}✅ Python dependencies installed${NC}"
    else
        echo -e "${YELLOW}⚠️  requirements.txt not found${NC}"
    fi
    cd ..
else
    echo -e "${YELLOW}⚠️  backend directory not found${NC}"
fi

# Node.js 依赖安装
echo ""
echo "📦 Setting up Node.js dependencies..."
if [ -d "frontend" ]; then
    cd frontend
    if [ -f "package.json" ]; then
        echo "Installing Node.js dependencies..."
        npm install
        echo -e "${GREEN}✅ Node.js dependencies installed${NC}"
    else
        echo -e "${YELLOW}⚠️  package.json not found${NC}"
    fi
    cd ..
else
    echo -e "${YELLOW}⚠️  frontend directory not found${NC}"
fi

# 创建必要的目录
echo ""
echo "📁 Creating necessary directories..."
mkdir -p data/uploads
mkdir -p data/sessions
mkdir -p data/usage_records
mkdir -p logs
echo -e "${GREEN}✅ Directories created${NC}"

# 数据库优化测试
echo ""
echo "🧪 Running database optimization tests..."
cd backend
if [ -f "tests/test_optimization_mock.py" ]; then
    python3 tests/test_optimization_mock.py
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Database optimization tests passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Some tests failed, but environment is ready${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Database optimization tests not found${NC}"
fi
cd ..

echo ""
echo "🎉 Development Environment Setup Complete!"
echo "=========================================="
echo ""
echo -e "${GREEN}✅ Ready to start development!${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Start backend: cd backend && python3 main.py"
echo "3. Start frontend: cd frontend && npm run dev"
echo "4. Open browser: http://localhost:3000"
echo ""
echo "API Documentation: http://localhost:8001/api/docs"
echo "Database Optimization API: http://localhost:8001/api/v1/database-optimization"
echo ""
echo -e "${YELLOW}Note: Backend runs on port 8001 (not 8000) to avoid conflicts${NC}"