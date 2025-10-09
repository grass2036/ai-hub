#!/bin/bash

# AI Hub Docker开发环境启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${GREEN}[AI Hub Docker]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[AI Hub Docker]${NC} $1"
}

print_error() {
    echo -e "${RED}[AI Hub Docker]${NC} $1"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装，请先安装Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
}

# 检查环境变量文件
check_env_file() {
    if [ ! -f .env ]; then
        print_warning ".env文件不存在，从.env.example创建..."
        if [ -f .env.example ]; then
            cp .env.example .env
            print_warning "请编辑 .env 文件并填入真实的API密钥"
        else
            print_error ".env.example文件不存在"
            exit 1
        fi
    fi
}

# 停止现有服务
stop_services() {
    print_message "停止现有服务..."
    docker-compose -f docker-compose.dev.yml down --remove-orphans
}

# 启动服务
start_services() {
    print_message "启动Docker开发环境..."

    # 构建并启动服务
    docker-compose -f docker-compose.dev.yml up --build -d

    print_message "等待服务启动..."
    sleep 10

    # 检查服务状态
    if docker-compose -f docker-compose.dev.yml ps | grep -q "Up"; then
        print_message "✅ 服务启动成功！"
        print_message ""
        print_message "📱 前端服务: http://localhost:3000"
        print_message "🔧 后端API: http://localhost:8001"
        print_message "📚 API文档: http://localhost:8001/docs"
        print_message ""
        print_message "🔍 查看日志: docker-compose -f docker-compose.dev.yml logs -f"
        print_message "🛑 停止服务: docker-compose -f docker-compose.dev.yml down"
        print_message ""
    else
        print_error "❌ 服务启动失败，请检查日志"
        docker-compose -f docker-compose.dev.yml logs
        exit 1
    fi
}

# 显示日志
show_logs() {
    print_message "显示服务日志..."
    docker-compose -f docker-compose.dev.yml logs -f
}

# 主菜单
main_menu() {
    echo -e "${BLUE}"
    echo "======================================="
    echo "     AI Hub Docker 开发环境"
    echo "======================================="
    echo -e "${NC}"
    echo "1) 启动开发环境"
    echo "2) 停止服务"
    echo "3) 查看日志"
    echo "4) 重新构建并启动"
    echo "5) 退出"
    echo ""

    read -p "请选择操作 [1-5]: " choice

    case $choice in
        1)
            check_docker
            check_env_file
            start_services
            ;;
        2)
            stop_services
            ;;
        3)
            show_logs
            ;;
        4)
            check_docker
            check_env_file
            stop_services
            start_services
            ;;
        5)
            print_message "再见！"
            exit 0
            ;;
        *)
            print_error "无效选择，请重试"
            main_menu
            ;;
    esac
}

# 如果提供了参数，直接执行对应操作
if [ "$1" = "start" ]; then
    check_docker
    check_env_file
    start_services
elif [ "$1" = "stop" ]; then
    stop_services
elif [ "$1" = "logs" ]; then
    show_logs
elif [ "$1" = "restart" ]; then
    check_docker
    check_env_file
    stop_services
    start_services
else
    # 显示主菜单
    main_menu
fi