# AI Hub 平台性能压力测试

## 概述

本目录包含了 AI Hub 平台的完整性能压力测试套件，用于评估系统在不同负载条件下的性能表现。

## 测试目标

- **响应时间**: 确保在不同负载下响应时间保持在可接受范围内
- **吞吐量**: 测量系统的最大处理能力
- **稳定性**: 验证系统在持续负载下的稳定性
- **可扩展性**: 评估系统的扩展能力
- **资源利用率**: 监控系统资源使用情况

## 文件结构

```
performance/
├── README.md                    # 本文档
├── load_tests.py               # 主要的负载测试脚本
├── run_performance_tests.sh    # 测试运行脚本
├── requirements.txt            # Python 依赖
├── config/
│   ├── test_scenarios.yaml     # 测试场景配置
│   └── performance_targets.yaml # 性能目标配置
└── results/                    # 测试结果目录
    ├── reports/                # 测试报告
    ├── data/                   # 原始数据
    └── logs/                   # 测试日志
```

## 快速开始

### 1. 安装依赖

```bash
cd backend/tests/performance
pip install -r requirements.txt
```

### 2. 运行快速测试

```bash
# 确保后端服务运行在 http://localhost:8001
./run_performance_tests.sh quick
```

### 3. 查看结果

测试结果保存在 `results/` 目录中，包括：
- CSV 格式的详细请求数据
- JSON 格式的性能指标
- Markdown 格式的测试报告

## 测试类型

### 1. 快速测试 (Quick Test)

- **并发用户**: 10
- **测试时长**: 60 秒
- **测试场景**: 健康检查、获取模型列表
- **目的**: 基本功能验证

```bash
./run_performance_tests.sh quick
```

### 2. 标准测试 (Standard Test)

- **并发用户**: 50
- **测试时长**: 120 秒
- **测试场景**: 健康检查、获取模型、聊天补全
- **目的**: 常规负载测试

```bash
./run_performance_tests.sh standard
```

### 3. 高负载测试 (Heavy Load Test)

- **并发用户**: 100
- **测试时长**: 180 秒
- **测试场景**: 包含流式聊天
- **目的**: 高负载下的性能评估

```bash
./run_performance_tests.sh heavy
```

### 4. 峰值负载测试 (Peak Load Test)

- **并发用户**: 200
- **测试时长**: 300 秒
- **测试场景**: 主要为聊天功能
- **目的**: 系统极限测试

```bash
./run_performance_tests.sh peak
```

### 5. 完整测试套件 (Full Test Suite)

运行所有预设测试，从低负载到高负载逐步进行。

```bash
./run_performance_tests.sh full
```

## 自定义测试

### 使用 Python 脚本

```bash
python load_tests.py \
    --users 100 \
    --duration 180 \
    --url http://localhost:8001 \
    --scenarios health_check get_models chat_completion
```

### 参数说明

- `--users`: 并发用户数
- `--duration`: 测试持续时间（秒）
- `--url`: 测试目标 URL
- `--api-key`: API 密钥
- `--scenarios`: 测试场景列表
- `--all-tests`: 运行所有预设测试

## 测试场景

### 1. 健康检查 (health_check)

检查 API 健康状态，轻量级请求。

### 2. 获取模型列表 (get_models)

获取可用的 AI 模型列表，中等复杂度请求。

### 3. 聊天补全 (chat_completion)

发送聊天请求并获取完整响应，重量级请求。

### 4. 流式聊天 (stream_chat)

发送流式聊天请求，测试流式响应性能。

## 性能指标

### 基本指标

- **总请求数**: 测试期间发送的请求总数
- **成功请求数**: 成功完成的请求数
- **失败请求数**: 失败的请求数
- **成功率**: 成功请求的百分比

### 性能指标

- **平均响应时间**: 所有成功请求的平均响应时间
- **最小响应时间**: 最快的响应时间
- **最大响应时间**: 最慢的响应时间
- **P50 响应时间**: 50% 的请求响应时间
- **P95 响应时间**: 95% 的请求响应时间
- **P99 响应时间**: 99% 的请求响应时间

### 吞吐量指标

- **每秒请求数 (RPS)**: 系统每秒处理的请求数
- **吞吐量**: 每秒处理的数据量 (MB/s)

## 性能基准

### 目标性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 平均响应时间 | < 500ms | 常规负载下 |
| P95 响应时间 | < 2s | 常规负载下 |
| 错误率 | < 1% | 所有负载下 |
| 最大并发用户 | 100+ | 生产环境支持 |
| 吞吐量 | 50+ RPS | 常规负载下 |

### 性能等级

- **优秀**: P95 < 1s, 错误率 < 0.1%
- **良好**: P95 < 2s, 错误率 < 1%
- **可接受**: P95 < 3s, 错误率 < 5%
- **需优化**: P95 > 3s 或 错误率 > 5%

## 基准测试

### 创建性能基准

```bash
./run_performance_tests.sh baseline
```

### 比较性能结果

```bash
./run_performance_tests.sh compare
```

基准测试结果保存在 `results/performance_baseline.json`，用于后续性能比较。

## 结果分析

### 测试报告

每次测试后会生成详细的 Markdown 报告，包含：

1. **测试配置**: 测试参数和环境信息
2. **性能指标**: 所有关键性能指标
3. **错误分析**: 失败请求的详细分析
4. **响应时间分布**: 响应时间的分布统计
5. **优化建议**: 基于测试结果的优化建议

### 数据文件

- **CSV 文件**: 包含每个请求的详细数据
- **JSON 文件**: 包含测试指标和配置信息
- **日志文件**: 测试过程的详细日志

### 性能趋势

通过多次测试的结果比较，可以：

1. 监控性能趋势变化
2. 识别性能回归问题
3. 评估优化效果
4. 制定容量规划

## 故障排除

### 常见问题

1. **连接被拒绝**
   - 确保后端服务正在运行
   - 检查端口配置是否正确

2. **高错误率**
   - 检查 API 密钥是否有效
   - 确认服务稳定性

3. **响应时间过长**
   - 检查系统资源使用情况
   - 优化数据库查询

4. **内存不足**
   - 减少并发用户数
   - 增加系统内存

### 调试模式

启用详细日志输出：

```bash
export PYTHONPATH=.
python -m load_tests --users 10 --duration 30 --debug
```

## 最佳实践

### 测试环境

1. **独立环境**: 在专用测试环境中运行
2. **网络隔离**: 避免网络波动影响结果
3. **资源充足**: 确保测试机器资源充足
4. **数据准备**: 准备足够的测试数据

### 测试执行

1. **逐步加压**: 从低负载开始逐步增加
2. **充分预热**: 系统需要时间预热
3. **多次测试**: 运行多次测试取平均值
4. **监控资源**: 测试时监控系统资源

### 结果分析

1. **关注趋势**: 重点关注性能趋势变化
2. **基准比较**: 与历史基准进行比较
3. **根因分析**: 深入分析性能问题根因
4. **持续优化**: 基于结果持续优化

## 自动化集成

### CI/CD 集成

可以将性能测试集成到 CI/CD 流水线中：

```yaml
# .github/workflows/performance.yml
name: Performance Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨2点运行

jobs:
  performance-test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9

    - name: Install dependencies
      run: |
        cd backend/tests/performance
        pip install -r requirements.txt

    - name: Start backend service
      run: |
        cd backend
        python simple_main.py &
        sleep 10

    - name: Run performance tests
      run: |
        cd backend/tests/performance
        ./run_performance_tests.sh quick

    - name: Upload results
      uses: actions/upload-artifact@v2
      with:
        name: performance-results
        path: backend/tests/performance/results/
```

### 监控告警

设置性能监控告警：

- 响应时间超过阈值
- 错误率超过目标值
- 吞吐量下降明显

## 扩展功能

### 自定义测试场景

可以在 `config/test_scenarios.yaml` 中定义自定义测试场景：

```yaml
custom_scenarios:
  - name: "batch_processing"
    endpoint: "/api/v1/batch/generation"
    method: "POST"
    data:
      name: "Test Batch"
      model: "gpt-4o-mini"
      prompts: ["Test prompt 1", "Test prompt 2"]
```

### 分布式测试

支持在多台机器上运行分布式测试：

```bash
# 在多台机器上运行
python load_tests.py \
    --users 50 \
    --duration 120 \
    --distributed \
    --node-id 1 \
    --total-nodes 4
```

## 联系支持

如有问题或建议，请联系：

- **技术支持**: performance@aihub.com
- **GitHub Issues**: https://github.com/aihub/platform/issues
- **文档**: https://docs.aihub.com/performance

---

*最后更新: 2024-01-01*