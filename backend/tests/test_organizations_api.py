#!/usr/bin/env python3
"""
Test Organizations API
"""

import requests
import json
import uuid
from typing import Dict, Any

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

def test_create_organization():
    """Test creating a new organization"""
    print("\n🧪 Testing organization creation...")

    org_data = {
        "name": "Test Organization API",
        "slug": f"test-org-api-{uuid.uuid4().hex[:8]}",
        "description": "Test organization for API validation",
        "plan": "pro",
        "settings": {
            "max_users": 100,
            "features": ["api-access", "priority-support"]
        }
    }

    try:
        response = requests.post(
            f"{BASE_URL}/organizations/",
            json=org_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 201:
            created_org = response.json()
            print(f"✅ Organization created successfully: {created_org['name']}")
            print(f"   ID: {created_org['id']}")
            print(f"   Slug: {created_org['slug']}")
            return created_org
        else:
            print(f"❌ Failed to create organization: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_get_organizations():
    """Test getting user organizations"""
    print("\n🧪 Testing get user organizations...")

    try:
        response = requests.get(
            f"{BASE_URL}/organizations/",
            timeout=10
        )

        if response.status_code == 200:
            organizations = response.json()
            print(f"✅ Retrieved {len(organizations)} organizations")
            for org in organizations:
                print(f"   - {org['name']} ({org['plan']})")
            return organizations
        else:
            print(f"❌ Failed to get organizations: {response.status_code}")
            print(f"   Response: {response.text}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return []

def test_get_organization_details(organization_id: str):
    """Test getting organization details"""
    print(f"\n🧪 Testing get organization details for ID: {organization_id}...")

    try:
        response = requests.get(
            f"{BASE_URL}/organizations/{organization_id}",
            timeout=10
        )

        if response.status_code == 200:
            org = response.json()
            print(f"✅ Retrieved organization: {org['name']}")
            print(f"   Description: {org.get('description', 'N/A')}")
            print(f"   Status: {org['status']}")
            print(f"   Created: {org['created_at']}")
            return org
        else:
            print(f"❌ Failed to get organization: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_update_organization(organization_id: str):
    """Test updating organization"""
    print(f"\n🧪 Testing update organization for ID: {organization_id}...")

    update_data = {
        "name": "Updated Test Organization",
        "description": "Updated description for testing",
        "settings": {
            "max_users": 200,
            "features": ["api-access", "priority-support", "advanced-analytics"]
        }
    }

    try:
        response = requests.put(
            f"{BASE_URL}/organizations/{organization_id}",
            json=update_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            updated_org = response.json()
            print(f"✅ Organization updated successfully: {updated_org['name']}")
            print(f"   New description: {updated_org['description']}")
            return updated_org
        else:
            print(f"❌ Failed to update organization: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_invite_member(organization_id: str):
    """Test inviting a member to organization"""
    print(f"\n🧪 Testing invite member to organization ID: {organization_id}...")

    invite_data = {
        "email": "test.invite@example.com",
        "role": "member"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/organizations/{organization_id}/invite",
            json=invite_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Member invitation sent: {result['message']}")
            print(f"   Email: {result['email']}")
            print(f"   Role: {result['role']}")
            return result
        else:
            print(f"❌ Failed to invite member: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_get_organization_members(organization_id: str):
    """Test getting organization members"""
    print(f"\n🧪 Testing get organization members for ID: {organization_id}...")

    try:
        response = requests.get(
            f"{BASE_URL}/organizations/{organization_id}/members",
            timeout=10
        )

        if response.status_code == 200:
            members = response.json()
            print(f"✅ Retrieved {len(members)} members")
            for member in members:
                print(f"   - {member['name']} ({member['email']}) - {member['role']}")
            return members
        else:
            print(f"❌ Failed to get members: {response.status_code}")
            print(f"   Response: {response.text}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return []

def test_get_organization_stats(organization_id: str):
    """Test getting organization statistics"""
    print(f"\n🧪 Testing get organization stats for ID: {organization_id}...")

    try:
        response = requests.get(
            f"{BASE_URL}/organizations/{organization_id}/stats",
            timeout=10
        )

        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Retrieved organization statistics")
            print(f"   Member count: {stats['member_count']}")
            print(f"   Team count: {stats['team_count']}")
            print(f"   Total requests (30d): {stats['usage_stats']['total_requests_30d']}")
            print(f"   Total cost (30d): ${stats['usage_stats']['total_cost_30d']:.4f}")
            print(f"   User role: {stats['user_role']}")

            if stats.get('budget'):
                budget = stats['budget']
                print(f"   Budget limit: ${budget['monthly_limit']:.2f}")
                print(f"   Current spend: ${budget['current_spend']:.2f}")
                print(f"   Usage percentage: {budget['usage_percentage']:.1f}%")

            return stats
        else:
            print(f"❌ Failed to get stats: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def main():
    """Main test function"""
    print("🚀 Starting Organizations API Tests")
    print("=" * 50)

    # Test API connection
    if not test_api_connection():
        return

    # Test creating organization
    created_org = test_create_organization()
    if not created_org:
        print("❌ Cannot proceed without a valid organization")
        return

    organization_id = created_org['id']

    # Test getting all organizations
    organizations = test_get_organizations()

    # Test getting organization details
    test_get_organization_details(organization_id)

    # Test updating organization
    test_update_organization(organization_id)

    # Test inviting member
    test_invite_member(organization_id)

    # Test getting organization members
    test_get_organization_members(organization_id)

    # Test getting organization statistics
    test_get_organization_stats(organization_id)

    print("\n" + "=" * 50)
    print("🎉 Organizations API tests completed!")
    print(f"📝 Test organization ID: {organization_id}")
    print("💡 You can explore the API endpoints using this ID in the documentation")

if __name__ == "__main__":
    main()