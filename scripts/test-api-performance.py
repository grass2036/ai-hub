#!/usr/bin/env python3
"""
API性能测试脚本
测试优化后的API响应时间和缓存效果
"""

import asyncio
import aiohttp
import time
import statistics
import json
from typing import List, Dict, Any
from dataclasses import dataclass
import argparse

@dataclass
class TestResult:
    """测试结果"""
    endpoint: str
    requests: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    p95_time: float
    success_rate: float
    cache_hit_rate: float = 0.0

class APITester:
    """API性能测试器"""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_endpoint(self, endpoint: str, requests: int = 10) -> TestResult:
        """测试单个端点"""
        url = f"{self.base_url}{endpoint}"
        response_times = []
        success_count = 0

        print(f"🧪 测试 {endpoint} ({requests} 次请求)")

        for i in range(requests):
            start_time = time.time()

            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        success_count += 1
                        response_time = time.time() - start_time
                        response_times.append(response_time)
                        print(f"  请求 {i+1}: {response_time:.3f}s")
                    else:
                        print(f"  请求 {i+1}: 失败 ({response.status})")

            except Exception as e:
                print(f"  请求 {i+1}: 错误 {str(e)}")

            # 避免请求过于频繁
            await asyncio.sleep(0.1)

        if not response_times:
            return TestResult(
                endpoint=endpoint,
                requests=requests,
                total_time=0,
                avg_time=0,
                min_time=0,
                max_time=0,
                p95_time=0,
                success_rate=0
            )

        total_time = sum(response_times)
        avg_time = total_time / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)

        # 计算P95
        sorted_times = sorted(response_times)
        p95_index = int(len(sorted_times) * 0.95)
        p95_time = sorted_times[p95_index] if p95_index < len(sorted_times) else max_time

        success_rate = (success_count / requests) * 100

        return TestResult(
            endpoint=endpoint,
            requests=requests,
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            p95_time=p95_time,
            success_rate=success_rate
        )

    async def test_cache_effect(self, endpoint: str) -> float:
        """测试缓存命中率"""
        print(f"💾 测试缓存效果: {endpoint}")

        # 第一次请求（缓存miss）
        start_time = time.time()
        try:
            async with self.session.get(f"{self.base_url}{endpoint}") as response:
                first_time = time.time() - start_time
                first_data = await response.json()
        except Exception as e:
            print(f"  缓存测试失败: {e}")
            return 0.0

        # 等待一小段时间
        await asyncio.sleep(0.5)

        # 第二次请求（应该命中缓存）
        start_time = time.time()
        try:
            async with self.session.get(f"{self.base_url}{endpoint}") as response:
                second_time = time.time() - start_time
                second_data = await response.json()
        except Exception as e:
            print(f"  缓存测试失败: {e}")
            return 0.0

        # 如果第二次明显更快，说明缓存生效
        cache_improvement = ((first_time - second_time) / first_time) * 100 if first_time > 0 else 0

        print(f"  首次请求: {first_time:.3f}s")
        print(f"  缓存请求: {second_time:.3f}s")
        print(f"  性能提升: {cache_improvement:.1f}%")

        return max(0, cache_improvement)

    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        try:
            async with self.session.get(f"{self.base_url}/api/v1/stats/cache/stats") as response:
                return await response.json()
        except Exception as e:
            print(f"  获取缓存统计失败: {e}")
            return {}

    def print_result(self, result: TestResult):
        """打印测试结果"""
        print(f"\n📊 {result.endpoint} 测试结果:")
        print(f"   总请求数: {result.requests}")
        print(f"   成功率: {result.success_rate:.1f}%")
        print(f"   平均响应时间: {result.avg_time:.3f}s")
        print(f"   最快响应: {result.min_time:.3f}s")
        print(f"   最慢响应: {result.max_time:.3f}s")
        print(f"   P95响应: {result.p95_time:.3f}s")
        if result.cache_hit_rate > 0:
            print(f"   缓存提升: {result.cache_hit_rate:.1f}%")

        # 性能评级
        if result.avg_time < 0.1:
            grade = "🟢 优秀"
        elif result.avg_time < 0.3:
            grade = "🟡 良好"
        elif result.avg_time < 1.0:
            grade = "🟠 一般"
        else:
            grade = "🔴 需优化"

        print(f"   性能评级: {grade}")

async def run_performance_test():
    """运行性能测试"""
    print("🚀 开始API性能测试")
    print("=" * 50)

    # 测试端点列表
    test_endpoints = [
        "/health",
        "/api/v1/stats/usage?days=7",
        "/api/v1/stats/daily",
        "/api/v1/stats/summary",
        "/api/v1/sessions"
    ]

    async with APITester() as tester:
        results = []

        # 测试每个端点
        for endpoint in test_endpoints:
            try:
                # 基础性能测试
                result = await tester.test_endpoint(endpoint, requests=5)

                # 测试缓存效果（仅限stats端点）
                if "/stats/" in endpoint:
                    cache_improvement = await tester.test_cache_effect(endpoint)
                    result.cache_hit_rate = cache_improvement

                results.append(result)
                tester.print_result(result)

            except Exception as e:
                print(f"❌ 测试 {endpoint} 失败: {e}")

            print("-" * 40)

        # 获取缓存统计
        print("\n💾 缓存统计信息:")
        cache_stats = await tester.get_cache_stats()
        if cache_stats:
            print(f"   缓存命中数: {cache_stats.get('hits', 0)}")
            print(f"   缓存未命中数: {cache_stats.get('misses', 0)}")
            print(f"   命中率: {cache_stats.get('hit_rate', 0):.1%}")
            print(f"   缓存项数: {cache_stats.get('total_items', 0)}")
            print(f"   内存使用: {cache_stats.get('memory_usage', '0B')}")

        # 总体评估
        print(f"\n📈 总体评估:")
        if results:
            avg_response_time = statistics.mean([r.avg_time for r in results])
            success_rate = statistics.mean([r.success_rate for r in results])

            print(f"   平均响应时间: {avg_response_time:.3f}s")
            print(f"   平均成功率: {success_rate:.1f}%")

            # 性能改进建议
            print(f"\n💡 优化建议:")
            if avg_response_time < 0.2:
                print("   ✅ API响应时间优秀")
            elif avg_response_time < 0.5:
                print("   ⚠️  API响应时间良好，可进一步优化")
            else:
                print("   ❌ API响应时间需要优化")

            if cache_stats.get('hit_rate', 0) > 0.5:
                print("   ✅ 缓存效果良好")
            else:
                print("   ⚠️  建议增加缓存使用")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="API性能测试工具")
    parser.add_argument("--url", default="http://localhost:8001",
                       help="API基础URL (默认: http://localhost:8001)")

    args = parser.parse_args()

    try:
        asyncio.run(run_performance_test())
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")

if __name__ == "__main__":
    main()