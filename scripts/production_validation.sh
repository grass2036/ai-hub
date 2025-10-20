#!/bin/bash

# AI Hub平台生产环境最终验证脚本
# Week 6 Day 6 - 生产环境最终验证

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

# 全局变量
VALIDATION_START_TIME=$(date +%s)
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试结果记录
declare -A TEST_RESULTS

# 记录测试结果
record_test_result() {
    local test_name=$1
    local result=$2
    local details=$3

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    TEST_RESULTS[$test_name]="$result:$details"

    if [ "$result" == "PASS" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        log_success "✓ $test_name: $details"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_error "✗ $test_name: $details"
    fi
}

# 1. Docker容器部署验证
validate_docker_deployment() {
    log_info "开始Docker容器部署验证..."

    # 检查容器状态
    local running_containers=$(docker-compose -f docker-compose.ha.yml ps -q | wc -l)
    if [ $running_containers -ge 5 ]; then
        record_test_result "Docker容器数量" "PASS" "运行中容器数量: $running_containers"
    else
        record_test_result "Docker容器数量" "FAIL" "运行中容器数量不足: $running_containers"
    fi

    # 检查容器健康状态
    local healthy_containers=$(docker-compose -f docker-compose.ha.yml ps --filter "status=running" --format "table {{.Service}}\t{{.Status}}" | grep "healthy" | wc -l)
    if [ $healthy_containers -ge 3 ]; then
        record_test_result "容器健康检查" "PASS" "健康容器数量: $healthy_containers"
    else
        record_test_result "容器健康检查" "FAIL" "健康容器数量不足: $healthy_containers"
    fi

    # 检查网络连通性
    if docker network ls | grep -q "ai-hub"; then
        record_test_result "Docker网络" "PASS" "网络配置正确"
    else
        record_test_result "Docker网络" "FAIL" "网络配置异常"
    fi

    # 检查卷挂载
    local volume_count=$(docker volume ls --filter "name=ai-hub" | wc -l)
    if [ $volume_count -ge 5 ]; then
        record_test_result "数据卷挂载" "PASS" "数据卷数量: $volume_count"
    else
        record_test_result "数据卷挂载" "FAIL" "数据卷数量不足: $volume_count"
    fi
}

# 2. API端点验证
validate_api_endpoints() {
    log_info "开始API端点验证..."

    local base_url="http://localhost"
    local endpoints=(
        "/api/v1/health"
        "/api/v1/models"
        "/api/v1/status"
        "/api/v1/ha/status"
        "/api/v1/backup/health"
    )

    for endpoint in "${endpoints[@]}"; do
        local response=$(curl -s -o /dev/null -w "%{http_code}" "$base_url$endpoint" || echo "000")
        if [ "$response" == "200" ]; then
            record_test_result "API端点$endpoint" "PASS" "响应正常"
        else
            record_test_result "API端点$endpoint" "FAIL" "HTTP状态码: $response"
        fi
    done
}

# 3. 数据库连接验证
validate_database_connections() {
    log_info "开始数据库连接验证..."

    # PostgreSQL连接测试
    if docker exec ai-hub-postgres-backup pg_isready -U aihub >/dev/null 2>&1; then
        record_test_result "PostgreSQL连接" "PASS" "数据库连接正常"
    else
        record_test_result "PostgreSQL连接" "FAIL" "数据库连接失败"
    fi

    # Redis连接测试
    if docker exec ai-hub-redis-backup redis-cli ping >/dev/null 2>&1; then
        record_test_result "Redis连接" "PASS" "缓存连接正常"
    else
        record_test_result "Redis连接" "FAIL" "缓存连接失败"
    fi
}

# 4. 高可用功能验证
validate_high_availability() {
    log_info "开始高可用功能验证..."

    # 负载均衡器状态
    if curl -s http://localhost/health >/dev/null 2>&1; then
        record_test_result "负载均衡器" "PASS" "Nginx运行正常"
    else
        record_test_result "负载均衡器" "FAIL" "Nginx无响应"
    fi

    # 集群状态检查
    local cluster_status=$(curl -s http://localhost/api/v1/ha/status 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('success') and data.get('data', {}).get('cluster_manager', {}).get('has_quorum'):
        print('PASS:Quorum正常')
    else:
        print('FAIL:Quorum异常')
except:
    print('FAIL:状态获取失败')
" 2>/dev/null || echo "FAIL:状态API无响应")

    record_test_result "集群Quorum" $cluster_status
}

# 5. 备份系统验证
validate_backup_system() {
    log_info "开始备份系统验证..."

    # 备份服务状态
    local backup_status=$(curl -s http://localhost:8080/health 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('status') == 'healthy':
        print('PASS:备份服务健康')
    else:
        print('FAIL:备份服务异常')
except:
    print('FAIL:备份服务无响应')
" 2>/dev/null || echo "FAIL:备份服务无响应")

    record_test_result "备份服务" $backup_status

    # 存储检查
    if docker exec ai-hub-backup-storage ls /data >/dev/null 2>&1; then
        record_test_result "备份存储" "PASS" "MinIO存储正常"
    else
        record_test_result "备份存储" "FAIL" "MinIO存储异常"
    fi
}

# 6. 监控系统验证
validate_monitoring_system() {
    log_info "开始监控系统验证..."

    # Prometheus状态
    if curl -s http://localhost:9091/-/healthy >/dev/null 2>&1; then
        record_test_result "Prometheus" "PASS" "监控服务正常"
    else
        record_test_result "Prometheus" "FAIL" "监控服务异常"
    fi

    # Grafana状态
    if curl -s http://localhost:3001/api/health >/dev/null 2>&1; then
        record_test_result "Grafana" "PASS" "可视化服务正常"
    else
        record_test_result "Grafana" "FAIL" "可视化服务异常"
    fi

    # 指标收集检查
    local metrics_count=$(curl -s http://localhost:9091/api/v1/query/query_up | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('status') == 'success' and data.get('data', {}).get('result'):
        print('PASS:指标收集正常')
    else:
        print('FAIL:指标收集异常')
except:
    print('FAIL:指标获取失败')
" 2>/dev/null || echo "FAIL:指标API无响应")

    record_test_result "指标收集" $metrics_count
}

# 7. 安全配置验证
validate_security_configuration() {
    log_info "开始安全配置验证..."

    # SSL证书检查
    if curl -s https://localhost --insecure >/dev/null 2>&1; then
        record_test_result "SSL配置" "PASS" "HTTPS可用"
    else
        record_test_result "SSL配置" "WARN" "HTTPS未配置或证书问题"
    fi

    # 防火墙状态
    if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
        record_test_result "防火墙" "PASS" "UFW防火墙启用"
    else
        record_test_result "防火墙" "WARN" "防火墙未启用或不存在"
    fi

    # 端口开放检查
    local open_ports=$(netstat -tlnp 2>/dev/null | grep -E ":(80|443|8080|3001|9091|3000)" | wc -l)
    if [ $open_ports -ge 4 ]; then
        record_test_result "端口配置" "PASS" "必要端口已开放: $open_ports"
    else
        record_test_result "端口配置" "FAIL" "端口配置异常: $open_ports"
    fi
}

# 8. 性能基准验证
validate_performance_benchmarks() {
    log_info "开始性能基准验证..."

    # API响应时间测试
    local response_time=$(curl -o /dev/null -s -w "%{time_total}" http://localhost/api/v1/health)
    if (( $(echo "$response_time < 2.0" | bc -l) )); then
        record_test_result "API响应时间" "PASS" "响应时间: ${response_time}s"
    else
        record_test_result "API响应时间" "FAIL" "响应时间过长: ${response_time}s"
    fi

    # 内存使用检查
    local memory_usage=$(docker stats --no-stream --format "table {{.MemUsage}}" | grep -E "(MB|GB)" | head -1 | awk '{print $1}' | sed 's/MiB//;s/GiB//')
    if [ -n "$memory_usage" ] && [ "$memory_usage" -lt 1000 ]; then
        record_test_result "内存使用" "PASS" "内存使用: ${memory_usage}MB"
    else
        record_test_result "内存使用" "WARN" "内存使用较高: ${memory_usage}"
    fi

    # 磁盘使用检查
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -lt 80 ]; then
        record_test_result "磁盘使用" "PASS" "磁盘使用: ${disk_usage}%"
    else
        record_test_result "磁盘使用" "WARN" "磁盘使用较高: ${disk_usage}%"
    fi
}

# 9. 数据完整性验证
validate_data_integrity() {
    log_info "开始数据完整性验证..."

    # 数据库连接数检查
    local db_connections=$(docker exec ai-hub-postgres-backup psql -U aihub -d aihub -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | tr -d ' ')
    if [ -n "$db_connections" ] && [ "$db_connections" -gt 0 ]; then
        record_test_result "数据库连接" "PASS" "活跃连接: $db_connections"
    else
        record_test_result "数据库连接" "FAIL" "连接异常"
    fi

    # 基础表检查
    local table_count=$(docker exec ai-hub-postgres-backup psql -U aihub -d aihub -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
    if [ -n "$table_count" ] && [ "$table_count" -gt 0 ]; then
        record_test_result "数据库表" "PASS" "表数量: $table_count"
    else
        record_test_result "数据库表" "FAIL" "表检查异常"
    fi
}

# 10. 日志系统验证
validate_logging_system() {
    log_info "开始日志系统验证..."

    # 应用日志检查
    if [ -d "./logs" ] && [ "$(ls -A ./logs)" ]; then
        local log_files=$(find ./logs -name "*.log" -type f | wc -l)
        record_test_result "应用日志" "PASS" "日志文件数量: $log_files"
    else
        record_test_result "应用日志" "FAIL" "日志目录为空或不存在"
    fi

    # 错误日志检查
    local error_count=$(find ./logs -name "*.log" -exec grep -l "ERROR\|CRITICAL" {} \; 2>/dev/null | wc -l)
    if [ "$error_count" -eq 0 ]; then
        record_test_result "错误日志" "PASS" "无严重错误"
    else
        record_test_result "错误日志" "WARN" "发现$error_count个错误日志文件"
    fi
}

# 生成测试报告
generate_test_report() {
    local validation_end_time=$(date +%s)
    local duration=$((validation_end_time - VALIDATION_START_TIME))
    local pass_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))

    echo ""
    echo "=========================================="
    echo "        AI Hub平台生产环境验证报告"
    echo "=========================================="
    echo "验证时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "验证耗时: ${duration}秒"
    echo ""
    echo "测试统计:"
    echo "  总测试数: $TOTAL_TESTS"
    echo "  通过测试: $PASSED_TESTS"
    echo "  失败测试: $FAILED_TESTS"
    echo "  通过率: ${pass_rate}%"
    echo ""
    echo "详细结果:"

    for test_name in "${!TEST_RESULTS[@]}"; do
        local result="${TEST_RESULTS[$test_name]}"
        local status=$(echo "$result" | cut -d: -f1)
        local details=$(echo "$result" | cut -d: -f2-)

        if [ "$status" == "PASS" ]; then
            echo "  ✓ $test_name: $details"
        elif [ "$status" == "FAIL" ]; then
            echo "  ✗ $test_name: $details"
        else
            echo "  ⚠ $test_name: $details"
        fi
    done

    echo ""
    echo "验证结论:"
    if [ $pass_rate -ge 90 ]; then
        echo "  🟢 生产环境验证通过，系统可以上线"
    elif [ $pass_rate -ge 70 ]; then
        echo "  🟡 生产环境基本就绪，建议修复关键问题后上线"
    else
        echo "  🔴 生产环境未就绪，需要修复问题后重新验证"
    fi

    echo "=========================================="

    # 保存报告到文件
    local report_file="production_validation_report_$(date +%Y%m%d_%H%M%S).txt"
    {
        echo "AI Hub平台生产环境验证报告"
        echo "生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "验证耗时: ${duration}秒"
        echo "总测试数: $TOTAL_TESTS"
        echo "通过测试: $PASSED_TESTS"
        echo "失败测试: $FAILED_TESTS"
        echo "通过率: ${pass_rate}%"
        echo ""
        echo "详细结果:"
        for test_name in "${!TEST_RESULTS[@]}"; do
            local result="${TEST_RESULTS[$test_name]}"
            echo "$test_name: $result"
        done
    } > "$report_file"

    echo "详细报告已保存到: $report_file"
}

# 主验证流程
main() {
    echo "=========================================="
    echo "    AI Hub平台生产环境最终验证"
    echo "=========================================="
    echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # 检查依赖
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker未安装或不在PATH中"
        exit 1
    fi

    if ! command -v docker-compose >/dev/null 2>&1; then
        log_error "Docker Compose未安装或不在PATH中"
        exit 1
    fi

    # 执行验证
    validate_docker_deployment
    validate_api_endpoints
    validate_database_connections
    validate_high_availability
    validate_backup_system
    validate_monitoring_system
    validate_security_configuration
    validate_performance_benchmarks
    validate_data_integrity
    validate_logging_system

    # 生成报告
    generate_test_report

    # 返回适当的退出码
    local pass_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    if [ $pass_rate -ge 90 ]; then
        exit 0
    elif [ $pass_rate -ge 70 ]; then
        exit 1
    else
        exit 2
    fi
}

# 脚本入口点
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi