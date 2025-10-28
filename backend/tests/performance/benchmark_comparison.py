"""
Week 8 Day 6 - Performance Benchmark Comparison System
Compare current system performance against baseline and optimization targets
"""

import pytest
import asyncio
import time
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging
import aiohttp
import numpy as np
from pathlib import Path

from fastapi.testclient import TestClient
from backend.main import app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkMetric:
    """Individual benchmark metric"""
    name: str
    category: str
    value: float
    unit: str
    baseline_value: Optional[float] = None
    target_value: Optional[float] = None
    improvement_percentage: Optional[float] = None

    def calculate_improvement(self) -> float:
        """Calculate improvement percentage from baseline"""
        if self.baseline_value and self.baseline_value > 0:
            improvement = ((self.baseline_value - self.value) / self.baseline_value) * 100
            self.improvement_percentage = improvement
            return improvement
        return 0.0

    def meets_target(self) -> bool:
        """Check if metric meets target value"""
        if self.target_value is not None:
            # For response times, lower is better
            if self.unit in ['seconds', 'ms', 'milliseconds']:
                return self.value <= self.target_value
            # For throughput, higher is better
            elif self.unit in ['req/s', 'requests/second', 'ops/s']:
                return self.value >= self.target_value
            # For rates, higher is better
            elif 'rate' in self.unit or '%' in self.unit:
                return self.value >= self.target_value
        return True


@dataclass
class BenchmarkCategory:
    """Benchmark category with multiple metrics"""
    name: str
    description: str
    metrics: List[BenchmarkMetric] = field(default_factory=list)
    overall_score: float = 0.0

    def calculate_category_score(self) -> float:
        """Calculate overall category score"""
        if not self.metrics:
            return 0.0

        # Weight metrics based on their importance
        weighted_scores = []
        for metric in self.metrics:
            # Check if meets target
            if metric.meets_target():
                base_score = 100.0
            else:
                base_score = max(0, 50.0 + metric.calculate_improvement())

            # Apply importance weight
            importance_weights = {
                'response_time': 1.5,
                'throughput': 1.3,
                'success_rate': 1.4,
                'resource_usage': 1.2,
                'cache_performance': 1.1
            }

            weight = importance_weights.get(metric.category, 1.0)
            weighted_score = base_score * weight
            weighted_scores.append(weighted_score)

        if weighted_scores:
            self.overall_score = statistics.mean(weighted_scores)
        else:
            self.overall_score = 0.0

        return self.overall_score


class BenchmarkBaseline:
    """Manage benchmark baseline data"""

    def __init__(self):
        self.baseline_file = Path("data/benchmarks/baseline.json")
        self.baseline_data = self._load_baseline()

    def _load_baseline(self) -> Dict:
        """Load baseline data from file"""
        try:
            if self.baseline_file.exists():
                with open(self.baseline_file, 'r') as f:
                    return json.load(f)
            else:
                logger.info("Baseline file not found, using default values")
                return self._create_default_baseline()
        except Exception as e:
            logger.warning(f"Failed to load baseline: {e}")
            return self._create_default_baseline()

    def _create_default_baseline(self) -> Dict:
        """Create default baseline values"""
        return {
            "api_endpoints": {
                "health": {
                    "response_time": 0.1,  # seconds
                    "throughput": 1000.0,   # req/s
                    "success_rate": 99.9
                },
                "models": {
                    "response_time": 0.5,
                    "throughput": 500.0,
                    "success_rate": 99.0
                },
                "chat_stream": {
                    "response_time": 3.0,
                    "throughput": 100.0,
                    "success_rate": 95.0
                }
            },
            "system_resources": {
                "cpu_usage": 50.0,    # percentage
                "memory_usage": 60.0,  # percentage
                "disk_io": 100.0       # MB/s
            },
            "cache_performance": {
                "hit_rate": 70.0,      # percentage
                "response_time": 0.001 # seconds
            }
        }

    def get_baseline_metric(self, category: str, metric_name: str) -> Optional[float]:
        """Get baseline metric value"""
        try:
            if category in self.baseline_data:
                if metric_name in self.baseline_data[category]:
                    return self.baseline_data[category][metric_name]
        except Exception as e:
            logger.warning(f"Failed to get baseline metric {category}.{metric_name}: {e}")
        return None

    def update_baseline(self, current_metrics: Dict):
        """Update baseline with current metrics"""
        try:
            self.baseline_data.update(current_metrics)
            self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.baseline_file, 'w') as f:
                json.dump(self.baseline_data, f, indent=2)
            logger.info("Baseline updated successfully")
        except Exception as e:
            logger.error(f"Failed to update baseline: {e}")


class PerformanceBenchmarkSuite:
    """Comprehensive performance benchmark suite"""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.baseline = BenchmarkBaseline()
        self.client = TestClient(app)
        self.benchmark_categories = []

        # Define target performance metrics
        self.target_metrics = {
            "api_endpoints": {
                "health": {"response_time": 0.05, "throughput": 2000.0, "success_rate": 99.9},
                "models": {"response_time": 0.3, "throughput": 800.0, "success_rate": 99.5},
                "chat_stream": {"response_time": 2.0, "throughput": 150.0, "success_rate": 97.0}
            },
            "system_resources": {
                "cpu_usage": 40.0,
                "memory_usage": 50.0,
                "disk_io": 80.0
            },
            "cache_performance": {
                "hit_rate": 85.0,
                "response_time": 0.0005
            }
        }

    async def run_full_benchmark_suite(self) -> Dict:
        """Run complete benchmark suite"""
        logger.info("🏁 Starting comprehensive performance benchmark suite")

        start_time = time.time()

        try:
            # Run all benchmark categories
            await self.benchmark_api_endpoints()
            await self.benchmark_system_resources()
            await self.benchmark_cache_performance()
            await self.benchmark_database_performance()
            await self.benchmark_monitoring_overhead()

            # Generate comprehensive report
            report = self._generate_benchmark_report()

            end_time = time.time()
            report["execution_time"] = end_time - start_time
            report["timestamp"] = datetime.now().isoformat()

            logger.info(f"✅ Benchmark suite completed in {end_time - start_time:.2f} seconds")
            logger.info(f"Overall Performance Score: {report['overall_score']:.2f}/100")

            return report

        except Exception as e:
            logger.error(f"❌ Benchmark suite failed: {e}")
            raise

    async def benchmark_api_endpoints(self):
        """Benchmark API endpoint performance"""
        logger.info("🌐 Benchmarking API Endpoints...")

        api_category = BenchmarkCategory(
            name="API Endpoints",
            description="API endpoint performance metrics"
        )

        endpoints_to_benchmark = [
            {
                "name": "health",
                "url": "/api/v1/health",
                "method": "GET",
                "iterations": 100
            },
            {
                "name": "models",
                "url": "/api/v1/models",
                "method": "GET",
                "iterations": 50
            },
            {
                "name": "status",
                "url": "/api/v1/status",
                "method": "GET",
                "iterations": 50
            },
            {
                "name": "sessions",
                "url": "/api/v1/sessions",
                "method": "GET",
                "iterations": 30
            },
            {
                "name": "chat_stream_light",
                "url": "/api/v1/chat/stream",
                "method": "GET",
                "params": {"prompt": "Hello", "model": "grok-4-fast:free"},
                "iterations": 20
            }
        ]

        for endpoint_config in endpoints_to_benchmark:
            try:
                metrics = await self._benchmark_endpoint(endpoint_config)

                # Add response time metric
                response_time_metric = BenchmarkMetric(
                    name=f"{endpoint_config['name']}_response_time",
                    category="response_time",
                    value=metrics["avg_response_time"],
                    unit="seconds",
                    baseline_value=self.baseline.get_baseline_metric("api_endpoints", endpoint_config["name"]) or 0.0,
                    target_value=self.target_metrics["api_endpoints"][endpoint_config["name"]]["response_time"] if endpoint_config["name"] in self.target_metrics["api_endpoints"] else None
                )
                api_category.metrics.append(response_time_metric)

                # Add throughput metric
                throughput_metric = BenchmarkMetric(
                    name=f"{endpoint_config['name']}_throughput",
                    category="throughput",
                    value=metrics["throughput"],
                    unit="req/s",
                    baseline_value=self.baseline.get_baseline_metric("api_endpoints", endpoint_config["name"]) or 0.0,
                    target_value=self.target_metrics["api_endpoints"][endpoint_config["name"]]["throughput"] if endpoint_config["name"] in self.target_metrics["api_endpoints"] else None
                )
                api_category.metrics.append(throughput_metric)

                # Add success rate metric
                success_rate_metric = BenchmarkMetric(
                    name=f"{endpoint_config['name']}_success_rate",
                    category="success_rate",
                    value=metrics["success_rate"],
                    unit="%",
                    baseline_value=self.baseline.get_baseline_metric("api_endpoints", endpoint_config["name"]) or 0.0,
                    target_value=self.target_metrics["api_endpoints"][endpoint_config["name"]]["success_rate"] if endpoint_config["name"] in self.target_metrics["api_endpoints"] else None
                )
                api_category.metrics.append(success_rate_metric)

                logger.info(f"✅ {endpoint_config['name']}: {metrics['avg_response_time']:.3f}s, {metrics['throughput']:.1f} req/s, {metrics['success_rate']:.1f}% success")

            except Exception as e:
                logger.error(f"❌ Failed to benchmark endpoint {endpoint_config['name']}: {e}")

        self.benchmark_categories.append(api_category)

    async def _benchmark_endpoint(self, endpoint_config: Dict) -> Dict:
        """Benchmark a single API endpoint"""
        url = f"{self.base_url}{endpoint_config['url']}"
        method = endpoint_config.get("method", "GET")
        params = endpoint_config.get("params", {})
        iterations = endpoint_config.get("iterations", 50)

        response_times = []
        successful_requests = 0

        # Use async HTTP client for better performance measurement
        async with aiohttp.ClientSession() as session:
            for i in range(iterations):
                start_time = time.time()

                try:
                    if method == "GET":
                        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            await response.text()
                            success = response.status == 200
                    else:
                        async with session.request(method, url, json=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            await response.text()
                            success = response.status == 200

                    end_time = time.time()
                    response_time = end_time - start_time

                    response_times.append(response_time)
                    if success:
                        successful_requests += 1

                except Exception:
                    end_time = time.time()
                    response_times.append(end_time - start_time)  # Count as failed request

        # Calculate metrics
        avg_response_time = statistics.mean(response_times) if response_times else 0
        total_duration = max(response_times) if response_times else 0
        throughput = iterations / total_duration if total_duration > 0 else 0
        success_rate = (successful_requests / iterations) * 100 if iterations > 0 else 0

        return {
            "avg_response_time": avg_response_time,
            "p95_response_time": np.percentile(response_times, 95) if response_times else 0,
            "throughput": throughput,
            "success_rate": success_rate,
            "total_requests": iterations,
            "successful_requests": successful_requests
        }

    async def benchmark_system_resources(self):
        """Benchmark system resource usage"""
        logger.info("💻 Benchmarking System Resources...")

        import psutil

        resource_category = BenchmarkCategory(
            name="System Resources",
            description="System resource consumption metrics"
        )

        # Monitor resources for a period
        monitoring_duration = 30  # seconds
        cpu_usage_samples = []
        memory_usage_samples = []

        start_time = time.time()
        while time.time() - start_time < monitoring_duration:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_usage_samples.append(cpu_percent)

                # Memory usage
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_usage_samples.append(memory_percent)

                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"Resource monitoring error: {e}")

        if cpu_usage_samples:
            avg_cpu = statistics.mean(cpu_usage_samples)
            cpu_metric = BenchmarkMetric(
                name="cpu_usage_avg",
                category="resource_usage",
                value=avg_cpu,
                unit="%",
                baseline_value=self.baseline.get_baseline_metric("system_resources", "cpu_usage"),
                target_value=self.target_metrics["system_resources"]["cpu_usage"]
            )
            resource_category.metrics.append(cpu_metric)

        if memory_usage_samples:
            avg_memory = statistics.mean(memory_usage_samples)
            memory_metric = BenchmarkMetric(
                name="memory_usage_avg",
                category="resource_usage",
                value=avg_memory,
                unit="%",
                baseline_value=self.baseline.get_baseline_metric("system_resources", "memory_usage"),
                target_value=self.target_metrics["system_resources"]["memory_usage"]
            )
            resource_category.metrics.append(memory_metric)

        # Disk I/O benchmark
        try:
            disk_io_start = psutil.disk_io_counters()
            await asyncio.sleep(5)
            disk_io_end = psutil.disk_io_counters()

            if disk_io_start and disk_io_end:
                read_bytes = disk_io_end.read_bytes - disk_io_start.read_bytes
                write_bytes = disk_io_end.write_bytes - disk_io_start.write_bytes
                total_bytes = read_bytes + write_bytes

                disk_io_rate = total_bytes / (1024 * 1024 * 5)  # MB/s over 5 seconds
                disk_io_metric = BenchmarkMetric(
                    name="disk_io_rate",
                    category="resource_usage",
                    value=disk_io_rate,
                    unit="MB/s",
                    baseline_value=self.baseline.get_baseline_metric("system_resources", "disk_io"),
                    target_value=self.target_metrics["system_resources"]["disk_io"]
                )
                resource_category.metrics.append(disk_io_metric)

        except Exception as e:
            logger.warning(f"Disk I/O benchmark failed: {e}")

        self.benchmark_categories.append(resource_category)

        if cpu_usage_samples:
            logger.info(f"✅ System Resources - CPU: {avg_cpu:.1f}%, Memory: {avg_memory:.1f}%, Disk I/O: {disk_io_rate:.1f} MB/s")

    async def benchmark_cache_performance(self):
        """Benchmark cache system performance"""
        logger.info("💾 Benchmarking Cache Performance...")

        cache_category = BenchmarkCategory(
            name="Cache Performance",
            description="Cache system efficiency metrics"
        )

        try:
            # Test cache statistics endpoint
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/v1/cache/stats", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    cache_data = await response.json()
                    cache_response_time = time.time() - start_time

            if cache_data and "hit_rate" in cache_data:
                hit_rate = cache_data["hit_rate"] * 100  # Convert to percentage

                hit_rate_metric = BenchmarkMetric(
                    name="cache_hit_rate",
                    category="cache_performance",
                    value=hit_rate,
                    unit="%",
                    baseline_value=self.baseline.get_baseline_metric("cache_performance", "hit_rate"),
                    target_value=self.target_metrics["cache_performance"]["hit_rate"]
                )
                cache_category.metrics.append(hit_rate_metric)

                cache_response_metric = BenchmarkMetric(
                    name="cache_response_time",
                    category="cache_performance",
                    value=cache_response_time,
                    unit="seconds",
                    baseline_value=self.baseline.get_baseline_metric("cache_performance", "response_time"),
                    target_value=self.target_metrics["cache_performance"]["response_time"]
                )
                cache_category.metrics.append(cache_response_metric)

                logger.info(f"✅ Cache Performance - Hit Rate: {hit_rate:.1f}%, Response Time: {cache_response_time:.3f}s")

        except Exception as e:
            logger.warning(f"Cache performance benchmark failed: {e}")

        self.benchmark_categories.append(cache_category)

    async def benchmark_database_performance(self):
        """Benchmark database performance"""
        logger.info("🗄️ Benchmarking Database Performance...")

        db_category = BenchmarkCategory(
            name="Database Performance",
            description="Database operation performance metrics"
        )

        # Test database-related endpoints
        db_endpoints = [
            {
                "name": "sessions_db",
                "url": "/api/v1/sessions",
                "iterations": 20
            },
            {
                "name": "stats_db",
                "url": "/api/v1/stats",
                "iterations": 20
            }
        ]

        for endpoint_config in db_endpoints:
            try:
                metrics = await self._benchmark_endpoint(endpoint_config)

                response_time_metric = BenchmarkMetric(
                    name=f"{endpoint_config['name']}_response_time",
                    category="response_time",
                    value=metrics["avg_response_time"],
                    unit="seconds",
                    baseline_value=1.0,  # Default baseline for DB operations
                    target_value=0.5   # Target: < 500ms for DB operations
                )
                db_category.metrics.append(response_time_metric)

                throughput_metric = BenchmarkMetric(
                    name=f"{endpoint_config['name']}_throughput",
                    category="throughput",
                    value=metrics["throughput"],
                    unit="req/s",
                    baseline_value=50.0,
                    target_value=100.0
                )
                db_category.metrics.append(throughput_metric)

                logger.info(f"✅ {endpoint_config['name']}: {metrics['avg_response_time']:.3f}s, {metrics['throughput']:.1f} req/s")

            except Exception as e:
                logger.error(f"❌ Failed to benchmark DB endpoint {endpoint_config['name']}: {e}")

        self.benchmark_categories.append(db_category)

    async def benchmark_monitoring_overhead(self):
        """Benchmark monitoring system overhead"""
        logger.info("📊 Benchmarking Monitoring Overhead...")

        monitoring_category = BenchmarkCategory(
            name="Monitoring Overhead",
            description="Monitoring system performance impact"
        )

        try:
            # Test monitoring endpoints response time
            monitoring_endpoints = [
                "/api/v1/monitoring-new/dashboard",
                "/api/v1/performance/stats",
                "/api/v1/performance-optimization/stats"
            ]

            total_response_times = []
            for endpoint in monitoring_endpoints:
                start_time = time.time()
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{self.base_url}{endpoint}", timeout=aiohttp.ClientTimeout(total=5)) as response:
                            await response.text()
                            response_time = time.time() - start_time
                            total_response_times.append(response_time)
                except Exception:
                    total_response_times.append(5.0)  # Timeout penalty

            if total_response_times:
                avg_monitoring_overhead = statistics.mean(total_response_times)
                overhead_metric = BenchmarkMetric(
                    name="monitoring_endpoint_avg_response",
                    category="response_time",
                    value=avg_monitoring_overhead,
                    unit="seconds",
                    baseline_value=0.5,
                    target_value=0.2
                )
                monitoring_category.metrics.append(overhead_metric)

                logger.info(f"✅ Monitoring Overhead - Average: {avg_monitoring_overhead:.3f}s")

        except Exception as e:
            logger.warning(f"Monitoring overhead benchmark failed: {e}")

        self.benchmark_categories.append(monitoring_category)

    def _generate_benchmark_report(self) -> Dict:
        """Generate comprehensive benchmark report"""
        logger.info("📋 Generating Benchmark Report...")

        # Calculate category scores
        for category in self.benchmark_categories:
            category.calculate_category_score()

        # Calculate overall performance score
        if self.benchmark_categories:
            category_scores = [cat.overall_score for cat in self.benchmark_categories if cat.metrics]
            overall_score = statistics.mean(category_scores) if category_scores else 0.0
        else:
            overall_score = 0.0

        # Generate detailed metrics analysis
        detailed_metrics = []
        total_metrics = 0
        improved_metrics = 0
        target_met_metrics = 0

        for category in self.benchmark_categories:
            for metric in category.metrics:
                metric_info = {
                    "name": metric.name,
                    "category": category.name,
                    "current_value": metric.value,
                    "unit": metric.unit,
                    "baseline_value": metric.baseline_value,
                    "target_value": metric.target_value,
                    "improvement_percentage": metric.calculate_improvement(),
                    "meets_target": metric.meets_target()
                }
                detailed_metrics.append(metric_info)

                total_metrics += 1
                if metric.improvement_percentage and metric.improvement_percentage > 0:
                    improved_metrics += 1
                if metric.meets_target():
                    target_met_metrics += 1

        # Generate recommendations
        recommendations = self._generate_benchmark_recommendations(detailed_metrics)

        return {
            "overall_score": overall_score,
            "performance_grade": self._calculate_performance_grade(overall_score),
            "summary": {
                "total_metrics": total_metrics,
                "improved_metrics": improved_metrics,
                "target_met_metrics": target_met_metrics,
                "improvement_rate": (improved_metrics / total_metrics * 100) if total_metrics > 0 else 0,
                "target_achievement_rate": (target_met_metrics / total_metrics * 100) if total_metrics > 0 else 0
            },
            "category_scores": {
                cat.name: {
                    "score": cat.overall_score,
                    "metric_count": len(cat.metrics),
                    "description": cat.description
                }
                for cat in self.benchmark_categories
            },
            "detailed_metrics": detailed_metrics,
            "recommendations": recommendations,
            "baseline_comparison": {
                "improved_categories": [cat.name for cat in self.benchmark_categories if any(m.calculate_improvement() > 0 for m in cat.metrics)],
                "degraded_categories": [cat.name for cat in self.benchmark_categories if any(m.calculate_improvement() < 0 for m in cat.metrics)],
                "stable_categories": [cat.name for cat in self.benchmark_categories if all(m.calculate_improvement() == 0 or m.calculate_improvement() is None for m in cat.metrics)]
            }
        }

    def _calculate_performance_grade(self, score: float) -> str:
        """Calculate performance grade based on score"""
        if score >= 95:
            return "A+ (Excellent)"
        elif score >= 90:
            return "A (Outstanding)"
        elif score >= 85:
            return "B+ (Very Good)"
        elif score >= 80:
            return "B (Good)"
        elif score >= 75:
            return "C+ (Average)"
        elif score >= 70:
            return "C (Fair)"
        elif score >= 60:
            return "D (Poor)"
        else:
            return "F (Critical)"

    def _generate_benchmark_recommendations(self, detailed_metrics: List[Dict]) -> List[str]:
        """Generate recommendations based on benchmark results"""
        recommendations = []

        # Analyze response time issues
        slow_metrics = [m for m in detailed_metrics if "response_time" in m["name"] and not m["meets_target"]]
        if slow_metrics:
            recommendations.append(f"Response time optimization needed for: {', '.join(m['name'] for m in slow_metrics)}")

        # Analyze throughput issues
        low_throughput = [m for m in detailed_metrics if "throughput" in m["name"] and not m["meets_target"]]
        if low_throughput:
            recommendations.append(f"Throughput improvement needed for: {', '.join(m['name'] for m in low_throughput)}")

        # Analyze success rate issues
        low_success_rate = [m for m in detailed_metrics if "success_rate" in m["name"] and not m["meets_target"]]
        if low_success_rate:
            recommendations.append(f"Success rate improvement needed for: {', '.join(m['name'] for m in low_success_rate)}")

        # Analyze resource usage
        high_resource_usage = [m for m in detailed_metrics if ("cpu" in m["name"] or "memory" in m["name"]) and m["current_value"] > (m["target_value"] or 80)]
        if high_resource_usage:
            recommendations.append("High resource usage detected. Consider optimization or scaling.")

        # Analyze cache performance
        cache_issues = [m for m in detailed_metrics if "cache" in m["name"] and not m["meets_target"]]
        if cache_issues:
            recommendations.append("Cache performance below target. Review caching strategies.")

        # Check overall improvement trend
        improved_count = sum(1 for m in detailed_metrics if m.get("improvement_percentage", 0) > 0)
        if improved_count < len(detailed_metrics) * 0.5:
            recommendations.append("Limited performance improvements detected. Review optimization strategies.")

        if not recommendations:
            recommendations.append("Performance looks good across all metrics. Continue monitoring.")

        return recommendations


# Pytest test functions
@pytest.fixture
async def benchmark_suite():
    """Fixture for benchmark suite"""
    return PerformanceBenchmarkSuite()


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_performance_benchmark_suite(benchmark_suite):
    """Test complete performance benchmark suite"""
    report = await benchmark_suite.run_full_benchmark_suite()

    # Verify benchmark suite executed successfully
    assert report["overall_score"] >= 50.0, f"Overall performance score too low: {report['overall_score']}"
    assert len(report["category_scores"]) >= 4, "Insufficient benchmark categories executed"

    # Verify critical metrics
    api_metrics = [m for m in report["detailed_metrics"] if "health" in m["name"]]
    if api_metrics:
        health_response_time = next((m for m in api_metrics if "response_time" in m["name"]), None)
        if health_response_time:
            assert health_response_time["current_value"] <= 1.0, f"Health endpoint too slow: {health_response_time['current_value']}s"

    # Log benchmark results
    logger.info(f"🏁 Performance Benchmark Results:")
    logger.info(f"   Overall Score: {report['overall_score']:.2f}/100")
    logger.info(f"   Performance Grade: {report['performance_grade']}")
    logger.info(f"   Improvement Rate: {report['summary']['improvement_rate']:.1f}%")
    logger.info(f"   Target Achievement Rate: {report['summary']['target_achievement_rate']:.1f}%")


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_critical_benchmarks_only(benchmark_suite):
    """Test only critical benchmarks for faster execution"""
    # Run only the most important benchmarks
    await benchmark_suite.benchmark_api_endpoints()
    await benchmark_suite.benchmark_system_resources()

    # Generate partial report
    report = benchmark_suite._generate_benchmark_report()

    # Basic sanity checks
    assert report["overall_score"] >= 40.0, f"Critical benchmarks score too low: {report['overall_score']}"
    assert len(report["detailed_metrics"]) >= 5, "Insufficient critical metrics collected"

    logger.info(f"⚡ Critical Benchmarks - Score: {report['overall_score']:.2f}/100")


if __name__ == "__main__":
    # Run benchmark suite directly
    async def main():
        print("🏁 Starting Performance Benchmark Suite")
        print("=" * 80)

        benchmark_suite = PerformanceBenchmarkSuite()
        report = await benchmark_suite.run_full_benchmark_suite()

        print("\n📊 PERFORMANCE BENCHMARK REPORT")
        print("=" * 50)
        print(f"Overall Score: {report['overall_score']:.2f}/100")
        print(f"Performance Grade: {report['performance_grade']}")
        print(f"Improvement Rate: {report['summary']['improvement_rate']:.1f}%")
        print(f"Target Achievement Rate: {report['summary']['target_achievement_rate']:.1f}%")

        print("\n📈 CATEGORY SCORES:")
        for category_name, category_data in report['category_scores'].items():
            print(f"  {category_name}: {category_data['score']:.2f}/100 ({category_data['metric_count']} metrics)")

        print("\n🎯 KEY METRICS:")
        critical_metrics = [m for m in report['detailed_metrics']
                          if any(keyword in m['name'].lower()
                                for keyword in ['health', 'response_time', 'throughput'])]
        for metric in critical_metrics[:10]:  # Show top 10
            status = "✅" if metric['meets_target'] else "❌"
            improvement = f" ({metric['improvement_percentage']:+.1f}%)" if metric['improvement_percentage'] else ""
            print(f"  {status} {metric['name']}: {metric['current_value']:.3f} {metric['unit']}{improvement}")

        if report['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for rec in report['recommendations']:
                print(f"  - {rec}")

        print("\n" + "=" * 80)
        print("✅ PERFORMANCE BENCHMARK COMPLETED")

        # Save detailed report
        report_file = f"data/benchmarks/benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path(report_file).parent.mkdir(parents=True, exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"📄 Detailed report saved to: {report_file}")

    asyncio.run(main())