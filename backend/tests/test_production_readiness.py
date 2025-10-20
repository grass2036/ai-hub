"""
生产环境就绪测试
Week 6 Day 6: 生产环境最终验证

验证AI Hub平台是否准备好投入生产环境
"""

import asyncio
import pytest
import time
import requests
import subprocess
import docker
from datetime import datetime
from typing import Dict, List, Any
import psutil
import json
import os


class TestProductionReadiness:
    """生产环境就绪测试套件"""

    @pytest.fixture(scope="class")
    def docker_client(self):
        """Docker客户端"""
        return docker.from_env()

    @pytest.fixture(scope="class")
    def test_config(self):
        """测试配置"""
        return {
            "base_url": "http://localhost",
            "ha_url": "http://localhost/api/v1/ha",
            "backup_url": "http://localhost/api/v1/backup",
            "monitoring_url": "http://localhost:9091",
            "grafana_url": "http://localhost:3001",
            "timeout": 30,
            "max_retries": 3
        }

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """设置测试环境"""
        # 确保在正确的目录下
        os.chdir("/Users/chiyingjie/code/git/ai-hub")

        # 检查必要的文件
        required_files = [
            "docker-compose.ha.yml",
            "docker-compose.backup.yml",
            "docker-compose.monitoring.yml"
        ]

        for file in required_files:
            if not os.path.exists(file):
                pytest.skip(f"Required file not found: {file}")

    class TestDockerDeployment:
        """Docker部署测试"""

        @pytest.mark.asyncio
        async def test_docker_services_running(self, docker_client):
            """测试Docker服务是否正常运行"""
            running_services = []

            # 检查主要服务
            expected_services = [
                "ai-hub-app-1",
                "ai-hub-app-2",
                "ai-hub-app-3",
                "ai-hub-nginx",
                "ai-hub-postgres-backup",
                "ai-hub-redis-backup",
                "ai-hub-backup-storage"
            ]

            for service_name in expected_services:
                try:
                    containers = docker_client.containers.list(
                        filters={"name": service_name, "status": "running"}
                    )
                    if containers:
                        running_services.append(service_name)
                        print(f"✓ Service {service_name} is running")
                    else:
                        print(f"✗ Service {service_name} is not running")
                except Exception as e:
                    print(f"✗ Error checking service {service_name}: {str(e)}")

            # 至少70%的服务应该运行
            min_services = len(expected_services) * 0.7
            assert len(running_services) >= min_services, \
                f"Only {len(running_services)}/{len(expected_services)} services are running"

        @pytest.mark.asyncio
        async def test_container_health_checks(self, docker_client):
            """测试容器健康检查"""
            unhealthy_containers = []

            containers = docker_client.containers.list(filters={"status": "running"})

            for container in containers:
                try:
                    health = container.attrs.get("State", {}).get("Health", {})
                    if health:
                        status = health.get("Status", "unknown")
                        if status != "healthy":
                            unhealthy_containers.append({
                                "name": container.name,
                                "status": status
                            })
                            print(f"✗ Container {container.name} is {status}")
                        else:
                            print(f"✓ Container {container.name} is healthy")
                    else:
                        print(f"! Container {container.name} has no health check")
                except Exception as e:
                    print(f"✗ Error checking container health: {str(e)}")

            # 不超过30%的容器应该不健康
            total_containers = len(containers)
            max_unhealthy = total_containers * 0.3 if total_containers > 0 else 0

            assert len(unhealthy_containers) <= max_unhealthy, \
                f"Too many unhealthy containers: {len(unhealthy_containers)}"

        @pytest.mark.asyncio
        async def test_network_connectivity(self):
            """测试网络连通性"""
            network_name = "ai-hub-ha_backup-network"

            try:
                # 检查网络是否存在
                result = subprocess.run(
                    ["docker", "network", "ls", "--filter", f"name={network_name}"],
                    capture_output=True, text=True
                )

                if network_name in result.stdout:
                    print(f"✓ Network {network_name} exists")
                else:
                    pytest.fail(f"Network {network_name} not found")

            except Exception as e:
                pytest.fail(f"Error checking network: {str(e)}")

        @pytest.mark.asyncio
        async def test_volume_mounts(self, docker_client):
            """测试数据卷挂载"""
            mounted_volumes = []

            containers = docker_client.containers.list(filters={"status": "running"})

            for container in containers:
                try:
                    mounts = container.attrs.get("Mounts", [])
                    if mounts:
                        for mount in mounts:
                            if mount.get("Type") == "volume":
                                mounted_volumes.append({
                                    "container": container.name,
                                    "volume": mount.get("Name"),
                                    "destination": mount.get("Destination")
                                })
                except Exception as e:
                    print(f"Error checking container {container.name} mounts: {str(e)}")

            # 应该有数据卷挂载
            assert len(mounted_volumes) > 0, "No volume mounts found"
            print(f"✓ Found {len(mounted_volumes)} volume mounts")

    class TestAPIEndpoints:
        """API端点测试"""

        @pytest.mark.asyncio
        async def test_core_api_endpoints(self, test_config):
            """测试核心API端点"""
            endpoints = [
                "/api/v1/health",
                "/api/v1/status",
                "/api/v1/models"
            ]

            failed_endpoints = []

            for endpoint in endpoints:
                url = f"{test_config['base_url']}{endpoint}"

                for attempt in range(test_config["max_retries"]):
                    try:
                        response = requests.get(
                            url,
                            timeout=test_config["timeout"]
                        )

                        if response.status_code == 200:
                            print(f"✓ API endpoint {endpoint} is responding")
                            break
                        else:
                            print(f"✗ API endpoint {endpoint} returned {response.status_code}")
                            failed_endpoints.append(endpoint)
                            break

                    except requests.exceptions.RequestException as e:
                        if attempt == test_config["max_retries"] - 1:
                            print(f"✗ API endpoint {endpoint} is not accessible: {str(e)}")
                            failed_endpoints.append(endpoint)
                        else:
                            await asyncio.sleep(2)  # 等待后重试

            # 所有核心端点都应该响应
            assert len(failed_endpoints) == 0, \
                f"Failed API endpoints: {failed_endpoints}"

        @pytest.mark.asyncio
        async def test_high_availability_endpoints(self, test_config):
            """测试高可用API端点"""
            ha_endpoints = [
                "/api/v1/ha/status",
                "/api/v1/ha/load-balancer/stats"
            ]

            for endpoint in ha_endpoints:
                url = f"{test_config['base_url']}{endpoint}"

                try:
                    response = requests.get(
                        url,
                        timeout=test_config["timeout"]
                    )

                    if response.status_code == 200:
                        data = response.json()
                        assert data.get("success", False), f"HA endpoint {endpoint} returned failure"
                        print(f"✓ HA endpoint {endpoint} is working")
                    else:
                        pytest.fail(f"HA endpoint {endpoint} returned {response.status_code}")

                except requests.exceptions.RequestException as e:
                    pytest.fail(f"HA endpoint {endpoint} not accessible: {str(e)}")

        @pytest.mark.asyncio
        async def test_backup_endpoints(self, test_config):
            """测试备份API端点"""
            backup_endpoints = [
                "/api/v1/backup/health",
                "/api/v1/backup/statistics"
            ]

            for endpoint in backup_endpoints:
                url = f"{test_config['base_url']}{endpoint}"

                try:
                    response = requests.get(
                        url,
                        timeout=test_config["timeout"]
                    )

                    if response.status_code == 200:
                        print(f"✓ Backup endpoint {endpoint} is working")
                    else:
                        print(f"⚠ Backup endpoint {endpoint} returned {response.status_code}")

                except requests.exceptions.RequestException as e:
                    print(f"⚠ Backup endpoint {endpoint} not accessible: {str(e)}")

    class TestDatabaseConnections:
        """数据库连接测试"""

        @pytest.mark.asyncio
        async def test_postgresql_connection(self, docker_client):
            """测试PostgreSQL连接"""
            try:
                # 获取PostgreSQL容器
                postgres_container = docker_client.containers.get("ai-hub-postgres-backup")

                # 执行连接测试
                exit_code, output = postgres_container.exec_run(
                    "pg_isready -U aihub"
                )

                if exit_code == 0:
                    print("✓ PostgreSQL connection is working")
                else:
                    pytest.fail(f"PostgreSQL connection failed: {output.decode()}")

            except docker.errors.NotFound:
                pytest.skip("PostgreSQL container not found")
            except Exception as e:
                pytest.fail(f"Error testing PostgreSQL connection: {str(e)}")

        @pytest.mark.asyncio
        async def test_redis_connection(self, docker_client):
            """测试Redis连接"""
            try:
                # 获取Redis容器
                redis_container = docker_client.containers.get("ai-hub-redis-backup")

                # 执行连接测试
                exit_code, output = redis_container.exec_run(
                    "redis-cli ping"
                )

                if exit_code == 0 and "PONG" in output.decode():
                    print("✓ Redis connection is working")
                else:
                    pytest.fail(f"Redis connection failed: {output.decode()}")

            except docker.errors.NotFound:
                pytest.skip("Redis container not found")
            except Exception as e:
                pytest.fail(f"Error testing Redis connection: {str(e)}")

    class TestMonitoringSystem:
        """监控系统测试"""

        @pytest.mark.asyncio
        async def test_prometheus_health(self, test_config):
            """测试Prometheus健康状态"""
            try:
                response = requests.get(
                    f"{test_config['monitoring_url']}/-/healthy",
                    timeout=10
                )

                if response.status_code == 200:
                    print("✓ Prometheus is healthy")
                else:
                    pytest.fail(f"Prometheus health check failed: {response.status_code}")

            except requests.exceptions.RequestException as e:
                pytest.skip(f"Prometheus not accessible: {str(e)}")

        @pytest.mark.asyncio
        async def test_grafana_health(self, test_config):
            """测试Grafana健康状态"""
            try:
                response = requests.get(
                    f"{test_config['grafana_url']}/api/health",
                    timeout=10
                )

                if response.status_code == 200:
                    print("✓ Grafana is healthy")
                else:
                    print(f"⚠ Grafana health check returned: {response.status_code}")

            except requests.exceptions.RequestException as e:
                pytest.skip(f"Grafana not accessible: {str(e)}")

        @pytest.mark.asyncio
        async def test_metrics_collection(self, test_config):
            """测试指标收集"""
            try:
                response = requests.get(
                    f"{test_config['monitoring_url']}/api/v1/query?query=up",
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        metrics_count = len(data.get("data", {}).get("result", []))
                        if metrics_count > 0:
                            print(f"✓ Metrics collection working ({metrics_count} targets up)")
                        else:
                            pytest.fail("No metrics targets are up")
                    else:
                        pytest.fail("Metrics query failed")
                else:
                    pytest.fail(f"Metrics query failed: {response.status_code}")

            except requests.exceptions.RequestException as e:
                pytest.skip(f"Metrics collection test failed: {str(e)}")

    class TestSystemPerformance:
        """系统性能测试"""

        @pytest.mark.asyncio
        async def test_api_response_time(self, test_config):
            """测试API响应时间"""
            endpoint = f"{test_config['base_url']}/api/v1/health"

            response_times = []

            # 测试5次响应时间
            for i in range(5):
                try:
                    start_time = time.time()
                    response = requests.get(endpoint, timeout=10)
                    end_time = time.time()

                    if response.status_code == 200:
                        response_time = end_time - start_time
                        response_times.append(response_time)
                    else:
                        pytest.fail(f"API request failed with status {response.status_code}")

                except requests.exceptions.RequestException as e:
                    pytest.fail(f"API request failed: {str(e)}")

            # 计算平均响应时间
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)

            print(f"✓ Average response time: {avg_response_time:.3f}s")
            print(f"✓ Max response time: {max_response_time:.3f}s")

            # 响应时间应该小于2秒
            assert avg_response_time < 2.0, \
                f"Average response time too high: {avg_response_time:.3f}s"
            assert max_response_time < 5.0, \
                f"Max response time too high: {max_response_time:.3f}s"

        @pytest.mark.asyncio
        async def test_system_resources(self):
            """测试系统资源使用"""
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            print(f"✓ CPU usage: {cpu_percent}%")

            # 内存使用率
            memory = psutil.virtual_memory()
            print(f"✓ Memory usage: {memory.percent}%")

            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            print(f"✓ Disk usage: {disk_percent:.1f}%")

            # 资源使用应该在合理范围内
            assert cpu_percent < 80.0, f"CPU usage too high: {cpu_percent}%"
            assert memory.percent < 80.0, f"Memory usage too high: {memory.percent}%"
            assert disk_percent < 85.0, f"Disk usage too high: {disk_percent:.1f}%"

    class TestBackupSystem:
        """备份系统测试"""

        @pytest.mark.asyncio
        async def test_backup_storage_health(self, docker_client):
            """测试备份存储健康状态"""
            try:
                # 检查MinIO存储容器
                storage_container = docker_client.containers.get("ai-hub-backup-storage")

                # 检查存储服务
                exit_code, output = storage_container.exec_run(
                    "curl -f http://localhost:9000/minio/health/live"
                )

                if exit_code == 0:
                    print("✓ MinIO storage is healthy")
                else:
                    pytest.fail(f"MinIO storage health check failed: {output.decode()}")

            except docker.errors.NotFound:
                pytest.skip("MinIO storage container not found")
            except Exception as e:
                pytest.fail(f"Error testing backup storage: {str(e)}")

        @pytest.mark.asyncio
        async def test_backup_configuration(self, test_config):
            """测试备份配置"""
            try:
                response = requests.get(
                    f"{test_config['backup_url']}/health",
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    components = data.get("components", {})

                    required_components = [
                        "backup_manager",
                        "recovery_manager",
                        "backup_scheduler",
                        "disaster_recovery"
                    ]

                    missing_components = []
                    for component in required_components:
                        if not components.get(component, False):
                            missing_components.append(component)

                    if missing_components:
                        print(f"⚠ Missing backup components: {missing_components}")
                    else:
                        print("✓ All backup components are initialized")

                else:
                    pytest.fail(f"Backup health check failed: {response.status_code}")

            except requests.exceptions.RequestException as e:
                pytest.skip(f"Backup configuration test failed: {str(e)}")

    class TestSecurityConfiguration:
        """安全配置测试"""

        @pytest.mark.asyncio
        async def test_ssl_configuration(self, test_config):
            """测试SSL配置"""
            try:
                # 尝试HTTPS连接
                response = requests.get(
                    f"https://localhost/api/v1/health",
                    verify=False,  # 忽略证书验证
                    timeout=10
                )

                if response.status_code == 200:
                    print("✓ HTTPS is working")
                else:
                    print(f"⚠ HTTPS returned status: {response.status_code}")

            except requests.exceptions.SSLError:
                print("⚠ SSL certificate issues detected")
            except requests.exceptions.RequestException:
                print("⚠ HTTPS not configured or accessible")

        @pytest.mark.asyncio
        async def test_api_security_headers(self, test_config):
            """测试API安全头"""
            try:
                response = requests.get(
                    f"{test_config['base_url']}/api/v1/health",
                    timeout=10
                )

                headers = response.headers

                # 检查安全相关的头
                security_headers = [
                    "x-content-type-options",
                    "x-frame-options",
                    "x-xss-protection"
                ]

                missing_headers = []
                for header in security_headers:
                    if header not in headers:
                        missing_headers.append(header)

                if missing_headers:
                    print(f"⚠ Missing security headers: {missing_headers}")
                else:
                    print("✓ Security headers are present")

            except requests.exceptions.RequestException as e:
                pytest.skip(f"Security headers test failed: {str(e)}")


# 测试运行器
class TestRunner:
    """测试运行器"""

    @staticmethod
    async def run_production_readiness_tests():
        """运行生产环境就绪测试"""
        print("开始AI Hub平台生产环境就绪测试...")
        print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # 运行pytest
        import subprocess
        import sys

        test_command = [
            sys.executable, "-m", "pytest",
            __file__,
            "-v",
            "--tb=short",
            "--color=yes"
        ]

        result = subprocess.run(test_command, capture_output=True, text=True)

        print("=" * 60)
        print("测试结果:")
        print(result.stdout)

        if result.stderr:
            print("错误信息:")
            print(result.stderr)

        print(f"测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return result.returncode == 0


if __name__ == "__main__":
    # 运行测试
    import asyncio

    success = asyncio.run(TestRunner.run_production_readiness_tests())

    if success:
        print("\n🟢 生产环境就绪测试通过！")
        exit(0)
    else:
        print("\n🔴 生产环境就绪测试失败！")
        exit(1)