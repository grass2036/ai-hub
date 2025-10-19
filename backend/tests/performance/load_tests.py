"""
AI Hub 平台性能压力测试
Week 4 Day 27: System Integration Testing and Documentation
"""

import asyncio
import aiohttp
import time
import statistics
import json
import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import threading
import collections
import argparse
import sys
import csv
import os
from dataclasses import dataclass, asdict
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tests/performance/load_test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TestConfig:
    """测试配置"""
    base_url: str
    concurrent_users: int
    test_duration: int  # 秒
    ramp_up_time: int  # 秒
    api_key: str
    test_scenarios: List[str]
    output_dir: str = "tests/performance/results"


@dataclass
class RequestResult:
    """请求结果"""
    timestamp: float
    method: str
    endpoint: str
    status_code: int
    response_time: float
    response_size: int
    success: bool
    error_message: str = None


@dataclass
class TestMetrics:
    """测试指标"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    throughput_mb_per_second: float


class LoadTester:
    """负载测试器"""

    def __init__(self, config: TestConfig):
        self.config = config
        self.results: List[RequestResult] = []
        self.start_time = None
        self.end_time = None
        self.active_threads = 0
        self.lock = threading.Lock()
        self.session = None

        # 测试数据
        self.test_prompts = [
            "解释量子计算的基本原理",
            "写一个Python函数来计算斐波那契数列",
            "分析人工智能在医疗领域的应用前景",
            "创建一个简单的React组件示例",
            "比较机器学习和深度学习的区别",
            "解释区块链技术的工作原理",
            "写一个SQL查询来查找重复记录",
            "分析全球气候变化的影响",
            "创建一个RESTful API的设计规范",
            "解释微服务架构的优缺点"
        ]

        # 创建输出目录
        os.makedirs(config.output_dir, exist_ok=True)

    async def setup(self):
        """设置测试环境"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=50)
        )
        logger.info(f"Load tester initialized for {self.config.base_url}")

    async def cleanup(self):
        """清理测试环境"""
        if self.session:
            await self.session.close()

    def generate_test_data(self) -> Dict[str, Any]:
        """生成测试数据"""
        return {
            "message": random.choice(self.test_prompts),
            "model": random.choice(["gpt-4o-mini", "gpt-4o"]),
            "temperature": random.uniform(0.1, 1.0),
            "max_tokens": random.randint(100, 1000)
        }

    async def make_request(self, method: str, endpoint: str, data: Dict = None) -> RequestResult:
        """发送单个请求"""
        start_time = time.time()
        timestamp = start_time

        try:
            url = f"{self.config.base_url}{endpoint}"
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }

            if method.upper() == "GET":
                async with self.session.get(url, headers=headers) as response:
                    content = await response.read()
                    status_code = response.status
                    response_size = len(content)
            elif method.upper() == "POST":
                async with self.session.post(url, headers=headers, json=data) as response:
                    content = await response.read()
                    status_code = response.status
                    response_size = len(content)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response_time = time.time() - start_time
            success = 200 <= status_code < 400

            return RequestResult(
                timestamp=timestamp,
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                response_time=response_time,
                response_size=response_size,
                success=success
            )

        except Exception as e:
            response_time = time.time() - start_time
            return RequestResult(
                timestamp=timestamp,
                method=method,
                endpoint=endpoint,
                status_code=0,
                response_time=response_time,
                response_size=0,
                success=False,
                error_message=str(e)
            )

    async def run_user_session(self, user_id: int) -> List[RequestResult]:
        """运行单个用户会话"""
        user_results = []

        # 等待随机时间，模拟真实用户行为
        await asyncio.sleep(random.uniform(0, self.config.ramp_up_time))

        end_time = self.start_time + self.config.test_duration

        while time.time() < end_time:
            # 随机选择测试场景
            scenario = random.choice(self.config.test_scenarios)

            if scenario == "chat_completion":
                data = self.generate_test_data()
                result = await self.make_request("POST", "/api/v1/chat/completions", data)
            elif scenario == "get_models":
                result = await self.make_request("GET", "/api/v1/models")
            elif scenario == "health_check":
                result = await self.make_request("GET", "/api/v1/health")
            elif scenario == "stream_chat":
                data = self.generate_test_data()
                result = await self.make_request("POST", "/api/v1/chat/stream", data)
            else:
                continue

            user_results.append(result)

            # 模拟用户思考时间
            await asyncio.sleep(random.uniform(0.5, 3.0))

        return user_results

    async def run_load_test(self) -> TestMetrics:
        """运行负载测试"""
        logger.info(f"Starting load test: {self.config.concurrent_users} concurrent users for {self.config.test_duration} seconds")

        self.start_time = time.time()

        # 创建用户任务
        tasks = []
        for user_id in range(self.config.concurrent_users):
            task = asyncio.create_task(self.run_user_session(user_id))
            tasks.append(task)

        # 等待所有任务完成
        user_results = await asyncio.gather(*tasks, return_exceptions=True)

        self.end_time = time.time()

        # 收集所有结果
        all_results = []
        for results in user_results:
            if isinstance(results, list):
                all_results.extend(results)
            else:
                logger.error(f"User session failed: {results}")

        self.results = all_results

        # 计算指标
        metrics = self.calculate_metrics()

        logger.info(f"Load test completed: {metrics.total_requests} requests, {metrics.error_rate:.2%} error rate")

        return metrics

    def calculate_metrics(self) -> TestMetrics:
        """计算测试指标"""
        if not self.results:
            return TestMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        total_requests = len(self.results)
        successful_requests = sum(1 for r in self.results if r.success)
        failed_requests = total_requests - successful_requests

        response_times = [r.response_time for r in self.results if r.success]

        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p50_response_time = statistics.quantiles(response_times, n=2)[0]
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max(response_times)
        else:
            avg_response_time = min_response_time = max_response_time = 0
            p50_response_time = p95_response_time = p99_response_time = 0

        # 计算每秒请求数
        test_duration = self.end_time - self.start_time
        requests_per_second = total_requests / test_duration if test_duration > 0 else 0

        # 计算错误率
        error_rate = failed_requests / total_requests if total_requests > 0 else 0

        # 计算吞吐量 (MB/s)
        total_bytes = sum(r.response_size for r in self.results if r.success)
        throughput_mb_per_second = (total_bytes / (1024 * 1024)) / test_duration if test_duration > 0 else 0

        return TestMetrics(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p50_response_time=p50_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            throughput_mb_per_second=throughput_mb_per_second
        )

    def save_results(self, metrics: TestMetrics):
        """保存测试结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存详细结果
        results_file = os.path.join(self.config.output_dir, f"load_test_results_{timestamp}.csv")

        with open(results_file, 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'method', 'endpoint', 'status_code', 'response_time', 'response_size', 'success', 'error_message']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for result in self.results:
                writer.writerow(asdict(result))

        # 保存指标摘要
        summary_file = os.path.join(self.config.output_dir, f"load_test_summary_{timestamp}.json")

        summary_data = {
            "test_config": asdict(self.config),
            "test_metrics": asdict(metrics),
            "test_duration": self.end_time - self.start_time,
            "timestamp": timestamp
        }

        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2, default=str)

        logger.info(f"Results saved to {results_file} and {summary_file}")

    def generate_report(self, metrics: TestMetrics):
        """生成测试报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.config.output_dir, f"load_test_report_{timestamp}.md")

        report_content = f"""# AI Hub 平台负载测试报告

## 测试配置

- **测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **并发用户数**: {self.config.concurrent_users}
- **测试持续时间**: {self.config.test_duration} 秒
- **爬坡时间**: {self.config.ramp_up_time} 秒
- **目标URL**: {self.config.base_url}
- **测试场景**: {', '.join(self.config.test_scenarios)}

## 测试结果

### 基本指标

| 指标 | 数值 |
|------|------|
| 总请求数 | {metrics.total_requests:,} |
| 成功请求数 | {metrics.successful_requests:,} |
| 失败请求数 | {metrics.failed_requests:,} |
| 成功率 | {(1 - metrics.error_rate) * 100:.2f}% |
| 错误率 | {metrics.error_rate * 100:.2f}% |

### 性能指标

| 指标 | 数值 |
|------|------|
| 平均响应时间 | {metrics.avg_response_time:.3f} 秒 |
| 最小响应时间 | {metrics.min_response_time:.3f} 秒 |
| 最大响应时间 | {metrics.max_response_time:.3f} 秒 |
| P50 响应时间 | {metrics.p50_response_time:.3f} 秒 |
| P95 响应时间 | {metrics.p95_response_time:.3f} 秒 |
| P99 响应时间 | {metrics.p99_response_time:.3f} 秒 |

### 吞吐量指标

| 指标 | 数值 |
|------|------|
| 每秒请求数 (RPS) | {metrics.requests_per_second:.2f} |
| 吞吐量 | {metrics.throughput_mb_per_second:.2f} MB/s |

## 错误分析

"""

        # 错误统计
        error_stats = collections.Counter(r.status_code for r in self.results if not r.success)
        if error_stats:
            report_content += "### HTTP 状态码分布\n\n"
            for status_code, count in error_stats.most_common():
                percentage = (count / metrics.failed_requests) * 100
                report_content += f"- **{status_code}**: {count} 次 ({percentage:.1f}%)\n"
            report_content += "\n"

        # 端点分析
        endpoint_stats = collections.Counter(r.endpoint for r in self.results)
        if endpoint_stats:
            report_content += "### 端点请求分布\n\n"
            for endpoint, count in endpoint_stats.most_common():
                percentage = (count / metrics.total_requests) * 100
                endpoint_response_times = [r.response_time for r in self.results if r.endpoint == endpoint and r.success]
                avg_time = statistics.mean(endpoint_response_times) if endpoint_response_times else 0
                report_content += f"- **{endpoint}**: {count} 次 ({percentage:.1f}%), 平均响应时间: {avg_time:.3f}s\n"
            report_content += "\n"

        # 响应时间分布
        if self.results:
            response_times = [r.response_time for r in self.results if r.success]
            if response_times:
                buckets = [0, 0.1, 0.5, 1.0, 2.0, 5.0, float('inf')]
                bucket_labels = ["< 100ms", "100-500ms", "500ms-1s", "1-2s", "2-5s", "> 5s"]

                report_content += "### 响应时间分布\n\n"
                for i, (lower, upper) in enumerate(zip(buckets[:-1], buckets[1:])):
                    count = sum(1 for rt in response_times if lower <= rt < upper)
                    percentage = (count / len(response_times)) * 100
                    report_content += f"- **{bucket_labels[i]}**: {count} 次 ({percentage:.1f}%)\n"
                report_content += "\n"

        # 性能建议
        report_content += """## 性能分析建议

"""

        if metrics.error_rate > 0.05:
            report_content += "⚠️ **错误率过高**: 建议检查系统稳定性和错误处理机制\n\n"

        if metrics.p95_response_time > 2.0:
            report_content += "⚠️ **响应时间较长**: 建议优化数据库查询和缓存策略\n\n"

        if metrics.requests_per_second < 10:
            report_content += "⚠️ **吞吐量较低**: 建议增加服务器资源或优化代码性能\n\n"

        if metrics.p99_response_time > metrics.p95_response_time * 3:
            report_content += "⚠️ **响应时间不稳定**: 建议检查系统负载和资源竞争\n\n"

        if metrics.error_rate <= 0.01 and metrics.p95_response_time <= 1.0:
            report_content += "✅ **性能良好**: 系统在当前负载下表现良好\n\n"

        report_content += """## 测试建议

1. **定期测试**: 建议每周进行一次负载测试，监控性能趋势
2. **逐步加压**: 在生产环境中逐步增加负载，观察系统表现
3. **监控告警**: 设置性能监控告警，及时发现问题
4. **容量规划**: 根据测试结果进行容量规划和资源优化

---
*报告生成时间: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "*"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logger.info(f"Report generated: {report_file}")
        return report_file


class StressTestRunner:
    """压力测试运行器"""

    def __init__(self):
        self.test_configs = [
            # 轻负载测试
            TestConfig(
                base_url="http://localhost:8001",
                concurrent_users=10,
                test_duration=60,
                ramp_up_time=10,
                api_key="test_api_key",
                test_scenarios=["health_check", "get_models"]
            ),

            # 中等负载测试
            TestConfig(
                base_url="http://localhost:8001",
                concurrent_users=50,
                test_duration=120,
                ramp_up_time=30,
                api_key="test_api_key",
                test_scenarios=["health_check", "get_models", "chat_completion"]
            ),

            # 高负载测试
            TestConfig(
                base_url="http://localhost:8001",
                concurrent_users=100,
                test_duration=180,
                ramp_up_time=60,
                api_key="test_api_key",
                test_scenarios=["health_check", "get_models", "chat_completion", "stream_chat"]
            ),

            # 峰值负载测试
            TestConfig(
                base_url="http://localhost:8001",
                concurrent_users=200,
                test_duration=300,
                ramp_up_time=120,
                api_key="test_api_key",
                test_scenarios=["chat_completion", "stream_chat"]
            )
        ]

    async def run_all_tests(self):
        """运行所有测试"""
        results = []

        for i, config in enumerate(self.test_configs, 1):
            logger.info(f"Running test {i}/{len(self.test_configs)}: {config.concurrent_users} users")

            tester = LoadTester(config)
            await tester.setup()

            try:
                metrics = await tester.run_load_test()
                tester.save_results(metrics)
                report_file = tester.generate_report(metrics)

                results.append({
                    "config": config,
                    "metrics": metrics,
                    "report_file": report_file
                })

                # 测试间隔，让系统恢复
                logger.info("Waiting 30 seconds before next test...")
                await asyncio.sleep(30)

            finally:
                await tester.cleanup()

        # 生成综合报告
        self.generate_summary_report(results)

        return results

    def generate_summary_report(self, results: List[Dict]):
        """生成综合报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = f"tests/performance/results/stress_test_summary_{timestamp}.md"

        report_content = """# AI Hub 平台压力测试综合报告

## 测试概述

本报告包含了 AI Hub 平台在不同负载条件下的性能测试结果。

"""

        # 测试结果表格
        report_content += """## 测试结果汇总

| 测试场景 | 并发用户 | 测试时长 | 总请求数 | 成功率 | 平均响应时间 | P95响应时间 | RPS |
|----------|----------|----------|----------|--------|--------------|------------|-----|
"""

        for result in results:
            config = result["config"]
            metrics = result["metrics"]
            scenarios = ", ".join(config.test_scenarios)

            report_content += f"| {scenarios} | {config.concurrent_users} | {config.test_duration}s | {metrics.total_requests:,} | {(1-metrics.error_rate)*100:.1f}% | {metrics.avg_response_time:.3f}s | {metrics.p95_response_time:.3f}s | {metrics.requests_per_second:.1f} |\n"

        report_content += "\n"

        # 性能趋势分析
        report_content += """## 性能趋势分析

"""

        # 找出最佳和最差性能
        best_rps = max(results, key=lambda x: x["metrics"].requests_per_second)
        worst_response_time = max(results, key=lambda x: x["metrics"].p95_response_time)

        report_content += f"- **最高吞吐量**: {best_rps['config'].concurrent_users} 并发用户时达到 {best_rps['metrics'].requests_per_second:.1f} RPS\n"
        report_content += f"- **最长响应时间**: {worst_response_time['config'].concurrent_users} 并发用户时 P95 响应时间为 {worst_response_time['metrics'].p95_response_time:.3f}s\n"

        # 瓶颈分析
        report_content += """
## 性能瓶颈分析

"""

        # 分析错误率变化
        high_error_tests = [r for r in results if r["metrics"].error_rate > 0.05]
        if high_error_tests:
            report_content += "### 高错误率测试\n\n"
            for test in high_error_tests:
                report_content += f"- {test['config'].concurrent_users} 并发用户: 错误率 {test['metrics'].error_rate*100:.1f}%\n"
            report_content += "\n"

        # 分析响应时间变化
        report_content += "### 响应时间趋势\n\n"
        report_content += "随着并发用户数增加，响应时间的变化趋势：\n\n"

        for result in results:
            config = result["config"]
            metrics = result["metrics"]
            report_content += f"- {config.concurrent_users} 用户: 平均 {metrics.avg_response_time:.3f}s, P95 {metrics.p95_response_time:.3f}s\n"

        report_content += "\n"

        # 建议
        report_content += """## 优化建议

基于测试结果，提出以下优化建议：

1. **数据库优化**:
   - 优化慢查询
   - 增加连接池大小
   - 实施读写分离

2. **缓存策略**:
   - 对频繁访问的数据实施缓存
   - 使用 Redis 缓存热点数据
   - 实施 CDN 加速

3. **应用优化**:
   - 优化代码逻辑
   - 减少不必要的计算
   - 实施异步处理

4. **基础设施**:
   - 增加服务器资源
   - 实施负载均衡
   - 优化网络配置

5. **监控告警**:
   - 设置性能监控
   - 实施自动扩容
   - 建立故障预警机制

## 测试结论

"""

        # 总体评估
        avg_success_rate = sum(1 - r["metrics"].error_rate for r in results) / len(results)
        avg_response_time = sum(r["metrics"].avg_response_time for r in results) / len(results)

        if avg_success_rate > 0.95 and avg_response_time < 1.0:
            report_content += "✅ **整体性能良好**: 系统在各种负载条件下都能保持稳定的表现\n"
        elif avg_success_rate > 0.90 and avg_response_time < 2.0:
            report_content += "⚠️ **性能可接受**: 系统整体表现良好，但在高负载下有优化空间\n"
        else:
            report_content += "❌ **需要优化**: 系统存在性能瓶颈，需要进行优化改进\n"

        report_content += f"""
- 平均成功率: {avg_success_rate*100:.1f}%
- 平均响应时间: {avg_response_time:.3f}s
- 建议生产环境最大并发用户数: {max(r['config'].concurrent_users for r in results if r['metrics'].error_rate < 0.05)}

---
*报告生成时间: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "*"

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logger.info(f"Summary report generated: {summary_file}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI Hub 平台压力测试')
    parser.add_argument('--users', type=int, help='并发用户数')
    parser.add_argument('--duration', type=int, help='测试持续时间（秒）')
    parser.add_argument('--url', default='http://localhost:8001', help='测试目标URL')
    parser.add_argument('--api-key', default='test_api_key', help='API密钥')
    parser.add_argument('--scenarios', nargs='+',
                       choices=['health_check', 'get_models', 'chat_completion', 'stream_chat'],
                       default=['health_check', 'get_models', 'chat_completion'],
                       help='测试场景')
    parser.add_argument('--all-tests', action='store_true', help='运行所有预设测试')

    args = parser.parse_args()

    if args.all_tests:
        # 运行所有预设测试
        runner = StressTestRunner()
        await runner.run_all_tests()
    else:
        # 运行单个测试
        config = TestConfig(
            base_url=args.url,
            concurrent_users=args.users or 50,
            test_duration=args.duration or 120,
            ramp_up_time=30,
            api_key=args.api_key,
            test_scenarios=args.scenarios
        )

        tester = LoadTester(config)
        await tester.setup()

        try:
            metrics = await tester.run_load_test()
            tester.save_results(metrics)
            report_file = tester.generate_report(metrics)

            print(f"\n{'='*50}")
            print(f"负载测试完成")
            print(f"{'='*50}")
            print(f"总请求数: {metrics.total_requests:,}")
            print(f"成功率: {(1-metrics.error_rate)*100:.2f}%")
            print(f"平均响应时间: {metrics.avg_response_time:.3f}s")
            print(f"P95响应时间: {metrics.p95_response_time:.3f}s")
            print(f"每秒请求数: {metrics.requests_per_second:.1f}")
            print(f"详细报告: {report_file}")

        finally:
            await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())