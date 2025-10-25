#!/usr/bin/env python3
"""
Week 7 综合功能测试脚本
Week 7 Comprehensive Feature Testing Script

测试Week 7开发的所有功能：
1. 多模态AI功能
2. 用户体验优化
3. 多平台支持
4. 生态系统建设
5. 商业化功能
6. 国际化支持

Usage:
    python scripts/test_week7_comprehensive.py [--verbose] [--component COMPONENT]
"""

import asyncio
import json
import sys
import time
import argparse
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

@dataclass
class TestResult:
    """测试结果"""
    component: str
    test_name: str
    status: str  # PASS, FAIL, SKIP, ERROR
    duration: float
    message: str
    details: Dict[str, Any] = None

class Week7TestSuite:
    """Week 7 测试套件"""

    def __init__(self):
        self.results: List[TestResult] = []
        self.verbose = False

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始Week 7综合功能测试")
        print("=" * 50)

        # 1. 多模态AI功能测试
        self.test_multimodal_ai()

        # 2. 用户体验优化测试
        self.test_ux_optimizations()

        # 3. 多平台支持测试
        self.test_multiplatform_support()

        # 4. 生态系统建设测试
        self.test_ecosystem_features()

        # 5. 商业化功能测试
        self.test_business_features()

        # 6. 国际化支持测试
        self.test_internationalization()

        # 生成测试报告
        self.generate_report()

    def test_multimodal_ai(self):
        """测试多模态AI功能"""
        print("\n🧪 测试多模态AI功能")
        print("-" * 30)

        # 测试图像识别接口
        self.test_image_processing()

        # 测试语音处理功能
        self.test_voice_processing()

        # 测试智能工作流引擎
        self.test_workflow_engine()

    def test_image_processing(self):
        """测试图像处理功能"""
        start_time = time.time()

        try:
            # 检查相关文件是否存在
            image_service_file = Path("backend/core/multimodal/image_processor.py")
            if not image_service_file.exists():
                self.add_result("multimodal_ai", "image_processing", "SKIP",
                                time.time() - start_time,
                                "图像处理服务文件不存在")
                return

            # 检查图像处理服务的导入
            try:
                from backend.core.multimodal.image_processor import ImageProcessor
                processor = ImageProcessor()

                # 测试基本配置
                if hasattr(processor, 'process_image'):
                    status = "PASS"
                    message = "图像处理服务导入成功"
                else:
                    status = "FAIL"
                    message = "图像处理服务缺少必要方法"

            except ImportError as e:
                status = "FAIL"
                message = f"无法导入图像处理服务: {str(e)}"

            duration = time.time() - start_time
            self.add_result("multimodal_ai", "image_processing", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("multimodal_ai", "image_processing", "ERROR", duration, f"测试出错: {str(e)}")

    def test_voice_processing(self):
        """测试语音处理功能"""
        start_time = time.time()

        try:
            # 检查语音处理相关文件
            voice_service_file = Path("backend/core/multimodal/voice_processor.py")
            if not voice_service_file.exists():
                self.add_result("multimodal_ai", "voice_processing", "SKIP",
                                time.time() - start_time,
                                "语音处理服务文件不存在")
                return

            # 检查语音处理服务的导入
            try:
                from backend.core.multimodal.voice_processor import VoiceProcessor
                processor = VoiceProcessor()

                # 测试基本配置
                if hasattr(processor, 'speech_to_text') and hasattr(processor, 'text_to_speech'):
                    status = "PASS"
                    message = "语音处理服务导入成功"
                else:
                    status = "FAIL"
                    message = "语音处理服务缺少必要方法"

            except ImportError as e:
                status = "FAIL"
                message = f"无法导入语音处理服务: {str(e)}"

            duration = time.time() - start_time
            self.add_result("multimodal_ai", "voice_processing", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("multimodal_ai", "voice_processing", "ERROR", duration, f"测试出错: {str(e)}")

    def test_workflow_engine(self):
        """测试智能工作流引擎"""
        start_time = time.time()

        try:
            # 检查工作流引擎文件
            workflow_file = Path("backend/core/workflow_engine.py")
            if not workflow_file.exists():
                self.add_result("multimodal_ai", "workflow_engine", "SKIP",
                                time.time() - start_time,
                                "工作流引擎文件不存在")
                return

            # 检查工作流引擎的导入
            try:
                from backend.core.workflow_engine import WorkflowEngine
                engine = WorkflowEngine()

                # 测试基本功能
                if hasattr(engine, 'create_workflow') and hasattr(engine, 'execute_workflow'):
                    status = "PASS"
                    message = "工作流引擎导入成功"
                else:
                    status = "FAIL"
                    message = "工作流引擎缺少必要方法"

            except ImportError as e:
                status = "FAIL"
                message = f"无法导入工作流引擎: {str(e)}"

            duration = time.time() - start_time
            self.add_result("multimodal_ai", "workflow_engine", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("multimodal_ai", "workflow_engine", "ERROR", duration, f"测试出错: {str(e)}")

    def test_ux_optimizations(self):
        """测试用户体验优化"""
        print("\n🎨 测试用户体验优化")
        print("-" * 30)

        # 测试响应式设计
        self.test_responsive_design()

        # 测试动画和交互
        self.test_animations()

        # 测试个性化系统
        self.test_personalization()

    def test_responsive_design(self):
        """测试响应式设计"""
        start_time = time.time()

        try:
            # 检查前端的响应式设计文件
            css_files = [
                "frontend/src/styles/responsive.css",
                "frontend/src/styles/mobile.css",
                "frontend/tailwind.config.js"
            ]

            responsive_files_exist = 0
            for css_file in css_files:
                if Path(css_file).exists():
                    responsive_files_exist += 1

            if responsive_files_exist >= 2:
                status = "PASS"
                message = f"响应式设计文件存在 ({responsive_files_exist}/{len(css_files)})"
            else:
                status = "FAIL"
                message = f"响应式设计文件不足 ({responsive_files_exist}/{len(css_files)})"

            duration = time.time() - start_time
            self.add_result("ux_optimizations", "responsive_design", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("ux_optimizations", "responsive_design", "ERROR", duration, f"测试出错: {str(e)}")

    def test_animations(self):
        """测试动画和交互效果"""
        start_time = time.time()

        try:
            # 检查动画相关文件
            animation_files = [
                "frontend/src/components/ui/LoadingSpinner.tsx",
                "frontend/src/styles/animations.css"
            ]

            animation_files_exist = 0
            for anim_file in animation_files:
                if Path(anim_file).exists():
                    animation_files_exist += 1

            if animation_files_exist > 0:
                status = "PASS"
                message = f"动画组件存在 ({animation_files_exist}/{len(animation_files)})"
            else:
                status = "FAIL"
                message = "动画组件缺失"

            duration = time.time() - start_time
            self.add_result("ux_optimizations", "animations", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("ux_optimizations", "animations", "ERROR", duration, f"测试出错: {str(e)}")

    def test_personalization(self):
        """测试个性化系统"""
        start_time = time.time()

        try:
            # 检查主题上下文
            theme_context = Path("frontend/src/contexts/ThemeContext.tsx")
            if theme_context.exists():
                status = "PASS"
                message = "主题个性化系统存在"
            else:
                status = "FAIL"
                message = "主题个性化系统缺失"

            duration = time.time() - start_time
            self.add_result("ux_optimizations", "personalization", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("ux_optimizations", "personalization", "ERROR", duration, f"测试出错: {str(e)}")

    def test_multiplatform_support(self):
        """测试多平台支持"""
        print("\n📱 测试多平台支持")
        print("-" * 30)

        # 测试移动端支持
        self.test_mobile_support()

        # 测试桌面端支持
        self.test_desktop_support()

        # 测试SDK支持
        self.test_sdk_support()

    def test_mobile_support(self):
        """测试移动端支持"""
        start_time = time.time()

        try:
            # 检查移动端相关文件
            mobile_files = [
                "frontend/src/components/ui/MobileNavigation.tsx",
                "frontend/tailwind.config.js"  # Tailwind支持响应式
            ]

            mobile_files_exist = 0
            for mobile_file in mobile_files:
                if Path(mobile_file).exists():
                    mobile_files_exist += 1

            if mobile_files_exist >= 1:
                status = "PASS"
                message = f"移动端组件存在 ({mobile_files_exist}/{len(mobile_files)})"
            else:
                status = "FAIL"
                message = "移动端组件缺失"

            duration = time.time() - start_time
            self.add_result("multiplatform", "mobile_support", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("multiplatform", "mobile_support", "ERROR", duration, f"测试出错: {str(e)}")

    def test_desktop_support(self):
        """测试桌面端支持"""
        start_time = time.time()

        try:
            # 检查Electron相关文件
            electron_files = [
                "frontend/electron.js",
                "frontend/package.json"
            ]

            electron_files_exist = 0
            for electron_file in electron_files:
                if Path(electron_file).exists():
                    electron_files_exist += 1

            if electron_files_exist >= 1:
                status = "PASS"
                message = f"桌面端应用文件存在 ({electron_files_exist}/{len(electron_files)})"
            else:
                status = "SKIP"
                message = "桌面端应用文件缺失"

            duration = time.time() - start_time
            self.add_result("multiplatform", "desktop_support", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("multiplatform", "desktop_support", "ERROR", duration, f"测试出错: {str(e)}")

    def test_sdk_support(self):
        """测试SDK支持"""
        start_time = time.time()

        try:
            # 检查SDK相关文件
            sdk_files = [
                "scripts/templates/backend/package.json",
                "scripts/templates/python-sdk/package.json"
            ]

            sdk_files_exist = 0
            for sdk_file in sdk_files:
                if Path(sdk_file).exists():
                    sdk_files_exist += 1

            if sdk_files_exist > 0:
                status = "PASS"
                message = f"SDK模板存在 ({sdk_files_exist}/{len(sdk_files)})"
            else:
                status = "FAIL"
                message = "SDK模板缺失"

            duration = time.time() - start_time
            self.add_result("multiplatform", "sdk_support", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("multiplatform", "sdk_support", "ERROR", duration, f"测试出错: {str(e)}")

    def test_ecosystem_features(self):
        """测试生态系统建设"""
        print("\n🌐 测试生态系统建设")
        print("-" * 30)

        # 测试插件系统
        self.test_plugin_system()

        # 测试开发者工具
        self.test_developer_tools()

        # 测试CLI工具
        self.test_cli_tools()

    def test_plugin_system(self):
        """测试插件系统"""
        start_time = time.time()

        try:
            # 检查插件相关文件
            plugin_files = [
                "backend/core/plugin_manager.py",
                "frontend/src/components/PluginMarketplace.tsx"
            ]

            plugin_files_exist = 0
            for plugin_file in plugin_files:
                if Path(plugin_file).exists():
                    plugin_files_exist += 1

            if plugin_files_exist >= 1:
                status = "PASS"
                message = f"插件系统文件存在 ({plugin_files_exist}/{len(plugin_files)})"
            else:
                status = "FAIL"
                message = "插件系统文件缺失"

            duration = time.time() - start_time
            self.add_result("ecosystem", "plugin_system", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("ecosystem", "plugin_system", "ERROR", duration, f"测试出错: {str(e)}")

    def test_developer_tools(self):
        """测试开发者工具"""
        start_time = time.time()

        try:
            # 检查开发者门户
            dev_portal = Path("frontend/src/app/developer-portal/page.tsx")
            if dev_portal.exists():
                status = "PASS"
                message = "开发者门户页面存在"
            else:
                status = "FAIL"
                message = "开发者门户页面缺失"

            duration = time.time() - start_time
            self.add_result("ecosystem", "developer_tools", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("ecosystem", "developer_tools", "ERROR", duration, f"测试出错: {str(e)}")

    def test_cli_tools(self):
        """测试CLI工具"""
        start_time = time.time()

        try:
            # 检查CLI相关文件
            cli_files = [
                "scripts/aihub-cli.py"
            ]

            cli_files_exist = 0
            for cli_file in cli_files:
                if Path(cli_file).exists():
                    cli_files_exist += 1

            if cli_files_exist > 0:
                status = "PASS"
                message = f"CLI工具存在 ({cli_files_exist}/{len(cli_files)})"
            else:
                status = "FAIL"
                message = "CLI工具缺失"

            duration = time.time() - start_time
            self.add_result("ecosystem", "cli_tools", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("ecosystem", "cli_tools", "ERROR", duration, f"测试出错: {str(e)}")

    def test_business_features(self):
        """测试商业化功能"""
        print("\n💰 测试商业化功能")
        print("-" * 30)

        # 测试计费系统
        self.test_billing_system()

        # 测试企业版功能
        self.test_enterprise_features()

        # 测试分析工具
        self.test_analytics_tools()

    def test_billing_system(self):
        """测试计费系统"""
        start_time = time.time()

        try:
            # 检查计费相关文件
            billing_files = [
                "backend/services/billing_service.py",
                "backend/core/cost_tracker.py"
            ]

            billing_files_exist = 0
            for billing_file in billing_files:
                if Path(billing_file).exists():
                    billing_files_exist += 1

            if billing_files_exist >= 2:
                status = "PASS"
                message = f"计费系统文件完整 ({billing_files_exist}/{len(billing_files)})"
            else:
                status = "FAIL"
                message = f"计费系统文件缺失 ({billing_files_exist}/{len(billing_files)})"

            duration = time.time() - start_time
            self.add_result("business", "billing_system", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("business", "billing_system", "ERROR", duration, f"测试出错: {str(e)}")

    def test_enterprise_features(self):
        """测试企业版功能"""
        start_time = time.time()

        try:
            # 检查企业版相关文件
            enterprise_files = [
                "backend/services/subscription_service.py",
                "frontend/src/app/dashboard/billing/page.tsx"
            ]

            enterprise_files_exist = 0
            for enterprise_file in enterprise_files:
                if Path(enterprise_file).exists():
                    enterprise_files_exist += 1

            if enterprise_files_exist >= 2:
                status = "PASS"
                message = f"企业版功能文件完整 ({enterprise_files_exist}/{len(enterprise_files)})"
            else:
                status = "FAIL"
                message = f"企业版功能文件缺失 ({enterprise_files_exist}/{len(enterprise_files)})"

            duration = time.time() - start_time
            self.add_result("business", "enterprise_features", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("business", "enterprise_features", "ERROR", duration, f"测试出错: {str(e)}")

    def test_analytics_tools(self):
        """测试分析工具"""
        start_time = time.time()

        try:
            # 检查分析相关文件
            analytics_files = [
                "backend/services/monitoring_service.py"
            ]

            analytics_files_exist = 0
            for analytics_file in analytics_files:
                if Path(analytics_file).exists():
                    analytics_files_exist += 1

            if analytics_files_exist > 0:
                status = "PASS"
                message = f"分析工具文件存在 ({analytics_files_exist}/{len(analytics_files)})"
            else:
                status = "FAIL"
                message = "分析工具文件缺失"

            duration = time.time() - start_time
            self.add_result("business", "analytics_tools", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("business", "analytics_tools", "ERROR", duration, f"测试出错: {str(e)}")

    def test_internationalization(self):
        """测试国际化支持"""
        print("\n🌍 测试国际化支持")
        print("-" * 30)

        # 测试i18n系统
        self.test_i18n_system()

        # 测试多语言支持
        self.test_multilingual_support()

        # 测试区域化部署
        self.test_regional_deployment()

        # 测试文档本地化
        self.test_documentation_localization()

    def test_i18n_system(self):
        """测试i18n系统"""
        start_time = time.time()

        try:
            # 检查i18n上下文文件
            i18n_file = Path("frontend/src/contexts/I18nContext.tsx")
            if i18n_file.exists():
                # 检查文件内容是否包含国际化相关代码
                content = i18n_file.read_text(encoding='utf-8')
                if 'I18nProvider' in content and 'useI18n' in content:
                    status = "PASS"
                    message = "i18n系统实现完整"
                else:
                    status = "FAIL"
                    message = "i18n系统实现不完整"
            else:
                status = "FAIL"
                message = "i18n上下文文件不存在"

            duration = time.time() - start_time
            self.add_result("internationalization", "i18n_system", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("internationalization", "i18n_system", "ERROR", duration, f"测试出错: {str(e)}")

    def test_multilingual_support(self):
        """测试多语言支持"""
        start_time = time.time()

        try:
            # 检查翻译文件
            locale_dirs = [
                "frontend/src/locales/en-US",
                "frontend/src/locales/zh-CN",
                "frontend/src/locales/ja-JP"
            ]

            locale_dirs_exist = 0
            for locale_dir in locale_dirs:
                if Path(locale_dir).exists():
                    # 检查是否有翻译文件
                    if (Path(locale_dir) / "index.json").exists():
                        locale_dirs_exist += 1

            if locale_dirs_exist >= 3:
                status = "PASS"
                message = f"多语言翻译文件完整 ({locale_dirs_exist}/{len(locale_dirs)})"
            else:
                status = "FAIL"
                message = f"多语言翻译文件缺失 ({locale_dirs_exist}/{len(locale_dirs)})"

            duration = time.time() - start_time
            self.add_result("internationalization", "multilingual_support", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("internationalization", "multilingual_support", "ERROR", duration, f"测试出错: {str(e)}")

    def test_regional_deployment(self):
        """测试区域化部署"""
        start_time = time.time()

        try:
            # 检查部署配置文件
            deployment_files = [
                "deployment/regions/asia-pacific.yaml",
                "deployment/regions/europe.yaml",
                "deployment/regions/americas.yaml"
            ]

            deployment_files_exist = 0
            for deployment_file in deployment_files:
                if Path(deployment_file).exists():
                    deployment_files_exist += 1

            if deployment_files_exist >= 3:
                status = "PASS"
                message = f"区域化部署配置完整 ({deployment_files_exist}/{len(deployment_files)})"
            else:
                status = "FAIL"
                message = f"区域化部署配置缺失 ({deployment_files_exist}/{len(deployment_files)})"

            duration = time.time() - start_time
            self.add_result("internationalization", "regional_deployment", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("internationalization", "regional_deployment", "ERROR", duration, f"测试出错: {str(e)}")

    def test_documentation_localization(self):
        """测试文档本地化"""
        start_time = time.time()

        try:
            # 检查多语言文档
            doc_files = [
                "docs/user-guides/en-US/getting-started.md",
                "docs/user-guides/zh-CN/getting-started.md",
                "docs/api/en-US/README.md",
                "docs/api/zh-CN/README.md",
                "docs/developer-guides/en-US/README.md",
                "docs/developer-guides/zh-CN/README.md",
                "docs/help/en-US/README.md",
                "docs/help/zh-CN/README.md"
            ]

            doc_files_exist = 0
            for doc_file in doc_files:
                if Path(doc_file).exists():
                    doc_files_exist += 1

            if doc_files_exist >= 8:
                status = "PASS"
                message = f"多语言文档完整 ({doc_files_exist}/{len(doc_files)})"
            else:
                status = "FAIL"
                message = f"多语言文档缺失 ({doc_files_exist}/{len(doc_files)})"

            duration = time.time() - start_time
            self.add_result("internationalization", "documentation_localization", status, duration, message)

        except Exception as e:
            duration = time.time() - start_time
            self.add_result("internationalization", "documentation_localization", "ERROR", duration, f"测试出错: {str(e)}")

    def add_result(self, component: str, test_name: str, status: str,
                     duration: float, message: str, details: Dict[str, Any] = None):
        """添加测试结果"""
        result = TestResult(
            component=component,
            test_name=test_name,
            status=status,
            duration=duration,
            message=message,
            details=details
        )
        self.results.append(result)

        # 打印结果
        if self.verbose or status in ["FAIL", "ERROR"]:
            status_icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️", "ERROR": "💥"}[status]
            print(f"  {status_icon} {test_name}: {message} ({duration:.2f}s)")

    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 50)
        print("📊 Week 7 测试报告")
        print("=" * 50)

        # 统计结果
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r.status == "PASS"])
        failed_tests = len([r for r in self.results if r.status == "FAIL"])
        skipped_tests = len([r for r in self.results if r.status == "SKIP"])
        error_tests = len([r for r in self.results if r.status == "ERROR"])

        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {failed_tests}")
        print(f"跳过: {skipped_tests}")
        print(f"错误: {error_tests}")
        print(f"成功率: {(passed_tests/total_tests*100):.1f}%")

        # 按组件统计
        print("\n📋 按组件统计:")
        component_stats = {}
        for result in self.results:
            if result.component not in component_stats:
                component_stats[result.component] = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "error": 0}
            component_stats[result.component]["total"] += 1
            if result.status.lower() in component_stats[result.component]:
                component_stats[result.component][result.status.lower()] += 1
            else:
                component_stats[result.component][result.status.lower()] = 1

        for component, stats in component_stats.items():
            total = stats["total"]
            passed = stats["passed"]
            component_rate = (passed/total*100) if total > 0 else 0
            print(f"  {component}: {passed}/{total} ({component_rate:.1f}%)")

        # 失败的测试详情
        if failed_tests > 0 or error_tests > 0:
            print("\n❌ 需要修复的问题:")
            for result in self.results:
                if result.status in ["FAIL", "ERROR"]:
                    print(f"  - {result.component}.{result.test_name}: {result.message}")

        # 保存详细报告
        self.save_detailed_report()

    def save_detailed_report(self):
        """保存详细测试报告"""
        report_data = {
            "test_date": datetime.now().isoformat(),
            "total_tests": len(self.results),
            "passed_tests": len([r for r in self.results if r.status == "PASS"]),
            "failed_tests": len([r for r in self.results if r.status == "FAIL"]),
            "skipped_tests": len([r for r in self.results if r.status == "SKIP"]),
            "error_tests": len([r for r in self.results if r.status == "ERROR"]),
            "results": [
                {
                    "component": r.component,
                    "test_name": r.test_name,
                    "status": r.status,
                    "duration": r.duration,
                    "message": r.message,
                    "details": r.details
                }
                for r in self.results
            ]
        }

        report_file = Path("test-reports/week7-test-report.json")
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存到: {report_file}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Week 7 综合功能测试")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--component", "-c",
                        choices=["multimodal_ai", "ux_optimizations", "multiplatform",
                               "ecosystem", "business", "internationalization"],
                        help="测试特定组件")

    args = parser.parse_args()

    # 创建测试套件
    test_suite = Week7TestSuite()
    test_suite.verbose = args.verbose

    try:
        if args.component:
            # 测试特定组件
            component_methods = {
                "multimodal_ai": test_suite.test_multimodal_ai,
                "ux_optimizations": test_suite.test_ux_optimizations,
                "multiplatform": test_suite.test_multiplatform_support,
                "ecosystem": test_suite.test_ecosystem_features,
                "business": test_suite.test_business_features,
                "internationalization": test_suite.test_internationalization
            }

            if args.component in component_methods:
                component_methods[args.component]()
            else:
                print(f"未知组件: {args.component}")
                return 1
        else:
            # 运行所有测试
            test_suite.run_all_tests()

        # 检查是否有严重问题
        failed_count = len([r for r in test_suite.results if r.status in ["FAIL", "ERROR"]])
        if failed_count > 0:
            return 1

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        return 2
    except Exception as e:
        print(f"\n💥 测试运行出错: {str(e)}")
        if args.verbose:
            traceback.print_exc()
        return 3

if __name__ == "__main__":
    sys.exit(main())