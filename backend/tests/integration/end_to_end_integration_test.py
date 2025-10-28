"""
Week 8 Day 6 - End-to-End System Integration Testing
This test suite validates the entire AI Hub platform's integration and performance
"""

import pytest
import asyncio
import time
import json
import aiohttp
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

from fastapi.testclient import TestClient
from httpx import AsyncClient
from backend.main import app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TestMetrics:
    """Test execution metrics collection"""
    test_name: str
    start_time: float
    end_time: float
    success: bool
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    data: Optional[Dict] = None


class TestEnvironment:
    """Test environment configuration and setup"""

    def __init__(self):
        self.base_url = "http://localhost:8001"
        self.api_endpoints = {
            "health": "/api/v1/health",
            "models": "/api/v1/models",
            "chat_stream": "/api/v1/chat/stream",
            "chat_completion": "/api/v1/chat/completions",
            "sessions": "/api/v1/sessions",
            "stats": "/api/v1/stats",
            "performance_stats": "/api/v1/performance",
            "monitoring_dashboard": "/api/v1/monitoring-new/dashboard",
            "cache_stats": "/api/v1/cache/stats",
            "alerts": "/api/v1/alerts/rules",
            "performance_optimization": "/api/v1/performance-optimization/stats"
        }
        self.test_data = self._generate_test_data()
        self.metrics: List[TestMetrics] = []

    def _generate_test_data(self) -> Dict:
        """Generate test data for various scenarios"""
        return {
            "chat_prompts": [
                "Hello, how are you?",
                "What is artificial intelligence?",
                "Explain machine learning",
                "Write a Python function to sort a list",
                "What are the benefits of cloud computing?",
                "How does neural network work?",
                "Explain the concept of microservices",
                "What is DevOps?"
            ],
            "user_scenarios": [
                {"user_type": "developer", "expected_response_time": 2.0},
                {"user_type": "enterprise", "expected_response_time": 1.5},
                {"user_type": "individual", "expected_response_time": 3.0}
            ],
            "load_patterns": {
                "light": {"concurrent_users": 5, "duration": 30},
                "moderate": {"concurrent_users": 20, "duration": 60},
                "heavy": {"concurrent_users": 50, "duration": 120}
            }
        }

    async def setup_test_environment(self):
        """Setup test environment and verify all services are ready"""
        logger.info("Setting up test environment...")

        # Verify API server is running
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}{self.api_endpoints['health']}") as response:
                    if response.status != 200:
                        raise Exception(f"Health check failed: {response.status}")
            logger.info("✅ API server is healthy")
        except Exception as e:
            logger.error(f"❌ API server setup failed: {e}")
            raise

        # Verify monitoring systems
        await self._verify_monitoring_systems()

        # Verify cache system
        await self._verify_cache_system()

        # Initialize test data
        await self._setup_test_data()

        logger.info("✅ Test environment setup complete")

    async def _verify_monitoring_systems(self):
        """Verify monitoring systems are operational"""
        monitoring_endpoints = [
            "monitoring_dashboard",
            "performance_stats",
            "performance_optimization"
        ]

        async with aiohttp.ClientSession() as session:
            for endpoint in monitoring_endpoints:
                try:
                    url = f"{self.base_url}{self.api_endpoints[endpoint]}"
                    async with session.get(url) as response:
                        if response.status == 200:
                            logger.info(f"✅ {endpoint} monitoring is active")
                        else:
                            logger.warning(f"⚠️ {endpoint} monitoring returned status: {response.status}")
                except Exception as e:
                    logger.warning(f"⚠️ {endpoint} monitoring check failed: {e}")

    async def _verify_cache_system(self):
        """Verify cache system is operational"""
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.base_url}{self.api_endpoints['cache_stats']}"
                async with session.get(url) as response:
                    if response.status == 200:
                        cache_data = await response.json()
                        logger.info(f"✅ Cache system operational: {cache_data.get('status', 'unknown')}")
                    else:
                        logger.warning(f"⚠️ Cache system status: {response.status}")
            except Exception as e:
                logger.warning(f"⚠️ Cache system check failed: {e}")

    async def _setup_test_data(self):
        """Setup test data and sessions for integration testing"""
        # Create test sessions for different user types
        async with aiohttp.ClientSession() as session:
            for scenario in self.test_data["user_scenarios"]:
                try:
                    session_data = {
                        "user_id": f"test_user_{scenario['user_type']}",
                        "user_type": scenario["user_type"],
                        "created_at": datetime.now().isoformat(),
                        "test_environment": True
                    }

                    url = f"{self.base_url}{self.api_endpoints['sessions']}"
                    async with session.post(url, json=session_data) as response:
                        if response.status in [200, 201]:
                            logger.info(f"✅ Created test session for {scenario['user_type']}")
                        else:
                            logger.warning(f"⚠️ Failed to create test session for {scenario['user_type']}")
                except Exception as e:
                    logger.warning(f"⚠️ Test session creation failed: {e}")

    def record_metric(self, test_name: str, start_time: float, end_time: float,
                     success: bool, error_message: str = None, data: Dict = None):
        """Record test execution metric"""
        metric = TestMetrics(
            test_name=test_name,
            start_time=start_time,
            end_time=end_time,
            success=success,
            response_time=end_time - start_time,
            error_message=error_message,
            data=data
        )
        self.metrics.append(metric)

    def generate_test_report(self) -> Dict:
        """Generate comprehensive test report"""
        if not self.metrics:
            return {"error": "No test metrics available"}

        total_tests = len(self.metrics)
        successful_tests = sum(1 for m in self.metrics if m.success)
        failed_tests = total_tests - successful_tests

        response_times = [m.response_time for m in self.metrics if m.response_time]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0

        # Group metrics by test type
        test_groups = {}
        for metric in self.metrics:
            test_type = metric.test_name.split('_')[0] if '_' in metric.test_name else 'unknown'
            if test_type not in test_groups:
                test_groups[test_type] = []
            test_groups[test_type].append(metric)

        return {
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": (successful_tests / total_tests) * 100,
                "overall_health": "HEALTHY" if successful_tests / total_tests > 0.95 else "NEEDS_ATTENTION"
            },
            "performance": {
                "average_response_time": round(avg_response_time, 3),
                "max_response_time": round(max_response_time, 3),
                "min_response_time": round(min_response_time, 3),
                "total_test_duration": round(max(m.end_time for m in self.metrics) - min(m.start_time for m in self.metrics), 2)
            },
            "test_groups": {
                group_name: {
                    "total": len(group_metrics),
                    "successful": sum(1 for m in group_metrics if m.success),
                    "avg_response_time": round(sum(m.response_time or 0 for m in group_metrics) / len(group_metrics), 3)
                }
                for group_name, group_metrics in test_groups.items()
            },
            "failed_tests": [
                {
                    "test_name": m.test_name,
                    "error_message": m.error_message,
                    "response_time": m.response_time
                }
                for m in self.metrics if not m.success
            ],
            "recommendations": self._generate_recommendations()
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate system improvement recommendations based on test results"""
        recommendations = []

        # Check response times
        slow_tests = [m for m in self.metrics if m.response_time and m.response_time > 2.0]
        if slow_tests:
            recommendations.append("Some endpoints show slow response times (>2s). Consider optimization")

        # Check failure rates
        failure_rate = sum(1 for m in self.metrics if not m.success) / len(self.metrics)
        if failure_rate > 0.05:
            recommendations.append("High failure rate detected. Review error handling and system stability")

        # Check monitoring coverage
        monitoring_tests = [m for m in self.metrics if 'monitoring' in m.test_name.lower()]
        if len(monitoring_tests) < 5:
            recommendations.append("Limited monitoring coverage. Expand monitoring integration tests")

        if not recommendations:
            recommendations.append("System integration looks good. Continue regular testing")

        return recommendations


class EndToEndIntegrationTestSuite:
    """Comprehensive End-to-End Integration Test Suite"""

    def __init__(self):
        self.env = TestEnvironment()
        self.client = TestClient(app)

    async def run_all_tests(self) -> Dict:
        """Run all integration tests"""
        logger.info("🚀 Starting End-to-End Integration Test Suite")

        start_time = time.time()

        try:
            # Setup test environment
            await self.env.setup_test_environment()

            # Run all integration tests
            await self.test_system_health_integration()
            await self.test_ai_services_integration()
            await self.test_monitoring_systems_integration()
            await self.test_cache_system_integration()
            await self.test_performance_optimization_integration()
            await self.test_security_integration()
            await self.test_data_flow_integration()
            await self.test_error_handling_integration()
            await self.test_concurrent_user_scenarios()
            await self.test_system_resilience()

        except Exception as e:
            logger.error(f"❌ Integration test suite failed: {e}")
            raise

        end_time = time.time()
        logger.info(f"✅ Integration test suite completed in {end_time - start_time:.2f} seconds")

        # Generate comprehensive report
        report = self.env.generate_test_report()
        report["execution_summary"] = {
            "total_duration": round(end_time - start_time, 2),
            "timestamp": datetime.now().isoformat()
        }

        return report

    async def test_system_health_integration(self):
        """Test system health and basic functionality integration"""
        logger.info("🏥 Testing System Health Integration...")

        # Test basic health endpoint
        start_time = time.time()
        try:
            response = self.client.get(self.env.api_endpoints["health"])
            success = response.status_code == 200
            data = response.json() if success else None
            self.env.record_metric(
                "health_endpoint", start_time, time.time(),
                success, None if success else f"Status: {response.status_code}", data
            )
            logger.info(f"✅ Health endpoint: {response.status_code}")
        except Exception as e:
            self.env.record_metric("health_endpoint", start_time, time.time(), False, str(e))
            logger.error(f"❌ Health endpoint failed: {e}")

        # Test API status and configuration
        start_time = time.time()
        try:
            response = self.client.get("/api/v1/status")
            success = response.status_code == 200
            data = response.json() if success else None
            self.env.record_metric(
                "api_status", start_time, time.time(),
                success, None if success else f"Status: {response.status_code}", data
            )
            logger.info(f"✅ API status: {response.status_code}")
        except Exception as e:
            self.env.record_metric("api_status", start_time, time.time(), False, str(e))
            logger.error(f"❌ API status failed: {e}")

        # Test models availability
        start_time = time.time()
        try:
            response = self.client.get(self.env.api_endpoints["models"])
            success = response.status_code == 200
            data = response.json() if success else None
            self.env.record_metric(
                "models_availability", start_time, time.time(),
                success, None if success else f"Status: {response.status_code}", data
            )
            if success and data:
                model_count = len(data.get("models", []))
                logger.info(f"✅ Models available: {model_count}")
            else:
                logger.error("❌ Models endpoint failed")
        except Exception as e:
            self.env.record_metric("models_availability", start_time, time.time(), False, str(e))
            logger.error(f"❌ Models availability check failed: {e}")

    async def test_ai_services_integration(self):
        """Test AI services integration and functionality"""
        logger.info("🤖 Testing AI Services Integration...")

        # Test streaming chat
        for i, prompt in enumerate(self.env.test_data["chat_prompts"][:3]):  # Test first 3 prompts
            start_time = time.time()
            try:
                response = self.client.get(
                    f"{self.env.api_endpoints['chat_stream']}?prompt={prompt}&model=grok-4-fast:free"
                )
                success = response.status_code == 200
                # For streaming, check if response starts correctly
                stream_data = response.content.decode('utf-8') if hasattr(response, 'content') else ""
                self.env.record_metric(
                    f"chat_stream_{i+1}", start_time, time.time(),
                    success, None if success else f"Status: {response.status_code}",
                    {"prompt_length": len(prompt), "stream_received": bool(stream_data)}
                )
                logger.info(f"✅ Chat stream test {i+1}: {response.status_code}")
            except Exception as e:
                self.env.record_metric(f"chat_stream_{i+1}", start_time, time.time(), False, str(e))
                logger.error(f"❌ Chat stream test {i+1} failed: {e}")

        # Test session management
        start_time = time.time()
        try:
            session_data = {
                "user_id": "test_integration_user",
                "messages": [{"role": "user", "content": "Test message"}],
                "metadata": {"test": True}
            }
            response = self.client.post(self.env.api_endpoints["sessions"], json=session_data)
            success = response.status_code in [200, 201]
            data = response.json() if success else None
            self.env.record_metric(
                "session_creation", start_time, time.time(),
                success, None if success else f"Status: {response.status_code}", data
            )
            logger.info(f"✅ Session creation: {response.status_code}")
        except Exception as e:
            self.env.record_metric("session_creation", start_time, time.time(), False, str(e))
            logger.error(f"❌ Session creation failed: {e}")

    async def test_monitoring_systems_integration(self):
        """Test monitoring systems integration"""
        logger.info("📊 Testing Monitoring Systems Integration...")

        monitoring_endpoints = [
            ("monitoring_dashboard", "Dashboard Data"),
            ("performance_stats", "Performance Stats"),
            ("performance_optimization", "Performance Optimization")
        ]

        for endpoint_key, description in monitoring_endpoints:
            start_time = time.time()
            try:
                response = self.client.get(self.env.api_endpoints[endpoint_key])
                success = response.status_code == 200
                data = response.json() if success else None
                self.env.record_metric(
                    f"monitoring_{endpoint_key}", start_time, time.time(),
                    success, None if success else f"Status: {response.status_code}", data
                )
                logger.info(f"✅ {description}: {response.status_code}")
            except Exception as e:
                self.env.record_metric(f"monitoring_{endpoint_key}", start_time, time.time(), False, str(e))
                logger.error(f"❌ {description} failed: {e}")

    async def test_cache_system_integration(self):
        """Test cache system integration"""
        logger.info("💾 Testing Cache System Integration...")

        # Test cache statistics
        start_time = time.time()
        try:
            response = self.client.get(self.env.api_endpoints["cache_stats"])
            success = response.status_code == 200
            data = response.json() if success else None
            self.env.record_metric(
                "cache_statistics", start_time, time.time(),
                success, None if success else f"Status: {response.status_code}", data
            )
            logger.info(f"✅ Cache statistics: {response.status_code}")
        except Exception as e:
            self.env.record_metric("cache_statistics", start_time, time.time(), False, str(e))
            logger.error(f"❌ Cache statistics failed: {e}")

    async def test_performance_optimization_integration(self):
        """Test performance optimization system integration"""
        logger.info("⚡ Testing Performance Optimization Integration...")

        # Test performance optimization endpoint
        start_time = time.time()
        try:
            response = self.client.get("/api/v1/performance-optimization/dashboard")
            success = response.status_code == 200
            data = response.json() if success else None
            self.env.record_metric(
                "performance_dashboard", start_time, time.time(),
                success, None if success else f"Status: {response.status_code}", data
            )
            logger.info(f"✅ Performance dashboard: {response.status_code}")
        except Exception as e:
            self.env.record_metric("performance_dashboard", start_time, time.time(), False, str(e))
            logger.error(f"❌ Performance dashboard failed: {e}")

    async def test_security_integration(self):
        """Test security integration"""
        logger.info("🔒 Testing Security Integration...")

        # Test CORS headers
        start_time = time.time()
        try:
            response = self.client.options(self.env.api_endpoints["health"])
            cors_headers = {
                'access-control-allow-origin',
                'access-control-allow-methods',
                'access-control-allow-headers'
            }
            has_cors = any(header in [h.lower() for h in response.headers.keys()] for header in cors_headers)
            self.env.record_metric(
                "cors_security", start_time, time.time(),
                has_cors, None if has_cors else "Missing CORS headers",
                {"cors_enabled": has_cors}
            )
            logger.info(f"✅ CORS security check: {'Enabled' if has_cors else 'Disabled'}")
        except Exception as e:
            self.env.record_metric("cors_security", start_time, time.time(), False, str(e))
            logger.error(f"❌ CORS security check failed: {e}")

    async def test_data_flow_integration(self):
        """Test data flow between system components"""
        logger.info("🔄 Testing Data Flow Integration...")

        # Test chat → session → monitoring data flow
        start_time = time.time()
        try:
            # Step 1: Create a chat interaction
            chat_response = self.client.get(
                f"{self.env.api_endpoints['chat_stream']}?prompt=Integration test prompt"
            )

            # Step 2: Check if session was updated
            session_response = self.client.get(self.env.api_endpoints["sessions"])

            # Step 3: Check monitoring data
            monitoring_response = self.client.get(self.env.api_endpoints["monitoring_dashboard"])

            success = (chat_response.status_code == 200 and
                      session_response.status_code == 200 and
                      monitoring_response.status_code == 200)

            self.env.record_metric(
                "data_flow_chat_session_monitoring", start_time, time.time(),
                success, None if success else "Data flow interruption",
                {
                    "chat_status": chat_response.status_code,
                    "session_status": session_response.status_code,
                    "monitoring_status": monitoring_response.status_code
                }
            )
            logger.info(f"✅ Data flow integration: {'Success' if success else 'Failed'}")
        except Exception as e:
            self.env.record_metric("data_flow_chat_session_monitoring", start_time, time.time(), False, str(e))
            logger.error(f"❌ Data flow integration failed: {e}")

    async def test_error_handling_integration(self):
        """Test error handling across the system"""
        logger.info("⚠️ Testing Error Handling Integration...")

        # Test invalid endpoint
        start_time = time.time()
        try:
            response = self.client.get("/api/v1/nonexistent-endpoint")
            success = response.status_code == 404  # Expected 404
            self.env.record_metric(
                "error_handling_404", start_time, time.time(),
                success, None if success else f"Expected 404, got {response.status_code}",
                {"status_code": response.status_code}
            )
            logger.info(f"✅ 404 error handling: {'Correct' if success else 'Incorrect'}")
        except Exception as e:
            self.env.record_metric("error_handling_404", start_time, time.time(), False, str(e))
            logger.error(f"❌ 404 error handling test failed: {e}")

        # Test invalid request data
        start_time = time.time()
        try:
            response = self.client.post(self.env.api_endpoints["sessions"], json={"invalid": "data"})
            success = response.status_code in [400, 422]  # Expected validation error
            self.env.record_metric(
                "error_handling_validation", start_time, time.time(),
                success, None if success else f"Expected validation error, got {response.status_code}",
                {"status_code": response.status_code}
            )
            logger.info(f"✅ Validation error handling: {'Correct' if success else 'Incorrect'}")
        except Exception as e:
            self.env.record_metric("error_handling_validation", start_time, time.time(), False, str(e))
            logger.error(f"❌ Validation error handling test failed: {e}")

    async def test_concurrent_user_scenarios(self):
        """Test concurrent user scenarios"""
        logger.info("👥 Testing Concurrent User Scenarios...")

        async def simulate_user_session(user_id: str, scenario: Dict) -> Dict:
            """Simulate a single user session"""
            start_time = time.time()
            try:
                # Simulate user actions
                actions = [
                    self.client.get(self.env.api_endpoints["health"]),
                    self.client.get(self.env.api_endpoints["models"]),
                    self.client.get(f"{self.env.api_endpoints['chat_stream']}?prompt=Hello from user {user_id}")
                ]

                # Check if all actions succeed
                success_count = sum(1 for action in actions if action.status_code == 200)
                success = success_count == len(actions)

                end_time = time.time()

                return {
                    "user_id": user_id,
                    "success": success,
                    "response_time": end_time - start_time,
                    "success_rate": success_count / len(actions),
                    "scenario": scenario
                }
            except Exception as e:
                return {
                    "user_id": user_id,
                    "success": False,
                    "error": str(e),
                    "scenario": scenario
                }

        # Test different load patterns
        for pattern_name, pattern_config in self.env.test_data["load_patterns"].items():
            start_time = time.time()

            # Create concurrent user sessions
            concurrent_users = []
            for i in range(pattern_config["concurrent_users"]):
                user_id = f"concurrent_user_{pattern_name}_{i}"
                scenario = self.env.test_data["user_scenarios"][i % len(self.env.test_data["user_scenarios"])]
                concurrent_users.append(simulate_user_session(user_id, scenario))

            # Execute concurrent sessions
            results = await asyncio.gather(*concurrent_users)

            # Analyze results
            successful_users = sum(1 for result in results if result.get("success", False))
            success_rate = successful_users / len(results) if results else 0

            avg_response_time = sum(result.get("response_time", 0) for result in results) / len(results) if results else 0

            end_time = time.time()

            self.env.record_metric(
                f"concurrent_users_{pattern_name}", start_time, end_time,
                success_rate > 0.8,  # 80% success rate threshold
                f"Success rate: {success_rate:.2%}" if success_rate <= 0.8 else None,
                {
                    "concurrent_users": pattern_config["concurrent_users"],
                    "successful_users": successful_users,
                    "success_rate": success_rate,
                    "avg_response_time": avg_response_time,
                    "duration": end_time - start_time
                }
            )

            logger.info(f"✅ Concurrent users ({pattern_name}): {successful_users}/{len(results)} successful, "
                       f"Response time: {avg_response_time:.2f}s")

    async def test_system_resilience(self):
        """Test system resilience under stress conditions"""
        logger.info("💪 Testing System Resilience...")

        # Test rapid consecutive requests
        start_time = time.time()
        rapid_requests = []
        for i in range(20):
            try:
                response = self.client.get(self.env.api_endpoints["health"])
                rapid_requests.append({"request": i, "status": response.status_code, "success": response.status_code == 200})
            except Exception as e:
                rapid_requests.append({"request": i, "error": str(e), "success": False})

        success_rate = sum(1 for req in rapid_requests if req.get("success", False)) / len(rapid_requests)
        end_time = time.time()

        self.env.record_metric(
            "rapid_requests_resilience", start_time, end_time,
            success_rate > 0.9,  # 90% success rate threshold
            f"Success rate: {success_rate:.2%}" if success_rate <= 0.9 else None,
            {
                "total_requests": len(rapid_requests),
                "successful_requests": sum(1 for req in rapid_requests if req.get("success", False)),
                "success_rate": success_rate,
                "duration": end_time - start_time,
                "requests_per_second": len(rapid_requests) / (end_time - start_time)
            }
        )

        logger.info(f"✅ Rapid requests resilience: {success_rate:.2%} success rate")


# Pytest test functions
@pytest.fixture
async def integration_test_suite():
    """Fixture for integration test suite"""
    suite = EndToEndIntegrationTestSuite()
    return suite


@pytest.mark.asyncio
async def test_full_system_integration(integration_test_suite):
    """Test complete system integration"""
    report = await integration_test_suite.run_all_tests()

    # Assertions for overall system health
    assert report["summary"]["success_rate"] >= 90.0, f"System integration success rate too low: {report['summary']['success_rate']}%"
    assert report["summary"]["total_tests"] >= 20, "Insufficient number of integration tests executed"
    assert report["performance"]["average_response_time"] <= 2.0, f"Average response time too high: {report['performance']['average_response_time']}s"

    # Log detailed report
    logger.info("📊 System Integration Report:")
    logger.info(f"  Success Rate: {report['summary']['success_rate']:.2f}%")
    logger.info(f"  Total Tests: {report['summary']['total_tests']}")
    logger.info(f"  Average Response Time: {report['performance']['average_response_time']:.3f}s")
    logger.info(f"  System Health: {report['summary']['overall_health']}")

    if report["failed_tests"]:
        logger.warning("❌ Failed Tests:")
        for test in report["failed_tests"]:
            logger.warning(f"  - {test['test_name']}: {test['error_message']}")

    if report["recommendations"]:
        logger.info("💡 Recommendations:")
        for rec in report["recommendations"]:
            logger.info(f"  - {rec}")


@pytest.mark.asyncio
async def test_critical_endpoints_health(integration_test_suite):
    """Test critical endpoints are healthy and responsive"""
    await integration_test_suite.env.setup_test_environment()

    critical_endpoints = [
        ("health", 2.0),  # endpoint, max_response_time
        ("models", 3.0),
        ("monitoring_dashboard", 2.5)
    ]

    for endpoint_key, max_response_time in critical_endpoints:
        start_time = time.time()
        try:
            response = integration_test_suite.client.get(integration_test_suite.env.api_endpoints[endpoint_key])
            end_time = time.time()
            response_time = end_time - start_time

            assert response.status_code == 200, f"Critical endpoint {endpoint_key} returned {response.status_code}"
            assert response_time <= max_response_time, f"Critical endpoint {endpoint_key} too slow: {response_time:.2f}s"

            logger.info(f"✅ Critical endpoint {endpoint_key}: {response.status_code} in {response_time:.2f}s")
        except Exception as e:
            logger.error(f"❌ Critical endpoint {endpoint_key} failed: {e}")
            raise


if __name__ == "__main__":
    # Run the integration test suite directly
    async def main():
        suite = EndToEndIntegrationTestSuite()
        report = await suite.run_all_tests()

        print("\n" + "="*80)
        print("🏁 END-TO-END SYSTEM INTEGRATION TEST REPORT")
        print("="*80)

        print(json.dumps(report, indent=2, default=str))

        print(f"\n✅ Integration Tests Completed:")
        print(f"   Success Rate: {report['summary']['success_rate']:.2f}%")
        print(f"   Total Tests: {report['summary']['total_tests']}")
        print(f"   Average Response Time: {report['performance']['average_response_time']:.3f}s")
        print(f"   System Health: {report['summary']['overall_health']}")

        if report["failed_tests"]:
            print(f"\n❌ Failed Tests ({len(report['failed_tests'])}):")
            for test in report["failed_tests"]:
                print(f"   - {test['test_name']}: {test['error_message']}")

        if report["recommendations"]:
            print(f"\n💡 Recommendations:")
            for rec in report["recommendations"]:
                print(f"   - {rec}")

        print("\n" + "="*80)

    asyncio.run(main())