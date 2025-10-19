#!/usr/bin/env python3
"""
监控系统部署和测试脚本
Week 5 Day 3: 系统监控和运维自动化
"""

import asyncio
import json
import time
import requests
from datetime import datetime
from typing import Dict, Any, List

# 配置
API_BASE_URL = "http://localhost:8001/api/v1"
MONITORING_ENDPOINTS = [
    "/monitoring/metrics",
    "/monitoring/alerts",
    "/monitoring/health",
    "/monitoring/logs",
    "/monitoring/summary"
]


class MonitoringSystemTester:
    """监控系统测试器"""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.test_results = []

    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始AI Hub监控系统测试...")
        print("=" * 60)

        # 测试API端点可用性
        await self.test_api_endpoints()

        # 测试监控指标收集
        await self.test_metrics_collection()

        # 测试告警系统
        await self.test_alert_system()

        # 测试健康检查
        await self.test_health_checks()

        # 测试日志系统
        await self.test_logging_system()

        # 测试通知系统
        await self.test_notification_system()

        # 生成测试报告
        self.generate_test_report()

    async def test_api_endpoints(self):
        """测试API端点可用性"""
        print("\n📡 测试监控API端点可用性...")

        endpoints_tested = 0
        endpoints_passed = 0

        for endpoint in MONITORING_ENDPOINTS:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                status = "✅ PASS" if response.status_code < 400 else "❌ FAIL"

                if response.status_code < 400:
                    endpoints_passed += 1

                print(f"  {status} {endpoint} (Status: {response.status_code})")
                self.test_results.append({
                    "test": f"API Endpoint {endpoint}",
                    "status": "PASS" if response.status_code < 400 else "FAIL",
                    "details": f"HTTP {response.status_code}"
                })
                endpoints_tested += 1

            except Exception as e:
                print(f"  ❌ FAIL {endpoint} (Error: {str(e)})")
                self.test_results.append({
                    "test": f"API Endpoint {endpoint}",
                    "status": "FAIL",
                    "details": str(e)
                })
                endpoints_tested += 1

        print(f"\nAPI端点测试结果: {endpoints_passed}/{endpoints_tested} 通过")

    async def test_metrics_collection(self):
        """测试指标收集"""
        print("\n📊 测试监控指标收集...")

        try:
            # 获取系统指标
            response = requests.get(f"{self.base_url}/monitoring/metrics", timeout=10)

            if response.status_code == 200:
                data = response.json()
                metrics_count = len(data.get("data", []))
                print(f"  ✅ 指标收集正常，获取到 {metrics_count} 个指标")
                self.test_results.append({
                    "test": "Metrics Collection",
                    "status": "PASS",
                    "details": f"Collected {metrics_count} metrics"
                })
            else:
                print(f"  ❌ 指标收集失败 (Status: {response.status_code})")
                self.test_results.append({
                    "test": "Metrics Collection",
                    "status": "FAIL",
                    "details": f"HTTP {response.status_code}"
                })

        except Exception as e:
            print(f"  ❌ 指标收集测试失败: {str(e)}")
            self.test_results.append({
                "test": "Metrics Collection",
                "status": "FAIL",
                "details": str(e)
            })

    async def test_alert_system(self):
        """测试告警系统"""
        print("\n🚨 测试告警系统...")

        try:
            # 获取活跃告警
            response = requests.get(f"{self.base_url}/monitoring/alerts", timeout=10)

            if response.status_code == 200:
                data = response.json()
                alerts = data.get("data", [])
                print(f"  ✅ 告警系统正常，当前有 {len(alerts)} 个活跃告警")
                self.test_results.append({
                    "test": "Alert System",
                    "status": "PASS",
                    "details": f"Found {len(alerts)} active alerts"
                })

                # 测试告警规则创建
                test_rule = {
                    "id": "test_cpu_alert",
                    "name": "测试CPU告警",
                    "metric_name": "system_cpu_usage",
                    "condition": "gt",
                    "threshold": 90.0,
                    "severity": "warning",
                    "duration": 60
                }

                rule_response = requests.post(
                    f"{self.base_url}/monitoring/alerts/rules",
                    json=test_rule,
                    timeout=10
                )

                if rule_response.status_code == 200:
                    print("  ✅ 告警规则创建测试通过")
                    self.test_results.append({
                        "test": "Alert Rule Creation",
                        "status": "PASS",
                        "details": "Test alert rule created successfully"
                    })
                else:
                    print(f"  ⚠️ 告警规则创建测试失败 (Status: {rule_response.status_code})")
                    self.test_results.append({
                        "test": "Alert Rule Creation",
                        "status": "FAIL",
                        "details": f"HTTP {rule_response.status_code}"
                    })
            else:
                print(f"  ❌ 告警系统测试失败 (Status: {response.status_code})")
                self.test_results.append({
                    "test": "Alert System",
                    "status": "FAIL",
                    "details": f"HTTP {response.status_code}"
                })

        except Exception as e:
            print(f"  ❌ 告警系统测试失败: {str(e)}")
            self.test_results.append({
                "test": "Alert System",
                "status": "FAIL",
                "details": str(e)
            })

    async def test_health_checks(self):
        """测试健康检查"""
        print("\n💗 测试系统健康检查...")

        try:
            response = requests.get(f"{self.base_url}/monitoring/health", timeout=10)

            if response.status_code == 200:
                data = response.json()
                health_checks = data.get("data", [])

                healthy_count = 0
                total_count = len(health_checks)

                for check in health_checks:
                    if check.get("status") == "healthy":
                        healthy_count += 1

                print(f"  ✅ 健康检查正常，{healthy_count}/{total_count} 组件健康")
                self.test_results.append({
                    "test": "Health Checks",
                    "status": "PASS",
                    "details": f"{healthy_count}/{total_count} components healthy"
                })
            else:
                print(f"  ❌ 健康检查失败 (Status: {response.status_code})")
                self.test_results.append({
                    "test": "Health Checks",
                    "status": "FAIL",
                    "details": f"HTTP {response.status_code}"
                })

        except Exception as e:
            print(f"  ❌ 健康检查测试失败: {str(e)}")
            self.test_results.append({
                "test": "Health Checks",
                "status": "FAIL",
                "details": str(e)
            })

    async def test_logging_system(self):
        """测试日志系统"""
        print("\n📝 测试日志系统...")

        try:
            # 获取日志统计
            response = requests.get(f"{self.base_url}/monitoring/logs/stats", timeout=10)

            if response.status_code == 200:
                stats = response.json()
                total_logs = stats.get("total_logs", 0)
                print(f"  ✅ 日志系统正常，统计到 {total_logs} 条日志")
                self.test_results.append({
                    "test": "Logging System",
                    "status": "PASS",
                    "details": f"Found {total_logs} log entries"
                })
            else:
                print(f"  ❌ 日志系统测试失败 (Status: {response.status_code})")
                self.test_results.append({
                    "test": "Logging System",
                    "status": "FAIL",
                    "details": f"HTTP {response.status_code}"
                })

        except Exception as e:
            print(f"  ❌ 日志系统测试失败: {str(e)}")
            self.test_results.append({
                "test": "Logging System",
                "status": "FAIL",
                "details": str(e)
            })

    async def test_notification_system(self):
        """测试通知系统"""
        print("\n📧 测试通知系统...")

        try:
            # 获取通知统计
            response = requests.get(f"{self.base_url}/monitoring/notifications/stats", timeout=10)

            if response.status_code == 200:
                stats = response.json()
                print(f"  ✅ 通知系统正常")
                self.test_results.append({
                    "test": "Notification System",
                    "status": "PASS",
                    "details": "Notification system operational"
                })
            else:
                print(f"  ❌ 通知系统测试失败 (Status: {response.status_code})")
                self.test_results.append({
                    "test": "Notification System",
                    "status": "FAIL",
                    "details": f"HTTP {response.status_code}"
                })

        except Exception as e:
            print(f"  ❌ 通知系统测试失败: {str(e)}")
            self.test_results.append({
                "test": "Notification System",
                "status": "FAIL",
                "details": str(e)
            })

    def generate_test_report(self):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📋 测试报告")
        print("=" * 60)

        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = total_tests - passed_tests

        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {failed_tests}")
        print(f"成功率: {(passed_tests/total_tests*100):.1f}%")

        if failed_tests > 0:
            print("\n❌ 失败的测试:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['details']}")

        print("\n📊 详细结果:")
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            print(f"  {status_icon} {result['test']}: {result['details']}")

        # 保存报告到文件
        report_file = f"monitoring_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "success_rate": passed_tests/total_tests*100
                },
                "results": self.test_results
            }, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存到: {report_file}")


async def check_system_requirements():
    """检查系统要求"""
    print("🔍 检查系统要求...")

    # 检查端口
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 8001))
    sock.close()

    if result == 0:
        print("✅ 端口 8001 可访问")
    else:
        print("❌ 端口 8001 不可访问，请确保后端服务正在运行")
        return False

    # 检查必需的Python包
    required_packages = ['requests', 'asyncio']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"❌ 缺少必需的包: {', '.join(missing_packages)}")
        return False
    else:
        print("✅ 所有必需的包已安装")

    return True


async def main():
    """主函数"""
    print("🎯 AI Hub 监控系统部署测试工具")
    print("=" * 60)

    # 检查系统要求
    if not await check_system_requirements():
        print("\n❌ 系统要求检查失败，请解决后重试")
        return

    # 等待用户确认
    input("\n按 Enter 键开始测试...")

    # 运行测试
    tester = MonitoringSystemTester()
    await tester.run_all_tests()

    print("\n🎉 测试完成！")


if __name__ == "__main__":
    asyncio.run(main())