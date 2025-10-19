"""
API Test Runner for Automated Testing
Week 4 Day 27: System Integration Testing and Documentation
"""

import asyncio
import httpx
import json
import pytest
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import statistics
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tests/api_test_results.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    endpoint: str
    method: str
    status_code: int
    response_time: float
    success: bool
    error_message: Optional[str] = None
    response_data: Optional[Dict] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class TestConfig:
    """测试配置"""
    base_url: str
    timeout: int = 30
    max_retries: int = 3
    concurrent_requests: int = 10
    test_user_credentials: Dict[str, str] = None
    headers: Dict[str, str] = None


class APITestRunner:
    """API测试运行器"""

    def __init__(self, config: TestConfig):
        self.config = config
        self.results: List[TestResult] = []
        self.session = None
        self.auth_token = None
        self.test_user = None

        # 测试数据存储
        self.created_resources: Dict[str, Any] = {}

    async def setup(self):
        """设置测试环境"""
        self.session = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout
        )

        # 如果提供了测试用户凭据，进行登录
        if self.config.test_user_credentials:
            await self._login_test_user()

        logger.info(f"API Test Runner initialized for {self.config.base_url}")

    async def cleanup(self):
        """清理测试环境"""
        if self.session:
            await self.session.aclose()

        # 清理创建的资源
        await self._cleanup_created_resources()

        logger.info("API Test Runner cleanup completed")

    async def _login_test_user(self):
        """登录测试用户"""
        try:
            response = await self.session.post(
                "/api/v1/developer/auth/login",
                json=self.config.test_user_credentials
            )

            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["data"]["access_token"]
                self.test_user = data["data"]["developer"]
                logger.info(f"Logged in test user: {self.test_user['email']}")
            else:
                logger.error("Failed to login test user")

        except Exception as e:
            logger.error(f"Error during test user login: {e}")

    async def _cleanup_created_resources(self):
        """清理创建的资源"""
        if not self.auth_token:
            return

        auth_headers = {"Authorization": f"Bearer {self.auth_token}"}

        # 清理创建的API密钥
        for api_key_id in self.created_resources.get("api_keys", []):
            try:
                await self.session.delete(
                    f"/api/v1/developer/keys/{api_key_id}",
                    headers=auth_headers
                )
                logger.info(f"Cleaned up API key: {api_key_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup API key {api_key_id}: {e}")

        # 清理创建的批量任务
        for job_id in self.created_resources.get("batch_jobs", []):
            try:
                await self.session.post(
                    f"/api/v1/developer/batch/jobs/{job_id}/cancel",
                    headers=auth_headers
                )
                logger.info(f"Cleaned up batch job: {job_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup batch job {job_id}: {e}")

    def get_auth_headers(self) -> Dict[str, str]:
        """获取认证头"""
        headers = self.config.headers.copy() if self.config.headers else {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def run_test_case(self, test_case: Dict[str, Any]) -> TestResult:
        """运行单个测试用例"""
        start_time = time.time()

        try:
            method = test_case["method"].upper()
            url = test_case["endpoint"]
            headers = test_case.get("headers", {})
            params = test_case.get("params", {})
            json_data = test_case.get("json", {})
            expected_status = test_case.get("expected_status", 200)

            # 合并认证头
            auth_headers = self.get_auth_headers()
            headers.update(auth_headers)

            # 发送请求
            if method == "GET":
                response = await self.session.get(url, params=params, headers=headers)
            elif method == "POST":
                response = await self.session.post(url, json=json_data, params=params, headers=headers)
            elif method == "PUT":
                response = await self.session.put(url, json=json_data, params=params, headers=headers)
            elif method == "DELETE":
                response = await self.session.delete(url, params=params, headers=headers)
            elif method == "PATCH":
                response = await self.session.patch(url, json=json_data, params=params, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response_time = time.time() - start_time

            # 验证响应
            success = response.status_code == expected_status
            error_message = None
            response_data = None

            if not success:
                error_message = f"Expected status {expected_status}, got {response.status_code}"
                try:
                    error_data = response.json()
                    error_message += f" - {error_data.get('detail', 'Unknown error')}"
                except:
                    pass

            # 尝试解析响应数据
            try:
                response_data = response.json()
            except:
                pass

            result = TestResult(
                test_name=test_case["name"],
                endpoint=url,
                method=method,
                status_code=response.status_code,
                response_time=response_time,
                success=success,
                error_message=error_message,
                response_data=response_data
            )

            # 保存创建的资源ID
            if success and "resource_id" in test_case:
                resource_type = test_case.get("resource_type", "unknown")
                if resource_type not in self.created_resources:
                    self.created_resources[resource_type] = []
                if response_data and "data" in response_data:
                    if isinstance(response_data["data"], dict) and "id" in response_data["data"]:
                        self.created_resources[resource_type].append(response_data["data"]["id"])
                    elif "job_id" in response_data["data"]:
                        self.created_resources[resource_type].append(response_data["data"]["job_id"])

            return result

        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                test_name=test_case["name"],
                endpoint=test_case["endpoint"],
                method=test_case["method"],
                status_code=0,
                response_time=response_time,
                success=False,
                error_message=str(e)
            )

    async def run_test_suite(self, test_cases: List[Dict[str, Any]]) -> List[TestResult]:
        """运行测试套件"""
        logger.info(f"Running {len(test_cases)} test cases")

        results = []
        for test_case in test_cases:
            result = await self.run_test_case(test_case)
            results.append(result)

            # 记录测试结果
            if result.success:
                logger.info(f"✅ {result.test_name} - {result.response_time:.3f}s")
            else:
                logger.error(f"❌ {result.test_name} - {result.error_message}")

        return results

    async def run_concurrent_tests(self, test_cases: List[Dict[str, Any]]) -> List[TestResult]:
        """并发运行测试"""
        logger.info(f"Running {len(test_cases)} test cases concurrently")

        semaphore = asyncio.Semaphore(self.config.concurrent_requests)

        async def run_with_semaphore(test_case):
            async with semaphore:
                return await self.run_test_case(test_case)

        results = await asyncio.gather(
            *[run_with_semaphore(test_case) for test_case in test_cases],
            return_exceptions=True
        )

        # 过滤异常并记录
        valid_results = []
        for result in results:
            if isinstance(result, TestResult):
                valid_results.append(result)
                if result.success:
                    logger.info(f"✅ {result.test_name} - {result.response_time:.3f}s")
                else:
                    logger.error(f"❌ {result.test_name} - {result.error_message}")
            else:
                logger.error(f"❌ Test execution error: {result}")

        return valid_results

    def generate_test_report(self, results: List[TestResult]) -> Dict[str, Any]:
        """生成测试报告"""
        total_tests = len(results)
        passed_tests = len([r for r in results if r.success])
        failed_tests = total_tests - passed_tests

        response_times = [r.response_time for r in results if r.response_time > 0]

        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "generated_at": datetime.utcnow().isoformat()
            },
            "performance": {
                "avg_response_time": statistics.mean(response_times) if response_times else 0,
                "min_response_time": min(response_times) if response_times else 0,
                "max_response_time": max(response_times) if response_times else 0,
                "median_response_time": statistics.median(response_times) if response_times else 0,
                "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0,
                "p99_response_time": statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else 0
            },
            "endpoints": {},
            "errors": []
        }

        # 按端点统计
        endpoint_stats = {}
        for result in results:
            endpoint_key = f"{result.method} {result.endpoint}"
            if endpoint_key not in endpoint_stats:
                endpoint_stats[endpoint_key] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "response_times": []
                }

            endpoint_stats[endpoint_key]["total"] += 1
            endpoint_stats[endpoint_key]["response_times"].append(result.response_time)
            if result.success:
                endpoint_stats[endpoint_key]["passed"] += 1
            else:
                endpoint_stats[endpoint_key]["failed"] += 1

        # 计算端点性能统计
        for endpoint, stats in endpoint_stats.items():
            times = stats["response_times"]
            report["endpoints"][endpoint] = {
                "total": stats["total"],
                "passed": stats["passed"],
                "failed": stats["failed"],
                "success_rate": (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0,
                "avg_response_time": statistics.mean(times) if times else 0,
                "min_response_time": min(times) if times else 0,
                "max_response_time": max(times) if times else 0
            }

        # 收集错误信息
        for result in results:
            if not result.success:
                report["errors"].append({
                    "test_name": result.test_name,
                    "endpoint": result.endpoint,
                    "method": result.method,
                    "status_code": result.status_code,
                    "error_message": result.error_message,
                    "timestamp": result.timestamp.isoformat()
                })

        return report

    async def save_report(self, report: Dict[str, Any], filename: Optional[str] = None):
        """保存测试报告"""
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"api_test_report_{timestamp}.json"

        filepath = f"tests/reports/{filename}"
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Test report saved to: {filepath}")
        return filepath


# 测试用例定义
def get_test_cases() -> List[Dict[str, Any]]:
    """获取所有测试用例"""
    return [
        # 健康检查测试
        {
            "name": "Health Check",
            "method": "GET",
            "endpoint": "/api/v1/health",
            "expected_status": 200
        },
        {
            "name": "API Status",
            "method": "GET",
            "endpoint": "/api/v1/status",
            "expected_status": 200
        },

        # 模型列表测试
        {
            "name": "Get Models",
            "method": "GET",
            "endpoint": "/api/v1/models",
            "expected_status": 200
        },

        # 认证测试（需要认证）
        {
            "name": "Get Developer Profile",
            "method": "GET",
            "endpoint": "/api/v1/developer/auth/me",
            "expected_status": 200,
            "requires_auth": True
        },

        # API密钥管理测试
        {
            "name": "Create API Key",
            "method": "POST",
            "endpoint": "/api/v1/developer/keys",
            "json": {
                "name": "Test API Key",
                "permissions": ["chat", "usage"]
            },
            "expected_status": 200,
            "requires_auth": True,
            "resource_type": "api_keys",
            "resource_id": "data.id"
        },
        {
            "name": "List API Keys",
            "method": "GET",
            "endpoint": "/api/v1/developer/keys",
            "expected_status": 200,
            "requires_auth": True
        },

        # 使用统计测试
        {
            "name": "Get Usage Overview",
            "method": "GET",
            "endpoint": "/api/v1/developer/usage/overview",
            "params": {"days": 30},
            "expected_status": 200,
            "requires_auth": True
        },
        {
            "name": "Get Usage Analytics",
            "method": "GET",
            "endpoint": "/api/v1/developer/usage/analytics",
            "params": {"days": 30},
            "expected_status": 200,
            "requires_auth": True
        },

        # 批量处理测试
        {
            "name": "Create Batch Generation Job",
            "method": "POST",
            "endpoint": "/api/v1/developer/batch/generation",
            "json": {
                "name": "Test Batch Job",
                "model": "gpt-4o-mini",
                "prompts": ["Test prompt 1", "Test prompt 2"],
                "max_concurrent_tasks": 2
            },
            "expected_status": 200,
            "requires_auth": True,
            "resource_type": "batch_jobs",
            "resource_id": "data.job_id"
        },
        {
            "name": "Get Batch Job Status",
            "method": "GET",
            "endpoint": "/api/v1/developer/batch/jobs",
            "expected_status": 200,
            "requires_auth": True
        },

        # 监控测试
        {
            "name": "Get System Metrics",
            "method": "GET",
            "endpoint": "/api/v1/monitoring/metrics",
            "expected_status": 200,
            "requires_auth": True
        },
        {
            "name": "Get Alerts",
            "method": "GET",
            "endpoint": "/api/v1/monitoring/alerts",
            "expected_status": 200,
            "requires_auth": True
        },

        # 错误处理测试
        {
            "name": "Invalid Endpoint",
            "method": "GET",
            "endpoint": "/api/v1/invalid/endpoint",
            "expected_status": 404
        },
        {
            "name": "Unauthorized Access",
            "method": "GET",
            "endpoint": "/api/v1/developer/auth/me",
            "expected_status": 401,
            "requires_auth": False
        },
        {
            "name": "Invalid Request Data",
            "method": "POST",
            "endpoint": "/api/v1/developer/auth/login",
            "json": {"invalid": "data"},
            "expected_status": 422
        }
    ]


async def run_api_tests():
    """运行API测试主函数"""
    # 测试配置
    config = TestConfig(
        base_url="http://localhost:8001",
        timeout=30,
        max_retries=3,
        concurrent_requests=5,
        test_user_credentials={
            "email": "test@example.com",
            "password": "test_password123"
        }
    )

    # 创建测试运行器
    test_runner = APITestRunner(config)

    try:
        # 设置测试环境
        await test_runner.setup()

        # 获取测试用例
        test_cases = get_test_cases()

        # 过滤需要认证的测试用例
        auth_required_cases = [tc for tc in test_cases if tc.get("requires_auth", False)]
        no_auth_cases = [tc for tc in test_cases if not tc.get("requires_auth", False)]

        # 运行不需要认证的测试
        logger.info("Running tests without authentication...")
        no_auth_results = await test_runner.run_test_suite(no_auth_cases)

        # 如果有认证信息，运行需要认证的测试
        if test_runner.auth_token and auth_required_cases:
            logger.info("Running tests with authentication...")
            auth_results = await test_runner.run_test_suite(auth_required_cases)
        else:
            auth_results = []
            logger.warning("Skipping authenticated tests - no valid auth token")

        # 合并所有结果
        all_results = no_auth_results + auth_results

        # 生成报告
        report = test_runner.generate_test_report(all_results)
        report_path = await test_runner.save_report(report)

        # 输出摘要
        print(f"\n{'='*50}")
        print(f"API Test Summary")
        print(f"{'='*50}")
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Passed: {report['summary']['passed']}")
        print(f"Failed: {report['summary']['failed']}")
        print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
        print(f"Average Response Time: {report['performance']['avg_response_time']:.3f}s")
        print(f"Report saved to: {report_path}")

        if report['summary']['failed'] > 0:
            print(f"\nFailed Tests:")
            for error in report['errors'][:5]:  # 显示前5个错误
                print(f"  - {error['test_name']}: {error['error_message']}")

        return report

    finally:
        # 清理测试环境
        await test_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(run_api_tests())