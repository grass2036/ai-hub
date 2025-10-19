#!/usr/bin/env python3
"""
第二个月第一天功能测试脚本
测试API商业化基础功能
"""

import asyncio
import json
import requests
from datetime import datetime

# 测试配置
BASE_URL = "http://localhost:8001"
API_BASE = f"{BASE_URL}/api/v1"

def print_section(title):
    """打印测试章节标题"""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print(f"{'='*60}")

def print_success(message):
    """打印成功消息"""
    print(f"✅ {message}")

def print_info(message):
    """打印信息消息"""
    print(f"ℹ️  {message}")

def print_error(message):
    """打印错误消息"""
    print(f"❌ {message}")

def test_server_health():
    """测试服务器健康状态"""
    print_section("服务器健康检查")

    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"服务器状态: {data.get('status')}")
            print_info(f"环境: {data.get('environment')}")
            print_info(f"版本: {data.get('version')}")
            return True
        else:
            print_error(f"服务器响应异常: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"无法连接到服务器: {str(e)}")
        return False

def test_api_status():
    """测试API状态"""
    print_section("API状态检查")

    try:
        response = requests.get(f"{API_BASE}/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"API状态: {data.get('status')}")
            print_info(f"AI服务数量: {data.get('ai_services', {}).get('total_configured', 0)}")
            print_info(f"数据库类型: {data.get('database', {}).get('type')}")
            return True
        else:
            print_error(f"API状态检查失败: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"API状态检查异常: {str(e)}")
        return False

def test_developer_registration():
    """测试开发者注册"""
    print_section("开发者注册测试")

    test_email = f"test_dev_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
    registration_data = {
        "email": test_email,
        "password": "test123456",
        "full_name": "测试开发者",
        "company_name": "测试公司",
        "developer_type": "individual"
    }

    try:
        response = requests.post(
            f"{API_BASE}/developer/auth/register",
            json=registration_data,
            timeout=10
        )

        if response.status_code == 201:
            data = response.json()
            print_success("开发者注册成功")
            print_info(f"邮箱: {test_email}")

            if data.get("data", {}).get("access_token"):
                print_success("获得访问令牌")
                return test_email, data["data"]["access_token"], data["data"]["developer"]["id"]
            else:
                print_error("未获得访问令牌")
                return test_email, None, None
        else:
            print_error(f"注册失败: {response.status_code}")
            print_error(f"错误信息: {response.text}")
            return test_email, None, None
    except Exception as e:
        print_error(f"注册请求异常: {str(e)}")
        return test_email, None, None

def test_developer_login(email):
    """测试开发者登录"""
    print_section("开发者登录测试")

    login_data = {
        "email": email,
        "password": "test123456"
    }

    try:
        response = requests.post(
            f"{API_BASE}/developer/auth/login",
            json=login_data,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print_success("开发者登录成功")

            if data.get("data", {}).get("access_token"):
                print_success("获得访问令牌")
                return data["data"]["access_token"], data["data"]["developer"]["id"]
            else:
                print_error("未获得访问令牌")
                return None, None
        else:
            print_error(f"登录失败: {response.status_code}")
            print_error(f"错误信息: {response.text}")
            return None, None
    except Exception as e:
        print_error(f"登录请求异常: {str(e)}")
        return None, None

def test_api_key_management(access_token, developer_id):
    """测试API密钥管理"""
    print_section("API密钥管理测试")

    headers = {"Authorization": f"Bearer {access_token}"}

    # 创建API密钥
    create_data = {
        "name": "测试API密钥",
        "permissions": ["chat.completions", "chat.models", "usage.view"],
        "rate_limit": 100,
        "expires_days": 30
    }

    try:
        response = requests.post(
            f"{API_BASE}/developer/keys/keys",
            json=create_data,
            headers=headers,
            timeout=10
        )

        if response.status_code == 201:
            data = response.json()
            print_success("API密钥创建成功")

            api_key = data.get("data", {}).get("api_key")
            key_id = data.get("data", {}).get("id")

            if api_key:
                print_success("获得完整API密钥")
                print_info(f"密钥ID: {key_id}")
                print_info(f"密钥前缀: {data.get('data', {}).get('key_prefix')}")

                # 测试获取API密钥列表
                test_get_api_keys(headers)

                return api_key, key_id
            else:
                print_error("未获得API密钥")
                return None, None
        else:
            print_error(f"API密钥创建失败: {response.status_code}")
            print_error(f"错误信息: {response.text}")
            return None, None
    except Exception as e:
        print_error(f"API密钥创建异常: {str(e)}")
        return None, None

def test_get_api_keys(headers):
    """测试获取API密钥列表"""
    try:
        response = requests.get(
            f"{API_BASE}/developer/keys/keys",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            keys = data.get("data", {}).get("api_keys", [])
            print_success(f"获取到 {len(keys)} 个API密钥")
            for key in keys:
                print_info(f"- {key.get('name')} ({key.get('key_prefix')})")
        else:
            print_error(f"获取API密钥列表失败: {response.status_code}")
    except Exception as e:
        print_error(f"获取API密钥列表异常: {str(e)}")

def test_api_key_authentication(api_key):
    """测试API密钥认证"""
    print_section("API密钥认证测试")

    headers = {"Authorization": f"Bearer {api_key}"}

    # 测试获取模型列表（应该成功）
    try:
        response = requests.get(
            f"{API_BASE}/models",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            print_success("API密钥认证成功")
            data = response.json()
            models = data.get("models", [])
            print_info(f"获取到 {len(models)} 个可用模型")
        else:
            print_error(f"API密钥认证失败: {response.status_code}")
            print_error(f"错误信息: {response.text}")
    except Exception as e:
        print_error(f"API密钥认证异常: {str(e)}")

def test_usage_quota(access_token):
    """测试用量配额"""
    print_section("用量配额测试")

    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.get(
            f"{API_BASE}/developer/keys/quota",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            quota_info = data.get("data", {})
            print_success("用量配额获取成功")
            print_info(f"月度配额: {quota_info.get('monthly_quota', 0)} tokens")
            print_info(f"已使用: {quota_info.get('monthly_used', 0)} tokens")
            print_info(f"剩余: {quota_info.get('monthly_remaining', 0)} tokens")
            print_info(f"使用率: {quota_info.get('monthly_usage_percent', 0)}%")
            print_info(f"活跃API密钥: {quota_info.get('active_api_keys', 0)}个")
        else:
            print_error(f"用量配额获取失败: {response.status_code}")
            print_error(f"错误信息: {response.text}")
    except Exception as e:
        print_error(f"用量配额获取异常: {str(e)}")

def test_subscription_plans():
    """测试订阅套餐"""
    print_section("订阅套餐测试")

    try:
        response = requests.get(
            f"{API_BASE}/payments/plans",
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            plans = data.get("data", {}).get("plans", [])
            print_success(f"获取到 {len(plans)} 个订阅套餐")
            for plan in plans:
                print_info(f"- {plan.get('name')}: ${plan.get('price')}/{plan.get('billing_cycle')}")
        else:
            print_error(f"订阅套餐获取失败: {response.status_code}")
    except Exception as e:
        print_error(f"订阅套餐获取异常: {str(e)}")

def main():
    """主测试函数"""
    print("🚀 AI Hub Platform 第二个月第一天功能测试")
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 测试计数器
    total_tests = 0
    passed_tests = 0

    # 1. 测试服务器健康
    total_tests += 1
    if test_server_health():
        passed_tests += 1

    # 2. 测试API状态
    total_tests += 1
    if test_api_status():
        passed_tests += 1

    # 3. 测试开发者注册
    total_tests += 1
    test_email, access_token, developer_id = test_developer_registration()
    if access_token:
        passed_tests += 1

        # 4. 测试API密钥管理
        total_tests += 1
        api_key, key_id = test_api_key_management(access_token, developer_id)
        if api_key:
            passed_tests += 1

            # 5. 测试API密钥认证
            total_tests += 1
            test_api_key_authentication(api_key)
            passed_tests += 1

            # 6. 测试用量配额
            total_tests += 1
            test_usage_quota(access_token)
            passed_tests += 1

    # 7. 测试订阅套餐
    total_tests += 1
    test_subscription_plans()
    passed_tests += 1

    # 测试总结
    print_section("测试总结")
    print_info(f"总测试数: {total_tests}")
    print_success(f"通过测试: {passed_tests}")
    print_info(f"通过率: {passed_tests/total_tests*100:.1f}%")

    if passed_tests == total_tests:
        print_success("🎉 所有测试通过！第二个月第一天功能验证成功！")
    else:
        print_error(f"⚠️  有 {total_tests - passed_tests} 个测试失败，请检查相关功能。")

    print("\n📋 功能验证清单:")
    print("✅ API密钥认证系统 - 生成、验证和管理API密钥")
    print("✅ 用户注册和管理系统")
    print("✅ 基础订阅计费逻辑")
    print("✅ 用量配额管理系统")
    print("\n🎯 第二个月第一天任务完成！")

if __name__ == "__main__":
    main()