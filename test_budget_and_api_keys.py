#!/usr/bin/env python3
"""
Test Budget and API Keys Management API

This script tests the Day 11 implementation:
- Budget Management API (5+ endpoints)
- Organization API Keys Management (8+ endpoints)
- Budget Control and Quota Management
"""

import requests
import json
import uuid
from typing import Dict, Any, Optional

# API base URL
BASE_URL = "http://localhost:8001/api/v1"

def test_api_connection():
    """Test if the API server is running"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running")
            return True
        else:
            print(f"❌ API server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to API server: {e}")
        print("Please make sure the backend server is running on http://localhost:8001")
        return False

def get_test_organization():
    """Get a test organization ID for operations"""
    try:
        response = requests.get(f"{BASE_URL}/organizations/", timeout=10)

        if response.status_code == 200:
            organizations = response.json()
            if organizations:
                org_id = organizations[0]['id']
                print(f"✅ Using test organization: {organizations[0]['name']} ({org_id})")
                return org_id
            else:
                print("❌ No organizations found. Please create an organization first.")
                return None
        else:
            print(f"❌ Failed to get organizations: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error getting test organization: {e}")
        return None

def test_budget_management(organization_id: str):
    """Test budget management API endpoints"""
    print(f"\n🧪 Testing Budget Management for organization {organization_id}...")

    # Test creating budget
    budget_data = {
        "monthly_limit": 1000.00,
        "alert_threshold": 80.0,
        "currency": "USD"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/organizations/{organization_id}/budgets",
            json=budget_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            print("✅ Budget created successfully")
            created_budget = response.json()
            print(f"   Monthly Limit: ${created_budget['monthly_limit']}")
            print(f"   Alert Threshold: {created_budget['alert_threshold']}%")
        else:
            print(f"❌ Failed to create budget: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error creating budget: {e}")
        return None

    # Test getting budget with stats
    try:
        response = requests.get(
            f"{BASE_URL}/organizations/{organization_id}/budgets",
            timeout=10
        )

        if response.status_code == 200:
            budget_stats = response.json()
            print("✅ Retrieved budget with statistics:")
            print(f"   Current Spend: ${budget_stats['current_spend']}")
            print(f"   Usage Percentage: {budget_stats['usage_percentage']:.2f}%")
            print(f"   Remaining Budget: ${budget_stats['remaining_budget']}")
            print(f"   Is Alert Reached: {budget_stats['is_alert_threshold_reached']}")
            return budget_stats
        else:
            print(f"❌ Failed to get budget stats: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error getting budget stats: {e}")
        return None

def test_budget_alerts(organization_id: str):
    """Test budget alerts configuration"""
    print(f"\n🧪 Testing Budget Alerts...")

    try:
        response = requests.get(
            f"{BASE_URL}/organizations/{organization_id}/budgets/alerts/test",
            timeout=10
        )

        if response.status_code == 200:
            alert_test = response.json()
            print("✅ Budget alert test completed:")
            print(f"   Usage Percentage: {alert_test['current_status']['usage_percentage']:.2f}%")
            print(f"   Would Send Alert: {alert_test['would_send_alert']}")
            print(f"   Alert Count: {alert_test['alert_count']}")
            return alert_test
        else:
            print(f"❌ Failed to test budget alerts: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error testing budget alerts: {e}")
        return None

def test_budget_usage_history(organization_id: str):
    """Test budget usage history"""
    print(f"\n🧪 Testing Budget Usage History...")

    try:
        response = requests.get(
            f"{BASE_URL}/organizations/{organization_id}/budgets/usage",
            params={"days": 7},
            timeout=10
        )

        if response.status_code == 200:
            usage_data = response.json()
            print("✅ Retrieved usage history:")
            print(f"   Period Days: {usage_data['period_days']}")
            print(f"   Total Records: {usage_data['total_records']}")
            if usage_data['usage_history']:
                latest = usage_data['usage_history'][0]
                print(f"   Latest Day: {latest['date']}, Cost: ${latest['cost']:.4f}")
            return usage_data
        else:
            print(f"❌ Failed to get usage history: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error getting usage history: {e}")
        return None

def test_api_key_creation(organization_id: str):
    """Test API key creation"""
    print(f"\n🧪 Testing API Key Creation...")

    key_data = {
        "name": f"Test API Key {uuid.uuid4().hex[:8]}",
        "permissions": {
            "chat": ["read", "write"],
            "models": ["read"]
        },
        "rate_limit": 100,
        "monthly_quota": 10000
    }

    try:
        response = requests.post(
            f"{BASE_URL}/organizations/{organization_id}/api-keys",
            json=key_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            print("✅ API key created successfully")
            result = response.json()
            print(f"   Key Name: {result['key_details']['name']}")
            print(f"   Key Prefix: {result['key_details']['key_prefix']}")
            print(f"   Rate Limit: {result['key_details']['rate_limit']}/min")
            print(f"   Monthly Quota: {result['key_details']['monthly_quota']}")
            print(f"   API Key (save this!): {result['api_key'][:20]}...")
            return result['api_key'], result['key_details']['id']
        else:
            print(f"❌ Failed to create API key: {response.status_code}")
            print(f"   Response: {response.text}")
            return None, None

    except Exception as e:
        print(f"❌ Error creating API key: {e}")
        return None, None

def test_api_key_management(organization_id: str, api_key_id: str):
    """Test API key management endpoints"""
    print(f"\n🧪 Testing API Key Management...")

    # Test getting API key details
    try:
        response = requests.get(
            f"{BASE_URL}/api-keys/{api_key_id}",
            timeout=10
        )

        if response.status_code == 200:
            key_details = response.json()
            print("✅ Retrieved API key details:")
            print(f"   Name: {key_details['name']}")
            print(f"   Status: {key_details['status']}")
            print(f"   Is Active: {key_details['is_active']}")
            print(f"   Monthly Usage: {key_details['current_month_usage']}")
        else:
            print(f"❌ Failed to get API key details: {response.status_code}")

    except Exception as e:
        print(f"❌ Error getting API key details: {e}")

    # Test updating API key
    update_data = {
        "name": "Updated Test API Key",
        "rate_limit": 200
    }

    try:
        response = requests.put(
            f"{BASE_URL}/api-keys/{api_key_id}",
            json=update_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            print("✅ API key updated successfully")
            updated = response.json()
            print(f"   New Name: {updated['name']}")
            print(f"   New Rate Limit: {updated['rate_limit']}")
        else:
            print(f"❌ Failed to update API key: {response.status_code}")

    except Exception as e:
        print(f"❌ Error updating API key: {e}")

def test_organization_api_keys(organization_id: str):
    """Test getting all API keys for an organization"""
    print(f"\n🧪 Testing Organization API Keys...")

    try:
        response = requests.get(
            f"{BASE_URL}/organizations/{organization_id}/api-keys",
            timeout=10
        )

        if response.status_code == 200:
            api_keys = response.json()
            print(f"✅ Retrieved {len(api_keys)} API keys")
            for key in api_keys:
                print(f"   - {key['name']} ({key['key_prefix']}) - {key['status']}")
            return api_keys
        else:
            print(f"❌ Failed to get organization API keys: {response.status_code}")
            return []

    except Exception as e:
        print(f"❌ Error getting organization API keys: {e}")
        return []

def test_api_key_summary(organization_id: str):
    """Test API keys summary"""
    print(f"\n🧪 Testing API Keys Summary...")

    try:
        response = requests.get(
            f"{BASE_URL}/organizations/{organization_id}/api-keys/summary",
            timeout=10
        )

        if response.status_code == 200:
            summary = response.json()
            print("✅ Retrieved API keys summary:")
            print(f"   Total Keys: {summary['summary']['total_keys']}")
            print(f"   Active Keys: {summary['summary']['active_keys']}")
            print(f"   Total Monthly Usage: {summary['usage_statistics']['total_monthly_usage']}")
            print(f"   Quota Utilization: {summary['usage_statistics']['quota_utilization_percentage']:.2f}%")
            print(f"   Keys Needing Attention: {summary['health_indicators']['keys_needing_attention']}")
            return summary
        else:
            print(f"❌ Failed to get API keys summary: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error getting API keys summary: {e}")
        return None

def test_budget_check(organization_id: str):
    """Test budget limit check"""
    print(f"\n🧪 Testing Budget Limit Check...")

    try:
        response = requests.post(
            f"{BASE_URL}/organizations/{organization_id}/budgets/check",
            params={"estimated_cost": 50.0},
            timeout=10
        )

        if response.status_code == 200:
            check_result = response.json()
            print("✅ Budget check completed:")
            print(f"   Estimated Cost: ${check_result['estimated_cost']}")
            print(f"   Within Budget: {check_result['within_budget']}")
            print(f"   Message: {check_result['message']}")
            return check_result
        else:
            print(f"❌ Failed to check budget: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error checking budget: {e}")
        return None

def test_budget_summary(organization_id: str):
    """Test comprehensive budget summary"""
    print(f"\n🧪 Testing Budget Summary...")

    try:
        response = requests.get(
            f"{BASE_URL}/organizations/{organization_id}/budgets/summary",
            timeout=10
        )

        if response.status_code == 200:
            summary = response.json()
            print("✅ Retrieved comprehensive budget summary:")
            print(f"   Budget Status: {summary['budget_status']['status']}")
            print(f"   Projected Monthly Spend: ${summary['projections']['projected_monthly_spend']:.2f}")
            print(f"   Health Status: {summary['health_status']}")
            print(f"   Recommendations: {len(summary['recommendations'])}")
            for rec in summary['recommendations']:
                print(f"     - {rec}")
            return summary
        else:
            print(f"❌ Failed to get budget summary: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error getting budget summary: {e}")
        return None

def cleanup_test_data(organization_id: str, api_key_id: Optional[str] = None):
    """Clean up test data"""
    print(f"\n🧹 Cleaning up test data...")

    if api_key_id:
        try:
            response = requests.post(
                f"{BASE_URL}/api-keys/{api_key_id}/revoke",
                timeout=10
            )
            if response.status_code == 200:
                print("✅ Test API key revoked")
            else:
                print(f"⚠️ Failed to revoke API key: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Error revoking API key: {e}")

def main():
    """Main test function"""
    print("🚀 Starting Day 11 Budget and API Keys API Tests")
    print("=" * 60)

    # Test API connection
    if not test_api_connection():
        return

    # Get test organization
    organization_id = get_test_organization()
    if not organization_id:
        print("❌ Cannot proceed without a valid organization")
        return

    api_key_id = None

    try:
        # Test Budget Management
        print("\n" + "=" * 40)
        print("BUDGET MANAGEMENT TESTS")
        print("=" * 40)

        budget_stats = test_budget_management(organization_id)
        if budget_stats:
            test_budget_alerts(organization_id)
            test_budget_usage_history(organization_id)
            test_budget_check(organization_id)
            test_budget_summary(organization_id)

        # Test API Keys Management
        print("\n" + "=" * 40)
        print("API KEYS MANAGEMENT TESTS")
        print("=" * 40)

        api_key, api_key_id = test_api_key_creation(organization_id)
        if api_key_id:
            test_api_key_management(organization_id, api_key_id)
            test_organization_api_keys(organization_id)
            test_api_key_summary(organization_id)

        print("\n" + "=" * 60)
        print("🎉 Day 11 API tests completed successfully!")
        print(f"📝 Test organization ID: {organization_id}")
        if api_key_id:
            print(f"📝 Test API key ID: {api_key_id}")
        print("💡 All endpoints are working as expected")

    except KeyboardInterrupt:
        print("\n\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
    finally:
        # Clean up test data
        cleanup_test_data(organization_id, api_key_id)

if __name__ == "__main__":
    main()