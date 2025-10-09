#!/usr/bin/env python3
"""
AI Hub平台集成测试脚本
测试核心功能是否正常工作
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_imports():
    """测试模块导入"""
    print("🧪 测试模块导入...")

    try:
        # 测试核心模块导入
        from backend.core.ai_service import ai_manager
        from backend.core.session_manager import SessionManager
        from backend.core.cost_tracker import CostTracker
        from backend.core.cache_service import cache_service
        from backend.core.health_service import health_service
        from backend.core.config_manager import config_manager

        print("✅ 核心模块导入成功")

        # 测试API模块导入
        from backend.api.v1.chat import router as chat_router
        from backend.api.v1.stats import router as stats_router
        from backend.api.v1.health import router as health_router
        from backend.api.v1.models import router as models_router
        from backend.api.v1.config import router as config_router

        print("✅ API模块导入成功")

        return True

    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        return False

async def test_ai_services():
    """测试AI服务"""
    print("\n🤖 测试AI服务...")

    try:
        from backend.core.ai_service import ai_manager

        # 测试获取可用服务
        services = await ai_manager.list_available_services()
        print(f"✅ 可用AI服务: {services['services']}")

        # 测试获取模型
        for service_name in services['services']:
            try:
                models = await ai_manager.get_models(service_name)
                print(f"✅ {service_name} 模型数量: {models['total_count']}")
            except Exception as e:
                print(f"⚠️  {service_name} 模型获取失败: {e}")

        return True

    except Exception as e:
        print(f"❌ AI服务测试失败: {e}")
        return False

async def test_session_manager():
    """测试会话管理器"""
    print("\n💾 测试会话管理器...")

    try:
        from backend.core.session_manager import SessionManager

        session_manager = SessionManager()

        # 创建会话
        session = await session_manager.create_session("测试会话")
        print(f"✅ 创建会话成功: {session.id[:8]}...")

        # 获取会话
        retrieved_session = await session_manager.get_session(session.id)
        print(f"✅ 获取会话成功: {retrieved_session.title}")

        # 添加消息
        message = await session_manager.add_message(
            session.id,
            "user",
            "Hello, AI Hub!"
        )
        print(f"✅ 添加消息成功: {message.id[:8]}...")

        return True

    except Exception as e:
        print(f"❌ 会话管理器测试失败: {e}")
        return False

async def test_cache_service():
    """测试缓存服务"""
    print("\n💾 测试缓存服务...")

    try:
        from backend.core.cache_service import cache_service

        # 设置缓存
        cache_service.set("test_key", "test_value", ttl=60)
        print("✅ 设置缓存成功")

        # 获取缓存
        value = cache_service.get("test_key")
        print(f"✅ 获取缓存成功: {value}")

        # 获取统计
        stats = cache_service.get_stats()
        print(f"✅ 缓存统计: 命中率 {stats['hit_rate']:.1%}")

        return True

    except Exception as e:
        print(f"❌ 缓存服务测试失败: {e}")
        return False

async def test_health_service():
    """测试健康检查服务"""
    print("\n🏥 测试健康检查服务...")

    try:
        from backend.core.health_service import get_system_health

        # 获取系统健康状态
        health_data = await get_system_health()
        print(f"✅ 系统状态: {health_data['status']}")
        print(f"✅ 服务数量: {len(health_data['services'])}")

        for service in health_data['services']:
            print(f"   - {service['name']}: {service['status']} ({service['response_time']:.3f}s)")

        return True

    except Exception as e:
        print(f"❌ 健康检查服务测试失败: {e}")
        return False

async def test_config_manager():
    """测试配置管理器"""
    print("\n⚙️ 测试配置管理器...")

    try:
        from backend.core.config_manager import config_manager

        # 加载应用配置
        app_config = await config_manager.load_app_config()
        print(f"✅ 应用配置加载成功")
        print(f"   - 调试模式: {app_config.debug_mode}")
        print(f"   - 限流启用: {app_config.enable_rate_limiting}")

        # 加载特性开关
        feature_flags = await config_manager.load_feature_flags()
        print(f"✅ 特性开关加载成功: {len(feature_flags)} 个开关")

        return True

    except Exception as e:
        print(f"❌ 配置管理器测试失败: {e}")
        return False

async def test_api_structure():
    """测试API结构"""
    print("\n🌐 测试API结构...")

    try:
        from backend.api.v1.router import api_router

        # 获取路由信息
        routes = []
        for route in api_router.routes:
            if hasattr(route, 'path'):
                routes.append(f"{route.methods} {route.path}")

        print(f"✅ API路由数量: {len(routes)}")

        # 显示主要路由
        main_routes = [r for r in routes if any(x in r for x in ['/health', '/models', '/stats', '/config'])]
        for route in main_routes[:5]:  # 只显示前5个
            print(f"   - {route}")

        return True

    except Exception as e:
        print(f"❌ API结构测试失败: {e}")
        return False

async def generate_test_report(results):
    """生成测试报告"""
    print("\n📊 测试报告")
    print("=" * 50)

    passed = sum(results.values())
    total = len(results)
    success_rate = (passed / total) * 100 if total > 0 else 0

    print(f"总测试数: {total}")
    print(f"通过数: {passed}")
    print(f"失败数: {total - passed}")
    print(f"成功率: {success_rate:.1f}%")

    print("\n详细结果:")
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")

    if success_rate >= 80:
        print("\n🎉 测试结果: 优秀！AI Hub平台功能完整")
    elif success_rate >= 60:
        print("\n👍 测试结果: 良好，大部分功能正常")
    else:
        print("\n⚠️  测试结果: 需要改进，部分功能存在问题")

    print(f"\n📈 平台就绪度: {success_rate:.0f}%")

async def main():
    """主测试函数"""
    print("🚀 AI Hub平台集成测试")
    print("=" * 50)

    # 运行测试
    test_results = {}

    test_functions = [
        ("模块导入", test_imports),
        ("AI服务", test_ai_services),
        ("会话管理", test_session_manager),
        ("缓存服务", test_cache_service),
        ("健康检查", test_health_service),
        ("配置管理", test_config_manager),
        ("API结构", test_api_structure)
    ]

    for test_name, test_func in test_functions:
        try:
            result = await test_func()
            test_results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            test_results[test_name] = False

    # 生成报告
    await generate_test_report(test_results)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")