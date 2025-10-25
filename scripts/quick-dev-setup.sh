#!/bin/bash

# AI Hub 快速开发环境设置
# Quick Development Setup for AI Hub

set -e

echo "🚀 AI Hub Quick Development Setup"
echo "================================="

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 检查Redis
echo "📋 Checking Redis..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✅ Redis is running${NC}"
    else
        echo "Starting Redis..."
        brew services start redis 2>/dev/null || redis-server --daemonize yes 2>/dev/null
        sleep 2
        if redis-cli ping &> /dev/null; then
            echo -e "${GREEN}✅ Redis started${NC}"
        else
            echo -e "${YELLOW}⚠️  Redis not available, some features may be limited${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠️  Redis not installed. Install with: brew install redis${NC}"
fi

# 检查PostgreSQL
echo "🗄️  Checking PostgreSQL..."
if pg_isready -h localhost -p 5432 &> /dev/null; then
    echo -e "${GREEN}✅ PostgreSQL is running${NC}"
else
    echo -e "${YELLOW}⚠️  PostgreSQL not running on port 5432${NC}"
fi

# 检查环境文件
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo -e "${GREEN}✅ .env file created${NC}"
    echo -e "${YELLOW}⚠️  Please add your API keys to .env${NC}"
fi

# 创建必要目录
mkdir -p data/uploads data/sessions data/usage_records logs
echo -e "${GREEN}✅ Directories created${NC}"

echo ""
echo "🎯 Quick Start Commands:"
echo "Backend:  cd backend && python3 main.py"
echo "Frontend: cd frontend && npm run dev"
echo "Tests:    cd backend && python3 tests/test_optimization_mock.py"
echo ""
echo -e "${GREEN}✅ Ready for development!${NC}"