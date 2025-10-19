#!/bin/bash
# AI Hub 平台性能压力测试运行脚本
# Week 4 Day 27: System Integration Testing and Documentation

set -e

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
RESULTS_DIR="$SCRIPT_DIR/results"
PYTHON_PATH=$(which python3)

# 颜色输出
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
    log_info "检查依赖项..."

    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 未安装"
        exit 1
    fi

    # 检查必要的 Python 包
    local required_packages=("aiohttp" "asyncio" "statistics")
    for package in "${required_packages[@]}"; do
        if ! $PYTHON_PATH -c "import $package" 2>/dev/null; then
            log_warning "Python 包 $package 未安装，尝试安装..."
            pip3 install $package
        fi
    done

    # 检查后端服务是否运行
    if ! curl -f -s http://localhost:8001/api/v1/health > /dev/null 2>&1; then
        log_warning "后端服务未运行，尝试启动..."
        cd "$PROJECT_ROOT"
        nohup python3 backend/simple_main.py > /dev/null 2>&1 &
        sleep 5

        if ! curl -f -s http://localhost:8001/api/v1/health > /dev/null 2>&1; then
            log_error "无法启动后端服务"
            exit 1
        fi
    fi

    log_success "依赖检查完成"
}

# 创建结果目录
setup_results_dir() {
    mkdir -p "$RESULTS_DIR"
    mkdir -p "$RESULTS_DIR/reports"
    mkdir -p "$RESULTS_DIR/data"
}

# 运行快速性能测试
run_quick_test() {
    log_info "运行快速性能测试..."

    cd "$SCRIPT_DIR"

    $PYTHON_PATH load_tests.py \
        --users 10 \
        --duration 60 \
        --url http://localhost:8001 \
        --scenarios health_check get_models

    if [ $? -eq 0 ]; then
        log_success "快速性能测试完成"
        log_info "结果保存在: $RESULTS_DIR"
    else
        log_error "快速性能测试失败"
        exit 1
    fi
}

# 运行标准性能测试
run_standard_test() {
    log_info "运行标准性能测试..."

    cd "$SCRIPT_DIR"

    $PYTHON_PATH load_tests.py \
        --users 50 \
        --duration 120 \
        --url http://localhost:8001 \
        --scenarios health_check get_models chat_completion

    if [ $? -eq 0 ]; then
        log_success "标准性能测试完成"
        log_info "结果保存在: $RESULTS_DIR"
    else
        log_error "标准性能测试失败"
        exit 1
    fi
}

# 运行高负载测试
run_heavy_test() {
    log_info "运行高负载测试..."

    cd "$SCRIPT_DIR"

    $PYTHON_PATH load_tests.py \
        --users 100 \
        --duration 180 \
        --url http://localhost:8001 \
        --scenarios health_check get_models chat_completion stream_chat

    if [ $? -eq 0 ]; then
        log_success "高负载测试完成"
        log_info "结果保存在: $RESULTS_DIR"
    else
        log_error "高负载测试失败"
        exit 1
    fi
}

# 运行峰值负载测试
run_peak_test() {
    log_info "运行峰值负载测试..."

    cd "$SCRIPT_DIR"

    $PYTHON_PATH load_tests.py \
        --users 200 \
        --duration 300 \
        --url http://localhost:8001 \
        --scenarios chat_completion stream_chat

    if [ $? -eq 0 ]; then
        log_success "峰值负载测试完成"
        log_info "结果保存在: $RESULTS_DIR"
    else
        log_error "峰值负载测试失败"
        exit 1
    fi
}

# 运行完整的压力测试套件
run_full_test_suite() {
    log_info "运行完整的压力测试套件..."

    cd "$SCRIPT_DIR"

    $PYTHON_PATH load_tests.py --all-tests

    if [ $? -eq 0 ]; then
        log_success "完整压力测试套件执行完成"
        log_info "结果保存在: $RESULTS_DIR"

        # 显示综合报告位置
        local latest_summary=$(find "$RESULTS_DIR" -name "stress_test_summary_*.md" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
        if [ -n "$latest_summary" ]; then
            log_info "综合报告: $latest_summary"
        fi
    else
        log_error "完整压力测试套件执行失败"
        exit 1
    fi
}

# 生成性能基准报告
generate_baseline_report() {
    log_info "生成性能基准报告..."

    local baseline_file="$RESULTS_DIR/performance_baseline.json"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # 运行基准测试
    cd "$SCRIPT_DIR"

    log_info "执行基准测试 (10个并发用户，60秒)..."
    $PYTHON_PATH load_tests.py \
        --users 10 \
        --duration 60 \
        --url http://localhost:8001 \
        --scenarios health_check get_models chat_completion \
        > /dev/null 2>&1

    # 提取最新的测试结果
    local latest_results=$(find "$RESULTS_DIR" -name "load_test_summary_*.json" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)

    if [ -n "$latest_results" ]; then
        cp "$latest_results" "$baseline_file"

        # 添加基准时间戳
        $PYTHON_PATH -c "
import json
import sys

with open('$baseline_file', 'r') as f:
    data = json.load(f)

data['baseline_timestamp'] = '$timestamp'
data['baseline_type'] = 'performance_baseline'

with open('$baseline_file', 'w') as f:
    json.dump(data, f, indent=2, default=str)

print('性能基准已保存到: $baseline_file')
"

        log_success "性能基准报告生成完成: $baseline_file"
    else
        log_error "无法生成性能基准报告"
    fi
}

# 比较性能测试结果
compare_with_baseline() {
    log_info "与性能基准比较..."

    local baseline_file="$RESULTS_DIR/performance_baseline.json"
    local latest_results=$(find "$RESULTS_DIR" -name "load_test_summary_*.json" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)

    if [ ! -f "$baseline_file" ]; then
        log_warning "未找到性能基准文件，先创建基准..."
        generate_baseline_report
        return
    fi

    if [ -n "$latest_results" ]; then
        log_info "生成性能比较报告..."

        $PYTHON_PATH -c "
import json
import sys
from datetime import datetime

# 读取基准数据
with open('$baseline_file', 'r') as f:
    baseline = json.load(f)

# 读取最新结果
with open('$latest_results', 'r') as f:
    latest = json.load(f)

baseline_metrics = baseline['test_metrics']
latest_metrics = latest['test_metrics']

print('=== 性能比较报告 ===')
print(f'基准时间: {baseline.get(\"baseline_timestamp\", \"未知\")}')
print(f'测试时间: {latest.get(\"timestamp\", \"未知\")}')
print()

print('指标比较:')
print(f'{'指标':<20} {'基准值':<15} {'当前值':<15} {'变化':<10}')
print('-' * 60)

def format_change(baseline_val, latest_val):
    if baseline_val == 0:
        return 'N/A'
    change = ((latest_val - baseline_val) / baseline_val) * 100
    if abs(change) < 0.1:
        return f'{change:+.2f}%'
    else:
        return f'{change:+.1f}%'

metrics_to_compare = [
    ('avg_response_time', '平均响应时间(s)', lambda x: f'{x:.3f}'),
    ('p95_response_time', 'P95响应时间(s)', lambda x: f'{x:.3f}'),
    ('requests_per_second', '每秒请求数', lambda x: f'{x:.1f}'),
    ('error_rate', '错误率', lambda x: f'{x*100:.2f}%'),
]

for key, label, formatter in metrics_to_compare:
    baseline_val = baseline_metrics.get(key, 0)
    latest_val = latest_metrics.get(key, 0)
    change = format_change(baseline_val, latest_val)

    print(f'{label:<20} {formatter(baseline_val):<15} {formatter(latest_val):<15} {change:<10}')

print()
print('性能评估:')
if latest_metrics['error_rate'] > baseline_metrics['error_rate'] * 1.5:
    print('⚠️ 错误率显著增加，需要关注系统稳定性')
elif latest_metrics['p95_response_time'] > baseline_metrics['p95_response_time'] * 1.3:
    print('⚠️ 响应时间显著增加，建议检查系统性能')
elif latest_metrics['requests_per_second'] < baseline_metrics['requests_per_second'] * 0.8:
    print('⚠️ 吞吐量显著下降，建议检查系统瓶颈')
else:
    print('✅ 性能表现正常，与基准相比无显著退化')
"

    else
        log_error "未找到最新的测试结果"
    fi
}

# 清理测试结果
cleanup_results() {
    log_info "清理测试结果..."

    read -p "确定要清理所有测试结果吗? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$RESULTS_DIR"/*
        log_success "测试结果已清理"
    else
        log_info "取消清理操作"
    fi
}

# 显示帮助信息
show_help() {
    cat << EOF
AI Hub 平台性能压力测试工具

用法: $0 [选项]

选项:
    quick           运行快速性能测试 (10用户, 60秒)
    standard        运行标准性能测试 (50用户, 120秒)
    heavy           运行高负载测试 (100用户, 180秒)
    peak            运行峰值负载测试 (200用户, 300秒)
    full            运行完整测试套件 (所有预设测试)
    baseline        生成性能基准
    compare         与性能基准比较
    cleanup         清理测试结果
    help            显示此帮助信息

示例:
    $0 quick                    # 运行快速测试
    $0 standard                 # 运行标准测试
    $0 full                     # 运行完整测试套件
    $0 baseline                 # 生成性能基准
    $0 compare                  # 比较性能结果

注意:
    - 确保后端服务在 http://localhost:8001 运行
    - 测试结果保存在 $RESULTS_DIR 目录
    - 建议在低负载时段运行高负载测试

EOF
}

# 主函数
main() {
    log_info "AI Hub 平台性能压力测试工具"

    # 创建结果目录
    setup_results_dir

    # 检查依赖
    check_dependencies

    case "${1:-help}" in
        "quick")
            run_quick_test
            ;;
        "standard")
            run_standard_test
            ;;
        "heavy")
            run_heavy_test
            ;;
        "peak")
            run_peak_test
            ;;
        "full")
            run_full_test_suite
            ;;
        "baseline")
            generate_baseline_report
            ;;
        "compare")
            compare_with_baseline
            ;;
        "cleanup")
            cleanup_results
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# 执行主函数
main "$@"