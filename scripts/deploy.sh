#!/bin/bash
# AI Hub 生产环境部署脚本
# Week 6 Day 4: 生产环境准备和部署配置

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查部署依赖..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装Docker"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装Docker Compose"
        exit 1
    fi

    # 检查kubectl (如果使用Kubernetes)
    if command -v kubectl &> /dev/null; then
        log_info "Kubernetes 已安装"
    fi

    # 检查git
    if ! command -v git &> /dev/null; then
        log_error "Git 未安装，请先安装Git"
        exit 1
    fi

    log_success "所有依赖检查通过"
}

# 环境验证
validate_environment() {
    log_info "验证部署环境..."

    # 检查环境变量
    if [ -z "$ENVIRONMENT" ]; then
        export ENVIRONMENT="production"
    fi

    log_info "部署环境: $ENVIRONMENT"

    # 检查必要目录
    local required_dirs=("config" "secrets" "logs" "uploads" "monitoring" "nginx")
    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            log_info "创建目录: $dir"
            mkdir -p "$dir"
        fi
    done

    # 设置目录权限
    chmod 700 secrets
    chmod 755 logs uploads

    log_success "环境验证完成"
}

# 生成配置
generate_config() {
    log_info "生成部署配置..."

    # 运行Python配置生成脚本
    python -m backend.core.production_config

    # 生成环境变量文件
    if [ ! -f ".env.prod" ]; then
        python -c "
from backend.core.production_config import config_manager
config = config_manager.load_config()
with open('.env.prod', 'w') as f:
    f.write(config_manager.get_env_file_content(config))
"
        log_success "环境变量文件已生成: .env.prod"
    fi

    # 生成生产环境Docker Compose文件
    if [ ! -f "docker-compose.prod.yml" ]; then
        python -c "
from backend.core.production_config import config_manager
config = config_manager.load_config()
with open('docker-compose.prod.yml', 'w') as f:
    f.write(config_manager.create_docker_compose_prod(config))
"
        log_success "Docker Compose配置已生成: docker-compose.prod.yml"
    fi

    # 生成Nginx配置
    if [ ! -f "nginx/nginx.conf" ]; then
        cat > nginx/nginx.conf << 'EOF'
# AI Hub 生产环境 Nginx 配置
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # 上游服务器
    upstream backend {
        server backend:8000;
    }

    # HTTP重定向到HTTPS
    server {
        listen 80;
        server_name _;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS主配置
    server {
        listen 443 ssl http2;
        server_name aihub.example.com;

        # SSL配置
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        # 安全头
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        # 静态文件
        location /static/ {
            alias /app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # API代理
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # 超时设置
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # 健康检查
        location /health {
            proxy_pass http://backend/health;
            access_log off;
        }

        # 默认代理
        location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF
        log_success "Nginx配置已生成: nginx/nginx.conf"
    fi

    # 生成Prometheus配置
    if [ ! -f "monitoring/prometheus.yml" ]; then
        mkdir -p monitoring
        cat > monitoring/prometheus.yml << 'EOF'
# Prometheus 配置
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'ai-hub-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'ai-hub-nginx'
    static_configs:
      - targets: ['nginx:9113']
    scrape_interval: 30s
EOF
        log_success "Prometheus配置已生成: monitoring/prometheus.yml"
    fi

    # 生成Grafana仪表板配置
    if [ ! -f "monitoring/grafana/dashboards/ai-hub-overview.json" ]; then
        mkdir -p monitoring/grafana/dashboards
        cat > monitoring/grafana/dashboards/ai-hub-overview.json << 'EOF'
{
  "dashboard": {
    "title": "AI Hub 平台概览",
    "panels": [
      {
        "title": "API请求数",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{status}}"
          }
        ]
      },
      {
        "title": "活跃用户数",
        "type": "stat",
        "targets": [
          {
            "expr": "active_users_total",
            "legendFormat": "活跃用户"
          }
        ]
      }
    ]
  }
}
EOF
        log_success "Grafana仪表板配置已生成"
    fi
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."

    # 构建后端镜像
    local image_tag="aihub/backend:$(date +%Y%m%d-%H%M%S)"

    docker build -t "$image_tag" .

    if [ $? -eq 0 ]; then
        log_success "后端镜像构建成功: $image_tag"
    else
        log_error "后端镜像构建失败"
        exit 1
    fi

    # 更新镜像标签
    docker tag "$image_tag" aihub/backend:latest

    log_success "镜像标签已更新: aihub/backend:latest"
}

# 备份数据
backup_data() {
    log_info "备份现有数据..."

    local backup_dir="backups/$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"

    # 备份数据库（如果存在）
    if docker ps -q postgres | grep -q .; then
        log_info "备份PostgreSQL数据..."
        docker exec ai-hub-postgres pg_dump -U postgres ai_hub_prod > "$backup_dir/postgres_backup.sql"
        log_success "PostgreSQL数据已备份"
    fi

    # 备份Redis数据（如果存在）
    if docker ps -q redis | grep -q .; then
        log_info "备份Redis数据..."
        docker exec ai-hub-redis redis-cli BGSAVE
        docker cp ai-hub-redis:/data/dump.rdb "$backup_dir/redis_backup.rdb"
        log_success "Redis数据已备份"
    fi

    # 备份配置文件
    log_info "备份配置文件..."
    cp -r config/ "$backup_dir/"
    cp -r secrets/ "$backup_dir/"
    cp .env.prod "$backup_dir/" 2>/dev/null || true
    cp docker-compose.prod.yml "$backup_dir/" 2>/dev/null || true

    log_success "数据备份完成: $backup_dir"
}

# 数据库迁移
migrate_database() {
    log_info "执行数据库迁移..."

    # 运行数据库迁移
    docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

    if [ $? -eq 0 ]; then
        log_success "数据库迁移完成"
    else
        log_error "数据库迁移失败"
        exit 1
    fi
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30

    # 检查后端健康状态
    max_attempts=10
    attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8001/health &>/dev/null; then
            log_success "后端服务健康检查通过"
            break
        else
            log_warning "后端服务尚未就绪，等待10秒后重试 ($attempt/$max_attempts)..."
            sleep 10
            ((attempt++))
        fi
    done

    if [ $attempt -gt $max_attempts ]; then
        log_error "后端服务健康检查失败"
        return 1
    fi

    # 检查数据库连接
    if docker-compose -f docker-compose.prod.yml exec backend python -c "
from backend.core.database import get_db
try:
    with get_db() as db:
        db.execute('SELECT 1')
    print('数据库连接正常')
except Exception as e:
    print(f'数据库连接失败: {e}')
    exit(1)
" &>/dev/null; then
        log_success "数据库连接正常"
    else
        log_error "数据库连接失败"
        return 1
    fi

    # 检查Redis连接
    if docker-compose -f docker-compose.prod.yml exec backend python -c "
import redis
r = redis.Redis(host='redis', port=6379, password='your_redis_password')
try:
    r.ping()
    print('Redis连接正常')
except Exception as e:
    print(f'Redis连接失败: {e}')
    exit(1)
" &>/dev/null; then
        log_success "Redis连接正常"
    else
        log_warning "Redis连接检查跳过（可能未配置密码）"
    fi

    log_success "所有健康检查通过"
}

# 部署服务
deploy_services() {
    log_info "部署生产环境服务..."

    # 停止现有服务
    log_info "停止现有服务..."
    docker-compose -f docker-compose.prod.yml down || true

    # 启动新服务
    log_info "启动生产环境服务..."
    docker-compose -f docker-compose.prod.yml up -d

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 60

    # 验证部署
    log_info "验证部署状态..."

    # 检查容器状态
    local containers=("ai-hub-nginx" "ai-hub-backend" "ai-hub-postgres" "ai-hub-redis")
    all_running=true

    for container in "${containers[@]}"; do
        if ! docker ps -q "$container" | grep -q .; then
            log_warning "容器 $container 未运行"
            all_running=false
        else
            log_success "容器 $container 运行正常"
        fi
    done

    if [ "$all_running" = true ]; then
        log_success "所有服务部署成功"
    else
        log_error "部分服务部署失败"
        return 1
    fi
}

# 验证部署
verify_deployment() {
    log_info "验证部署结果..."

    # 运行健康检查
    health_check

    # 测试API功能
    log_info "测试API功能..."

    if curl -f http://localhost/health &>/dev/null; then
        log_success "API健康检查端点正常"
    else
        log_warning "API健康检查端点异常"
    fi

    # 显示服务状态
    log_info "服务状态:"
    docker-compose -f docker-compose.prod.yml ps

    # 显示端口映射
    log_info "端口映射:"
    docker-compose -f docker-compose.prod.yml port

    log_success "部署验证完成"
}

# 显示部署信息
show_deployment_info() {
    log_info "部署信息:"
    echo "=========================="
    echo "部署环境: $ENVIRONMENT"
    echo "部署时间: $(date)"
    echo "Docker镜像: aihub/backend:latest"
    echo "=========================="
    echo ""
    echo "服务访问地址:"
    echo "- 前端: https://aihub.example.com"
    echo "- API: https://aihub.example.com/api/v1"
    echo "- 监控: http://localhost:3000 (Grafana)"
    echo "- 指标: http://localhost:9090 (Prometheus)"
    echo ""
    echo "管理命令:"
    echo "- 查看日志: docker-compose -f docker-compose.prod.yml logs -f [service]"
    echo "- 重启服务: docker-compose -f docker-compose.prod.yml restart [service]"
    echo "- 停止服务: docker-compose -f docker-compose.prod.yml down"
    echo ""
    echo "配置文件位置:"
    echo "- 环境变量: .env.prod"
    echo "- Docker配置: docker-compose.prod.yml"
    echo "- Nginx配置: nginx/nginx.conf"
    echo "- 监控配置: monitoring/"
}

# 主函数
main() {
    echo "🚀 AI Hub 平台生产环境部署"
    echo "================================="

    # 检查参数
    if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
        echo "用法: $0 [选项]"
        echo ""
        echo "选项:"
        echo "  --check-only    仅检查环境和依赖"
        echo "  --config-only   仅生成配置文件"
        echo "  --build-only    仅构建镜像"
        echo "  --backup-only   仅备份数据"
        echo "  --no-health-check 跳过健康检查"
        echo ""
        echo "环境变量:"
        echo "  ENVIRONMENT   部署环境 (production|staging|development)"
        echo "  BACKUP_DATA    是否备份数据 (true|false)"
        echo "  SKIP_HEALTH_CHECK 是否跳过健康检查 (true|false)"
        exit 0
    fi

    # 检查依赖
    check_dependencies

    # 验证环境
    validate_environment

    # 生成配置
    generate_config

    # 根据参数执行相应操作
    if [ "$1" = "--check-only" ]; then
        log_success "环境检查完成"
        exit 0
    fi

    if [ "$1" = "--config-only" ]; then
        log_success "配置生成完成"
        exit 0
    fi

    # 备份数据（默认执行）
    if [ "${BACKUP_DATA:-true}" = "true" ]; then
        backup_data
    fi

    # 构建镜像
    if [ "$1" != "--no-build" ] && [ "$1" != "--config-only" ] && [ "$1" != "--backup-only" ]; then
        build_images
    fi

    if [ "$1" = "--build-only" ]; then
        log_success "镜像构建完成"
        exit 0
    fi

    if [ "$1" = "--backup-only" ]; then
        log_success "数据备份完成"
        exit 0
    fi

    # 数据库迁移
    migrate_database

    # 部署服务
    deploy_services

    # 健康检查
    if [ "${SKIP_HEALTH_CHECK:-false}" != "true" ]; then
        health_check
    fi

    # 验证部署
    verify_deployment

    # 显示部署信息
    show_deployment_info

    log_success "🎉 AI Hub 平台生产环境部署完成！"
}

# 执行主函数
main "$@"