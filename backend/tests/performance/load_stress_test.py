"""
Week 8 Day 6 - Load and Stress Testing Suite
Comprehensive performance testing for AI Hub platform
"""

import pytest
import asyncio
import time
import json
import random
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import logging
import aiohttp
import psutil
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from fastapi.testclient import TestClient
from backend.main import app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LoadTestMetrics:
    """Load test metrics collection"""
    endpoint: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    response_times: List[float] = field(default_factory=list)
    status_codes: Dict[int, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    throughput: float = 0.0  # requests per second

    def calculate_statistics(self) -> Dict:
        """Calculate detailed response time statistics"""
        if not self.response_times:
            return {}

        return {
            "count": len(self.response_times),
            "min": min(self.response_times),
            "max": max(self.response_times),
            "mean": statistics.mean(self.response_times),
            "median": statistics.median(self.response_times),
            "p90": np.percentile(self.response_times, 90),
            "p95": np.percentile(self.response_times, 95),
            "p99": np.percentile(self.response_times, 99),
            "std_dev": statistics.stdev(self.response_times) if len(self.response_times) > 1 else 0
        }

    def calculate_throughput(self) -> float:
        """Calculate requests per second"""
        duration = self.end_time - self.start_time
        return self.total_requests / duration if duration > 0 else 0


class LoadTestScenarios:
    """Predefined load test scenarios"""

    @staticmethod
    def get_basic_load_scenarios() -> List[Dict]:
        """Get basic load test scenarios"""
        return [
            {
                "name": "Light_Load",
                "concurrent_users": 5,
                "requests_per_user": 10,
                "duration_seconds": 30,
                "ramp_up_time": 5,
                "description": "Light load to verify basic functionality"
            },
            {
                "name": "Moderate_Load",
                "concurrent_users": 20,
                "requests_per_user": 25,
                "duration_seconds": 60,
                "ramp_up_time": 10,
                "description": "Moderate load for normal usage patterns"
            },
            {
                "name": "Heavy_Load",
                "concurrent_users": 50,
                "requests_per_user": 50,
                "duration_seconds": 120,
                "ramp_up_time": 15,
                "description": "Heavy load for peak usage scenarios"
            },
            {
                "name": "Peak_Load",
                "concurrent_users": 100,
                "requests_per_user": 100,
                "duration_seconds": 180,
                "ramp_up_time": 20,
                "description": "Peak load to test system limits"
            }
        ]

    @staticmethod
    def get_endpoints_for_testing() -> List[Dict]:
        """Get endpoints to test with load patterns"""
        return [
            {
                "name": "Health_Check",
                "url": "/api/v1/health",
                "method": "GET",
                "weight": 40,  # Percentage of total requests
                "expected_response_time": 0.5,
                "critical": True
            },
            {
                "name": "Models_List",
                "url": "/api/v1/models",
                "method": "GET",
                "weight": 20,
                "expected_response_time": 1.0,
                "critical": True
            },
            {
                "name": "API_Status",
                "url": "/api/v1/status",
                "method": "GET",
                "weight": 15,
                "expected_response_time": 0.8,
                "critical": True
            },
            {
                "name": "Sessions_List",
                "url": "/api/v1/sessions",
                "method": "GET",
                "weight": 10,
                "expected_response_time": 1.5,
                "critical": False
            },
            {
                "name": "Stats_API",
                "url": "/api/v1/stats",
                "method": "GET",
                "weight": 10,
                "expected_response_time": 2.0,
                "critical": False
            },
            {
                "name": "Chat_Stream_Light",
                "url": "/api/v1/chat/stream",
                "method": "GET",
                "params": {"prompt": "Hello", "model": "grok-4-fast:free"},
                "weight": 5,
                "expected_response_time": 5.0,
                "critical": False
            }
        ]


class SystemResourceMonitor:
    """Monitor system resources during load testing"""

    def __init__(self):
        self.monitoring = False
        self.metrics = {
            "cpu_usage": [],
            "memory_usage": [],
            "disk_usage": [],
            "network_io": [],
            "process_count": []
        }
        self.start_time = 0

    async def start_monitoring(self):
        """Start system resource monitoring"""
        self.monitoring = True
        self.start_time = time.time()
        logger.info("📊 Started system resource monitoring")

        while self.monitoring:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.metrics["cpu_usage"].append({
                    "timestamp": time.time() - self.start_time,
                    "value": cpu_percent
                })

                # Memory usage
                memory = psutil.virtual_memory()
                self.metrics["memory_usage"].append({
                    "timestamp": time.time() - self.start_time,
                    "value": memory.percent,
                    "available_gb": memory.available / (1024**3)
                })

                # Disk usage
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                self.metrics["disk_usage"].append({
                    "timestamp": time.time() - self.start_time,
                    "value": disk_percent,
                    "free_gb": disk.free / (1024**3)
                })

                # Network I/O
                network = psutil.net_io_counters()
                self.metrics["network_io"].append({
                    "timestamp": time.time() - self.start_time,
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv
                })

                # Process count
                process_count = len(psutil.pids())
                self.metrics["process_count"].append({
                    "timestamp": time.time() - self.start_time,
                    "value": process_count
                })

                await asyncio.sleep(2)  # Monitor every 2 seconds

            except Exception as e:
                logger.warning(f"⚠️ Resource monitoring error: {e}")
                await asyncio.sleep(2)

    def stop_monitoring(self) -> Dict:
        """Stop monitoring and return collected metrics"""
        self.monitoring = False
        logger.info("⏹️ Stopped system resource monitoring")

        # Calculate resource statistics
        analysis = {}
        for metric_name, data_points in self.metrics.items():
            if data_points:
                values = [point["value"] for point in data_points if "value" in point]
                if values:
                    analysis[metric_name] = {
                        "mean": statistics.mean(values),
                        "max": max(values),
                        "min": min(values),
                        "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                        "samples": len(values)
                    }

        return {
            "monitoring_duration": time.time() - self.start_time,
            "metrics": analysis,
            "raw_data": self.metrics
        }


class LoadTestExecutor:
    """Execute load tests with various scenarios"""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.scenarios = LoadTestScenarios.get_basic_load_scenarios()
        self.endpoints = LoadTestScenarios.get_endpoints_for_testing()
        self.resource_monitor = SystemResourceMonitor()
        self.test_results = []

    async def run_load_test(self, scenario: Dict) -> Dict:
        """Run a specific load test scenario"""
        logger.info(f"🚀 Starting load test: {scenario['name']}")
        logger.info(f"   Concurrent users: {scenario['concurrent_users']}")
        logger.info(f"   Duration: {scenario['duration_seconds']}s")
        logger.info(f"   Requests per user: {scenario['requests_per_user']}")

        # Start resource monitoring
        monitor_task = asyncio.create_task(self.resource_monitor.start_monitoring())

        try:
            # Prepare user tasks
            user_tasks = []
            for user_id in range(scenario["concurrent_users"]):
                user_task = self._simulate_user_session(
                    user_id=user_id,
                    scenario=scenario,
                    ramp_up_time=scenario["ramp_up_time"]
                )
                user_tasks.append(user_task)

            # Execute all user sessions concurrently
            user_results = await asyncio.gather(*user_tasks, return_exceptions=True)

            # Analyze results
            test_result = self._analyze_load_test_results(
                scenario=scenario,
                user_results=user_results
            )

            # Add resource monitoring data
            test_result["resource_usage"] = self.resource_monitor.stop_monitoring()

            self.test_results.append(test_result)
            logger.info(f"✅ Load test completed: {scenario['name']}")
            logger.info(f"   Success rate: {test_result['overall_success_rate']:.2f}%")
            logger.info(f"   Average response time: {test_result['overall_avg_response_time']:.3f}s")
            logger.info(f"   Throughput: {test_result['overall_throughput']:.2f} req/s")

            return test_result

        except Exception as e:
            self.resource_monitor.stop_monitoring()
            logger.error(f"❌ Load test failed: {scenario['name']}: {e}")
            raise

    async def _simulate_user_session(self, user_id: int, scenario: Dict, ramp_up_time: int) -> Dict:
        """Simulate a single user's session"""
        # Add ramp-up delay
        if ramp_up_time > 0:
            await asyncio.sleep(random.uniform(0, ramp_up_time))

        user_results = []
        session_start_time = time.time()

        # Generate weighted endpoint requests
        endpoint_requests = self._generate_user_requests(scenario["requests_per_user"])

        for request_config in endpoint_requests:
            try:
                result = await self._make_request(
                    endpoint=request_config,
                    user_id=user_id
                )
                user_results.append(result)

                # Add small delay between requests
                await asyncio.sleep(random.uniform(0.1, 0.5))

            except Exception as e:
                user_results.append({
                    "endpoint": request_config["name"],
                    "success": False,
                    "error": str(e),
                    "response_time": 0
                })

        session_end_time = time.time()

        return {
            "user_id": user_id,
            "session_duration": session_end_time - session_start_time,
            "total_requests": len(user_results),
            "successful_requests": sum(1 for r in user_results if r["success"]),
            "requests": user_results,
            "success_rate": sum(1 for r in user_results if r["success"]) / len(user_results) if user_results else 0
        }

    def _generate_user_requests(self, total_requests: int) -> List[Dict]:
        """Generate weighted requests for a user session"""
        requests = []

        # Create weighted distribution
        total_weight = sum(ep["weight"] for ep in self.endpoints)
        endpoint_distribution = []

        for endpoint in self.endpoints:
            count = int((endpoint["weight"] / total_weight) * total_requests)
            endpoint_distribution.extend([endpoint] * count)

        # Randomize order
        random.shuffle(endpoint_distribution)

        return endpoint_distribution

    async def _make_request(self, endpoint: Dict, user_id: int) -> Dict:
        """Make a single HTTP request"""
        start_time = time.time()
        url = f"{self.base_url}{endpoint['url']}"
        method = endpoint.get("method", "GET")
        params = endpoint.get("params", {})

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                if method == "GET":
                    async with session.get(url, params=params) as response:
                        content = await response.text()
                        status_code = response.status
                else:
                    async with session.request(method, url, json=params) as response:
                        content = await response.text()
                        status_code = response.status

                end_time = time.time()
                response_time = end_time - start_time

                return {
                    "endpoint": endpoint["name"],
                    "success": status_code == 200,
                    "status_code": status_code,
                    "response_time": response_time,
                    "content_length": len(content),
                    "user_id": user_id,
                    "timestamp": start_time
                }

        except asyncio.TimeoutError:
            end_time = time.time()
            return {
                "endpoint": endpoint["name"],
                "success": False,
                "status_code": 0,
                "response_time": end_time - start_time,
                "error": "Request timeout",
                "user_id": user_id,
                "timestamp": start_time
            }

        except Exception as e:
            end_time = time.time()
            return {
                "endpoint": endpoint["name"],
                "success": False,
                "status_code": 0,
                "response_time": end_time - start_time,
                "error": str(e),
                "user_id": user_id,
                "timestamp": start_time
            }

    def _analyze_load_test_results(self, scenario: Dict, user_results: List[Dict]) -> Dict:
        """Analyze load test results"""
        # Aggregate all requests
        all_requests = []
        for user_result in user_results:
            if isinstance(user_result, dict) and "requests" in user_result:
                all_requests.extend(user_result["requests"])

        # Calculate endpoint metrics
        endpoint_metrics = {}
        for endpoint in self.endpoints:
            endpoint_name = endpoint["name"]
            endpoint_requests = [req for req in all_requests if req.get("endpoint") == endpoint_name]

            if endpoint_requests:
                successful_requests = [req for req in endpoint_requests if req.get("success", False)]
                response_times = [req.get("response_time", 0) for req in successful_requests if req.get("response_time")]

                metrics = LoadTestMetrics(
                    endpoint=endpoint_name,
                    total_requests=len(endpoint_requests),
                    successful_requests=len(successful_requests),
                    failed_requests=len(endpoint_requests) - len(successful_requests)
                )

                if response_times:
                    metrics.response_times = response_times
                    metrics.start_time = min(req.get("timestamp", 0) for req in endpoint_requests)
                    metrics.end_time = max(req.get("timestamp", 0) for req in endpoint_requests)

                # Count status codes
                for req in endpoint_requests:
                    status = req.get("status_code", 0)
                    metrics.status_codes[status] = metrics.status_codes.get(status, 0) + 1

                # Collect errors
                for req in endpoint_requests:
                    if not req.get("success", False) and "error" in req:
                        metrics.errors.append(req["error"])

                endpoint_metrics[endpoint_name] = metrics

        # Calculate overall statistics
        total_requests = sum(metrics.total_requests for metrics in endpoint_metrics.values())
        total_successful = sum(metrics.successful_requests for metrics in endpoint_metrics.values())
        total_failed = sum(metrics.failed_requests for metrics in endpoint_metrics.values())

        all_response_times = []
        for metrics in endpoint_metrics.values():
            all_response_times.extend(metrics.response_times)

        overall_avg_response_time = statistics.mean(all_response_times) if all_response_times else 0
        overall_success_rate = (total_successful / total_requests) * 100 if total_requests > 0 else 0

        # Calculate throughput
        test_duration = scenario["duration_seconds"]
        overall_throughput = total_requests / test_duration if test_duration > 0 else 0

        return {
            "scenario": scenario,
            "overall_statistics": {
                "total_requests": total_requests,
                "successful_requests": total_successful,
                "failed_requests": total_failed,
                "success_rate": overall_success_rate,
                "average_response_time": overall_avg_response_time,
                "throughput": overall_throughput
            },
            "endpoint_metrics": {
                name: {
                    "total_requests": metrics.total_requests,
                    "success_rate": (metrics.successful_requests / metrics.total_requests * 100) if metrics.total_requests > 0 else 0,
                    "response_time_stats": metrics.calculate_statistics(),
                    "status_codes": metrics.status_codes,
                    "error_count": len(metrics.errors)
                }
                for name, metrics in endpoint_metrics.items()
            },
            "performance_against_expectations": self._compare_with_expectations(endpoint_metrics),
            "test_timestamp": datetime.now().isoformat()
        }

    def _compare_with_expectations(self, endpoint_metrics: Dict) -> Dict:
        """Compare performance with expected response times"""
        expectations = {
            ep["name"]: ep["expected_response_time"]
            for ep in self.endpoints
        }

        comparison = {}
        for endpoint_name, metrics in endpoint_metrics.items():
            expected_time = expectations.get(endpoint_name)
            if expected_time and metrics.response_times:
                avg_time = statistics.mean(metrics.response_times)
                comparison[endpoint_name] = {
                    "expected": expected_time,
                    "actual": avg_time,
                    "performance_ratio": avg_time / expected_time,
                    "meets_expectation": avg_time <= expected_time
                }

        return comparison

    async def run_all_load_tests(self) -> Dict:
        """Run all load test scenarios"""
        logger.info("🎯 Starting comprehensive load testing suite")

        all_results = []
        for scenario in self.scenarios:
            try:
                result = await self.run_load_test(scenario)
                all_results.append(result)

                # Add delay between tests for system recovery
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"❌ Load test scenario failed: {scenario['name']}: {e}")
                all_results.append({
                    "scenario": scenario,
                    "error": str(e),
                    "success": False
                })

        # Generate comprehensive report
        report = self._generate_comprehensive_report(all_results)

        logger.info("✅ Load testing suite completed")
        logger.info(f"   Total scenarios tested: {len(all_results)}")
        logger.info(f"   Overall system health: {report['system_health']['overall_status']}")

        return report

    def _generate_comprehensive_report(self, test_results: List[Dict]) -> Dict:
        """Generate comprehensive load testing report"""
        successful_tests = [result for result in test_results if "error" not in result]

        if not successful_tests:
            return {
                "system_health": {"overall_status": "FAILED"},
                "error": "No successful load tests"
            }

        # Aggregate performance metrics
        all_throughputs = [result["overall_statistics"]["throughput"] for result in successful_tests]
        all_success_rates = [result["overall_statistics"]["success_rate"] for result in successful_tests]
        all_response_times = []

        for result in successful_tests:
            for endpoint_metrics in result["endpoint_metrics"].values():
                if "response_time_stats" in endpoint_metrics and "mean" in endpoint_metrics["response_time_stats"]:
                    all_response_times.append(endpoint_metrics["response_time_stats"]["mean"])

        # Calculate system health indicators
        avg_throughput = statistics.mean(all_throughputs) if all_throughputs else 0
        avg_success_rate = statistics.mean(all_success_rates) if all_success_rates else 0
        avg_response_time = statistics.mean(all_response_times) if all_response_times else 0

        # Determine system health status
        health_score = 0
        health_score += 25 if avg_success_rate >= 95 else (avg_success_rate / 95) * 25
        health_score += 25 if avg_response_time <= 1.0 else max(0, (2.0 - avg_response_time) / 1.0 * 25)
        health_score += 25 if avg_throughput >= 50 else (avg_throughput / 50) * 25

        # Check critical endpoints performance
        critical_endpoints_performance = []
        for result in successful_tests:
            for endpoint_name, metrics in result["endpoint_metrics"].items():
                endpoint_config = next((ep for ep in self.endpoints if ep["name"] == endpoint_name), None)
                if endpoint_config and endpoint_config.get("critical", False):
                    success_rate = metrics.get("success_rate", 0)
                    critical_endpoints_performance.append(success_rate)

        if critical_endpoints_performance:
            avg_critical_performance = statistics.mean(critical_endpoints_performance)
            health_score += 25 if avg_critical_performance >= 99 else (avg_critical_performance / 99) * 25

        if health_score >= 90:
            overall_status = "EXCELLENT"
        elif health_score >= 75:
            overall_status = "GOOD"
        elif health_score >= 60:
            overall_status = "FAIR"
        else:
            overall_status = "POOR"

        return {
            "system_health": {
                "overall_status": overall_status,
                "health_score": round(health_score, 2),
                "success_rate": round(avg_success_rate, 2),
                "average_throughput": round(avg_throughput, 2),
                "average_response_time": round(avg_response_time, 3),
                "critical_endpoints_performance": critical_endpoints_performance
            },
            "test_summary": {
                "total_scenarios": len(test_results),
                "successful_scenarios": len(successful_tests),
                "failed_scenarios": len(test_results) - len(successful_tests)
            },
            "performance_benchmarks": {
                "max_throughput_achieved": max(all_throughputs) if all_throughputs else 0,
                "min_response_time_achieved": min(all_response_times) if all_response_times else 0,
                "peak_success_rate": max(all_success_rates) if all_success_rates else 0
            },
            "recommendations": self._generate_load_test_recommendations(successful_tests),
            "detailed_results": test_results,
            "test_execution_time": datetime.now().isoformat()
        }

    def _generate_load_test_recommendations(self, test_results: List[Dict]) -> List[str]:
        """Generate recommendations based on load test results"""
        recommendations = []

        # Analyze success rates
        all_success_rates = [result["overall_statistics"]["success_rate"] for result in test_results]
        if any(rate < 95 for rate in all_success_rates):
            recommendations.append("Some load scenarios show success rates below 95%. Consider optimizing error handling and increasing system capacity.")

        # Analyze response times
        slow_endpoints = []
        for result in test_results:
            for endpoint_name, metrics in result["endpoint_metrics"].items():
                if "response_time_stats" in metrics and "mean" in metrics["response_time_stats"]:
                    avg_time = metrics["response_time_stats"]["mean"]
                    if avg_time > 2.0:  # 2 second threshold
                        slow_endpoints.append(endpoint_name)

        if slow_endpoints:
            recommendations.append(f"Endpoints with slow response times detected: {', '.join(set(slow_endpoints))}. Consider caching or optimization.")

        # Analyze throughput
        all_throughputs = [result["overall_statistics"]["throughput"] for result in test_results]
        if max(all_throughputs) < 100:
            recommendations.append("System throughput could be improved. Consider horizontal scaling or async processing optimization.")

        # Analyze resource usage patterns
        resource_intensive_tests = []
        for result in test_results:
            if "resource_usage" in result:
                resource_data = result["resource_usage"]
                if "metrics" in resource_data:
                    cpu_metrics = resource_data["metrics"].get("cpu_usage", {})
                    if cpu_metrics.get("max", 0) > 80:
                        resource_intensive_tests.append(result["scenario"]["name"])

        if resource_intensive_tests:
            recommendations.append(f"High CPU usage detected in scenarios: {', '.join(resource_intensive_tests)}. Consider load balancing or performance tuning.")

        if not recommendations:
            recommendations.append("Load test performance looks good. Continue monitoring and periodic testing.")

        return recommendations


# Stress Testing Suite
class StressTestSuite:
    """Stress testing to find system limits"""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url

    async def run_stress_test(self) -> Dict:
        """Run stress test to find breaking point"""
        logger.info("💪 Starting stress testing to find system limits")

        stress_results = []

        # Test increasing concurrent users
        concurrent_user_levels = [50, 100, 200, 300, 500, 1000]
        break_point = None

        for user_level in concurrent_user_levels:
            logger.info(f"🔄 Testing with {user_level} concurrent users...")

            try:
                result = await self._run_stress_scenario(user_level)
                stress_results.append(result)

                # Check if system is breaking
                if result["overall_statistics"]["success_rate"] < 50:
                    break_point = user_level
                    logger.warning(f"⚠️ System breaking point detected at {user_level} concurrent users")
                    break

                # Cool down period
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"❌ Stress test failed at {user_level} users: {e}")
                break_point = user_level
                stress_results.append({
                    "concurrent_users": user_level,
                    "error": str(e),
                    "success": False
                })
                break

        # Analyze stress test results
        stress_report = self._analyze_stress_test_results(stress_results, break_point)

        logger.info("✅ Stress testing completed")
        logger.info(f"   System break point: {break_point or 'Not found'}")

        return stress_report

    async def _run_stress_scenario(self, concurrent_users: int) -> Dict:
        """Run a single stress test scenario"""
        start_time = time.time()

        # Create concurrent user tasks
        user_tasks = []
        for user_id in range(concurrent_users):
            user_task = self._simulate_stress_user(user_id, duration=60)
            user_tasks.append(user_task)

        # Execute all users
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)

        end_time = time.time()
        duration = end_time - start_time

        # Analyze results
        all_requests = []
        for user_result in user_results:
            if isinstance(user_result, dict) and "requests" in user_result:
                all_requests.extend(user_result["requests"])

        total_requests = len(all_requests)
        successful_requests = sum(1 for req in all_requests if req.get("success", False))
        success_rate = (successful_requests / total_requests) * 100 if total_requests > 0 else 0

        response_times = [req.get("response_time", 0) for req in all_requests if req.get("success", False) and req.get("response_time")]
        avg_response_time = statistics.mean(response_times) if response_times else 0

        return {
            "concurrent_users": concurrent_users,
            "duration": duration,
            "overall_statistics": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "success_rate": success_rate,
                "average_response_time": avg_response_time,
                "throughput": total_requests / duration if duration > 0 else 0
            },
            "timestamp": datetime.now().isoformat()
        }

    async def _simulate_stress_user(self, user_id: int, duration: int) -> Dict:
        """Simulate a stress test user"""
        requests = []
        end_time = time.time() + duration

        while time.time() < end_time:
            try:
                # Simple health check request for stress testing
                start_time = time.time()
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(f"{self.base_url}/api/v1/health") as response:
                        await response.text()  # Consume response
                        success = response.status == 200

                response_time = time.time() - start_time
                requests.append({
                    "success": success,
                    "response_time": response_time,
                    "user_id": user_id,
                    "timestamp": start_time
                })

                # Small delay between requests
                await asyncio.sleep(0.1)

            except Exception:
                requests.append({
                    "success": False,
                    "response_time": 10.0,  # timeout
                    "user_id": user_id,
                    "timestamp": time.time()
                })

        return {
            "user_id": user_id,
            "requests": requests
        }

    def _analyze_stress_test_results(self, stress_results: List[Dict], break_point: Optional[int]) -> Dict:
        """Analyze stress test results"""
        successful_results = [result for result in stress_results if "error" not in result]

        if not successful_results:
            return {
                "stress_test_summary": "FAILED",
                "break_point": break_point,
                "max_concurrent_users": 0
            }

        # Find maximum successful concurrent users
        max_successful_users = max(result["concurrent_users"] for result in successful_results)

        # Calculate performance degradation
        performance_degradation = []
        for result in successful_results:
            performance_degradation.append({
                "concurrent_users": result["concurrent_users"],
                "success_rate": result["overall_statistics"]["success_rate"],
                "response_time": result["overall_statistics"]["average_response_time"]
            })

        return {
            "stress_test_summary": "PASSED",
            "break_point": break_point,
            "max_concurrent_users": max_successful_users,
            "performance_degradation": performance_degradation,
            "recommendations": self._generate_stress_test_recommendations(successful_results, break_point)
        }

    def _generate_stress_test_recommendations(self, stress_results: List[Dict], break_point: Optional[int]) -> List[str]:
        """Generate stress test recommendations"""
        recommendations = []

        if break_point and break_point < 500:
            recommendations.append(f"System breaks at {break_point} concurrent users. Consider horizontal scaling.")

        # Analyze performance degradation patterns
        if len(stress_results) > 1:
            first_result = stress_results[0]
            last_result = stress_results[-1]

            success_rate_drop = first_result["overall_statistics"]["success_rate"] - last_result["overall_statistics"]["success_rate"]
            if success_rate_drop > 20:
                recommendations.append("Significant performance degradation under load. Implement load balancing.")

        recommendations.append("Continue stress testing regularly to monitor system capacity changes.")

        return recommendations


# Pytest test functions
@pytest.fixture
async def load_test_executor():
    """Fixture for load test executor"""
    return LoadTestExecutor()


@pytest.fixture
async def stress_test_suite():
    """Fixture for stress test suite"""
    return StressTestSuite()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_basic_load_scenarios(load_test_executor):
    """Test basic load scenarios"""
    # Test only the first two scenarios to avoid long test times
    scenarios_to_test = load_test_executor.scenarios[:2]

    all_results = []
    for scenario in scenarios_to_test:
        try:
            result = await load_test_executor.run_load_test(scenario)
            all_results.append(result)

            # Verify basic requirements
            assert result["overall_statistics"]["success_rate"] >= 90.0, f"Success rate too low: {result['overall_statistics']['success_rate']}%"
            assert result["overall_statistics"]["average_response_time"] <= 2.0, f"Response time too high: {result['overall_statistics']['average_response_time']}s"

            logger.info(f"✅ Load test '{scenario['name']}' passed")
            await asyncio.sleep(5)  # Cool down period

        except Exception as e:
            pytest.fail(f"Load test '{scenario['name']}' failed: {e}")

    # Generate and check report
    report = load_test_executor._generate_comprehensive_report(all_results)
    assert report["system_health"]["overall_status"] in ["EXCELLENT", "GOOD"], f"System health poor: {report['system_health']}"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_critical_endpoints_load(load_test_executor):
    """Test critical endpoints under load"""
    # Create a focused test for critical endpoints only
    critical_scenario = {
        "name": "Critical_Endpoints_Load",
        "concurrent_users": 20,
        "requests_per_user": 50,
        "duration_seconds": 60,
        "ramp_up_time": 10,
        "description": "Focused test on critical endpoints"
    }

    # Override endpoints to only test critical ones
    original_endpoints = load_test_executor.endpoints.copy()
    load_test_executor.endpoints = [
        ep for ep in load_test_executor.endpoints if ep.get("critical", False)
    ]

    try:
        result = await load_test_executor.run_load_test(critical_scenario)

        # Critical endpoints should maintain high performance
        assert result["overall_statistics"]["success_rate"] >= 98.0, f"Critical endpoints success rate too low: {result['overall_statistics']['success_rate']}%"
        assert result["overall_statistics"]["average_response_time"] <= 1.0, f"Critical endpoints response time too high: {result['overall_statistics']['average_response_time']}s"

        logger.info(f"✅ Critical endpoints load test passed with {result['overall_statistics']['success_rate']:.2f}% success rate")

    finally:
        # Restore original endpoints
        load_test_executor.endpoints = original_endpoints


@pytest.mark.asyncio
@pytest.mark.slow
async def test_stress_test_limits(stress_test_suite):
    """Test system limits with stress testing"""
    stress_report = await stress_test_suite.run_stress_test()

    # Verify stress test completed and found reasonable limits
    assert stress_report["stress_test_summary"] == "PASSED", "Stress test did not complete successfully"
    assert stress_report["max_concurrent_users"] >= 100, f"System should handle at least 100 concurrent users, got {stress_report['max_concurrent_users']}"

    logger.info(f"✅ Stress test passed - Max concurrent users: {stress_report['max_concurrent_users']}")
    if stress_report["break_point"]:
        logger.info(f"   System break point: {stress_report['break_point']} concurrent users")


if __name__ == "__main__":
    # Run load and stress tests directly
    async def main():
        print("🚀 Starting Load and Stress Testing Suite")
        print("=" * 80)

        # Run load tests
        load_executor = LoadTestExecutor()
        load_report = await load_executor.run_all_load_tests()

        print("\n📊 LOAD TESTING REPORT")
        print("=" * 50)
        print(f"System Health: {load_report['system_health']['overall_status']}")
        print(f"Health Score: {load_report['system_health']['health_score']}/100")
        print(f"Success Rate: {load_report['system_health']['success_rate']:.2f}%")
        print(f"Avg Throughput: {load_report['system_health']['average_throughput']:.2f} req/s")
        print(f"Avg Response Time: {load_report['system_health']['average_response_time']:.3f}s")

        if load_report['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for rec in load_report['recommendations']:
                print(f"   - {rec}")

        print("\n" + "=" * 80)

        # Run stress tests
        print("💪 Starting Stress Testing")
        print("=" * 50)

        stress_suite = StressTestSuite()
        stress_report = await stress_suite.run_stress_test()

        print("\n💪 STRESS TESTING REPORT")
        print("=" * 50)
        print(f"Stress Test Status: {stress_report['stress_test_summary']}")
        print(f"Max Concurrent Users: {stress_report['max_concurrent_users']}")
        if stress_report['break_point']:
            print(f"System Break Point: {stress_report['break_point']} concurrent users")

        if stress_report.get('recommendations'):
            print("\n💡 STRESS TEST RECOMMENDATIONS:")
            for rec in stress_report['recommendations']:
                print(f"   - {rec}")

        print("\n" + "=" * 80)
        print("✅ LOAD AND STRESS TESTING COMPLETED")

    asyncio.run(main())