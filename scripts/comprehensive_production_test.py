#!/usr/bin/env python3
"""
综合生产环境测试脚本
Week 6 Day 6: 生产环境最终验证

执行完整的AI Hub平台生产环境测试
"""

import asyncio
import subprocess
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path


class ComprehensiveProductionTest:
    """综合生产环境测试"""

    def __init__(self):
        self.results = {
            "start_time": datetime.now().isoformat(),
            "test_suites": {},
            "summary": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "skipped_tests": 0
            }
        }
        self.project_root = Path(__file__).parent.parent
        os.chdir(self.project_root)

    def run_test_suite(self, suite_name, test_command, description):
        """运行测试套件"""
        print(f"\n{'='*60}")
        print(f"运行测试套件: {suite_name}")
        print(f"描述: {description}")
        print(f"开始时间: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")

        try:
            result = subprocess.run(
                test_command,
                capture_output=True,
                text=True,
                timeout=1800  # 30分钟超时
            )

            # 解析pytest输出
            passed = result.stdout.count("PASSED")
            failed = result.stdout.count("FAILED")
            errors = result.stdout.count("ERROR")
            skipped = result.stdout.count("SKIPPED")

            # 计算总测试数
            total = passed + failed + errors

            suite_result = {
                "command": " ".join(test_command),
                "description": description,
                "total_tests": total,
                "passed_tests": passed,
                "failed_tests": failed,
                "error_tests": errors,
                "skipped_tests": skipped,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": None
            }

            self.results["test_suites"][suite_name] = suite_result

            # 更新汇总统计
            self.results["summary"]["total_tests"] += total
            self.results["summary"]["passed_tests"] += passed
            self.results["summary"]["failed_tests"] += (failed + errors)
            self.results["summary"]["skipped_tests"] += skipped

            # 打印结果
            print(f"✓ 测试套件完成: {suite_name}")
            print(f"  总测试数: {total}")
            print(f"  通过: {passed}")
            print(f"  失败: {failed + errors}")
            print(f"  跳过: {skipped}")

            if result.returncode == 0:
                print(f"  状态: 🟢 通过")
            else:
                print(f"  状态: 🔴 失败")
                if result.stderr:
                    print(f"  错误: {result.stderr[:200]}...")

        except subprocess.TimeoutExpired:
            print(f"  状态: ⏰ 超时")
            suite_result = {
                "command": " ".join(test_command),
                "description": description,
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 1,
                "error_tests": 0,
                "skipped_tests": 0,
                "return_code": 124,
                "stdout": "",
                "stderr": "Test suite timed out after 30 minutes",
                "duration": None
            }
            self.results["test_suites"][suite_name] = suite_result
            self.results["summary"]["failed_tests"] += 1

        except Exception as e:
            print(f"  状态: ❌ 异常: {str(e)}")
            suite_result = {
                "command": " ".join(test_command),
                "description": description,
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 1,
                "error_tests": 0,
                "skipped_tests": 0,
                "return_code": 1,
                "stdout": "",
                "stderr": str(e),
                "duration": None
            }
            self.results["test_suites"][suite_name] = suite_result
            self.results["summary"]["failed_tests"] += 1

    def run_unit_tests(self):
        """运行单元测试"""
        test_command = [
            sys.executable, "-m", "pytest",
            "backend/tests/test_backup_system.py",
            "backend/tests/test_ha_system.py",
            "backend/tests/test_system_integration.py",
            "-v",
            "--tb=short"
        ]

        self.run_test_suite(
            "unit_tests",
            test_command,
            "单元测试 - 验证核心组件功能"
        )

    def run_integration_tests(self):
        """运行集成测试"""
        test_command = [
            sys.executable, "-m", "pytest",
            "backend/tests/integration/",
            "-v",
            "--tb=short"
        ]

        self.run_test_suite(
            "integration_tests",
            test_command,
            "集成测试 - 验证系统组件集成"
        )

    def run_production_readiness_tests(self):
        """运行生产环境就绪测试"""
        test_command = [
            sys.executable, "backend/tests/test_production_readiness.py"
        ]

        self.run_test_suite(
            "production_readiness",
            test_command,
            "生产环境就绪测试 - 验证生产环境配置"
        )

    def run_api_tests(self):
        """运行API测试"""
        test_command = [
            sys.executable, "-m", "pytest",
            "backend/tests/test_api_integration.py",
            "-v",
            "--tb=short"
        ]

        self.run_test_suite(
            "api_tests",
            test_command,
            "API测试 - 验证API端点功能"
        )

    def run_security_tests(self):
        """运行安全测试"""
        test_command = [
            sys.executable, "-m", "pytest",
            "backend/tests/test_permission_system.py",
            "-v",
            "--tb=short"
        ]

        self.run_test_suite(
            "security_tests",
            test_command,
            "安全测试 - 验证权限和安全配置"
        )

    def run_performance_tests(self):
        """运行性能测试"""
        # 检查性能测试依赖
        try:
            import locust
            performance_available = True
        except ImportError:
            performance_available = False
            print("⚠ Locust not installed, skipping performance tests")

        if performance_available:
            test_command = [
                sys.executable, "backend/tests/performance/load_tests.py",
                "--quick"  # 快速模式
            ]

            self.run_test_suite(
                "performance_tests",
                test_command,
                "性能测试 - 验证系统性能指标"
            )
        else:
            # 添加占位符结果
            self.results["test_suites"]["performance_tests"] = {
                "command": "",
                "description": "性能测试 - 验证系统性能指标",
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "error_tests": 0,
                "skipped_tests": 1,
                "return_code": 0,
                "stdout": "Skipped: Locust not installed",
                "stderr": "",
                "duration": None
            }
            self.results["summary"]["skipped_tests"] += 1

    def run_docker_validation(self):
        """运行Docker验证"""
        print(f"\n{'='*60}")
        print("运行Docker环境验证")
        print("描述: 验证Docker容器和服务状态")
        print(f"{'='*60}")

        try:
            # 运行Docker验证脚本
            result = subprocess.run(
                ["./scripts/production_validation.sh"],
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )

            if result.returncode == 0:
                print("✓ Docker验证通过")
                status = "🟢 通过"
            elif result.returncode == 1:
                print("⚠ Docker验证有警告")
                status = "🟡 警告"
            else:
                print("✗ Docker验证失败")
                status = "🔴 失败"

            # 解析Docker验证结果
            docker_result = {
                "command": "./scripts/production_validation.sh",
                "description": "Docker环境验证",
                "total_tests": 0,
                "passed_tests": 0 if result.returncode != 0 else 1,
                "failed_tests": 1 if result.returncode != 0 else 0,
                "error_tests": 0,
                "skipped_tests": 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": None,
                "status": status
            }

            self.results["test_suites"]["docker_validation"] = docker_result

            if result.returncode == 0:
                self.results["summary"]["passed_tests"] += 1
            else:
                self.results["summary"]["failed_tests"] += 1

            print(f"Docker验证输出:")
            print(result.stdout[-500:])  # 显示最后500个字符

        except subprocess.TimeoutExpired:
            print("✗ Docker验证超时")
            self.results["summary"]["failed_tests"] += 1

        except Exception as e:
            print(f"✗ Docker验证异常: {str(e)}")
            self.results["summary"]["failed_tests"] += 1

    def generate_test_report(self):
        """生成测试报告"""
        self.results["end_time"] = datetime.now().isoformat()

        # 计算通过率
        total = self.results["summary"]["total_tests"]
        passed = self.results["summary"]["passed_tests"]
        pass_rate = (passed / total * 100) if total > 0 else 0

        self.results["summary"]["pass_rate"] = round(pass_rate, 2)

        # 生成详细报告
        report = {
            "ai_hub_production_test_report": {
                "metadata": {
                    "test_execution": {
                        "start_time": self.results["start_time"],
                        "end_time": self.results["end_time"],
                        "total_duration": "Calculated",
                        "environment": "Production",
                        "version": "1.0.0"
                    },
                    "summary": self.results["summary"],
                    "test_suites": {}
                }
            }
        }

        # 添加测试套件结果
        for suite_name, suite_result in self.results["test_suites"].items():
            suite_data = {
                "name": suite_name,
                "description": suite_result["description"],
                "command": suite_result["command"],
                "results": {
                    "total": suite_result["total_tests"],
                    "passed": suite_result["passed_tests"],
                    "failed": suite_result["failed_tests"],
                    "errors": suite_result.get("error_tests", 0),
                    "skipped": suite_result["skipped_tests"],
                    "return_code": suite_result["return_code"]
                },
                "status": "PASSED" if suite_result["return_code"] == 0 else "FAILED"
            }

            if suite_result.get("status"):
                suite_data["status_detailed"] = suite_result["status"]

            report["ai_hub_production_test_report"]["metadata"]["test_execution"]["test_suites"][suite_name] = suite_data

        return report

    def save_report(self, report):
        """保存测试报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"production_test_report_{timestamp}.json"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            print(f"\n📊 详细测试报告已保存到: {report_file}")
            return report_file

        except Exception as e:
            print(f"❌ 保存测试报告失败: {str(e)}")
            return None

    def print_summary(self, report):
        """打印测试摘要"""
        print(f"\n{'='*80}")
        print("AI Hub平台生产环境测试报告")
        print(f"{'='*80}")

        summary = report["ai_hub_production_test_report"]["metadata"]["summary"]
        metadata = report["ai_hub_production_test_report"]["metadata"]["test_execution"]

        print(f"测试开始时间: {metadata['start_time']}")
        print(f"测试结束时间: {metadata['end_time']}")
        print(f"测试环境: {metadata['environment']}")
        print("")

        print("📊 测试统计:")
        print(f"  总测试数: {summary['total_tests']}")
        print(f"  通过测试: {summary['passed_tests']}")
        print(f"  失败测试: {summary['failed_tests']}")
        print(f"  跳过测试: {summary.get('skipped_tests', 0)}")
        print(f"  通过率: {summary['pass_rate']}%")
        print("")

        # 按状态分类显示测试套件
        passed_suites = []
        failed_suites = []
        skipped_suites = []

        for suite_name, suite_data in metadata["test_suites"].items():
            if suite_data["status"] == "PASSED":
                passed_suites.append(suite_name)
            elif suite_data["status"] == "FAILED":
                failed_suites.append(suite_name)
            else:
                skipped_suites.append(suite_name)

        if passed_suites:
            print("🟢 通过的测试套件:")
            for suite in passed_suites:
                print(f"  ✓ {suite}")

        if failed_suites:
            print("🔴 失败的测试套件:")
            for suite in failed_suites:
                print(f"  ✗ {suite}")

        if skipped_suites:
            print("⚠ 跳过的测试套件:")
            for suite in skipped_suites:
                print(f"  - {suite}")

        print("")
        print("📋 结论:")

        pass_rate = summary["pass_rate"]
        if pass_rate >= 95:
            print("🟢 生产环境测试通过，系统可以安全上线")
        elif pass_rate >= 80:
            print("🟡 生产环境基本就绪，建议修复关键问题后上线")
        elif pass_rate >= 60:
            print("🟠 生产环境需要重大改进，不建议上线")
        else:
            print("🔴 生产环境存在严重问题，绝对不能上线")

        print(f"{'='*80}")

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始AI Hub平台综合生产环境测试")
        print(f"开始时间: {self.results['start_time']}")
        print(f"项目目录: {self.project_root}")
        print("")

        # 检查必要文件
        required_files = [
            "docker-compose.ha.yml",
            "scripts/production_validation.sh"
        ]

        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)

        if missing_files:
            print(f"❌ 缺少必要文件: {missing_files}")
            return False

        try:
            # 1. Docker环境验证
            self.run_docker_validation()

            # 2. 生产环境就绪测试
            self.run_production_readiness_tests()

            # 3. 单元测试
            self.run_unit_tests()

            # 4. 集成测试
            self.run_integration_tests()

            # 5. API测试
            self.run_api_tests()

            # 6. 安全测试
            self.run_security_tests()

            # 7. 性能测试
            self.run_performance_tests()

            # 生成并保存报告
            report = self.generate_test_report()
            report_file = self.save_report(report)

            # 打印摘要
            self.print_summary(report)

            # 返回是否通过
            pass_rate = self.results["summary"]["pass_rate"]
            return pass_rate >= 90

        except KeyboardInterrupt:
            print("\n⏹ 测试被用户中断")
            return False
        except Exception as e:
            print(f"\n❌ 测试执行异常: {str(e)}")
            return False


def main():
    """主函数"""
    tester = ComprehensiveProductionTest()

    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 测试运行失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()