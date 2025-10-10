#!/usr/bin/env python3
"""
Test Teams API
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

def get_test_organization():
    """Get a test organization ID for team operations"""
    try:
        # First get organizations to find one we can use
        response = requests.get(
            f"{BASE_URL}/organizations/",
            timeout=10
        )

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

def test_create_team(organization_id: str):
    """Test creating a new team"""
    print(f"\n🧪 Testing team creation in organization {organization_id}...")

    team_data = {
        "name": f"Test Team {uuid.uuid4().hex[:8]}",
        "description": "Test team for API validation",
        "parent_team_id": None,
        "settings": {
            "max_members": 50,
            "specialization": "testing"
        }
    }

    try:
        response = requests.post(
            f"{BASE_URL}/organizations/{organization_id}/teams",
            json=team_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 201:
            created_team = response.json()
            print(f"✅ Team created successfully: {created_team['name']}")
            print(f"   ID: {created_team['id']}")
            print(f"   Organization: {created_team['organization_id']}")
            return created_team
        else:
            print(f"❌ Failed to create team: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_get_organization_teams(organization_id: str):
    """Test getting teams in an organization"""
    print(f"\n🧪 Testing get teams for organization {organization_id}...")

    try:
        response = requests.get(
            f"{BASE_URL}/organizations/{organization_id}/teams",
            timeout=10
        )

        if response.status_code == 200:
            teams = response.json()
            print(f"✅ Retrieved {len(teams)} teams")
            for team in teams:
                print(f"   - {team['name']} (ID: {team['id'][:8]}...)")
            return teams
        else:
            print(f"❌ Failed to get teams: {response.status_code}")
            print(f"   Response: {response.text}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return []

def test_get_team_details(team_id: str):
    """Test getting team details"""
    print(f"\n🧪 Testing get team details for ID: {team_id}...")

    try:
        response = requests.get(
            f"{BASE_URL}/teams/{team_id}",
            timeout=10
        )

        if response.status_code == 200:
            team = response.json()
            print(f"✅ Retrieved team: {team['name']}")
            print(f"   Description: {team.get('description', 'N/A')}")
            print(f"   Organization: {team['organization_id']}")
            print(f"   Created: {team['created_at']}")
            return team
        else:
            print(f"❌ Failed to get team: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_update_team(team_id: str):
    """Test updating a team"""
    print(f"\n🧪 Testing update team for ID: {team_id}...")

    update_data = {
        "name": "Updated Test Team",
        "description": "Updated description for testing",
        "settings": {
            "max_members": 100,
            "specialization": "updated-testing"
        }
    }

    try:
        response = requests.put(
            f"{BASE_URL}/teams/{team_id}",
            json=update_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            updated_team = response.json()
            print(f"✅ Team updated successfully: {updated_team['name']}")
            print(f"   New description: {updated_team['description']}")
            return updated_team
        else:
            print(f"❌ Failed to update team: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_add_team_member(team_id: str):
    """Test adding a member to a team"""
    print(f"\n🧪 Testing add member to team ID: {team_id}...")

    # For this test, we'll use a test user ID
    # In a real scenario, you'd get this from user registration or existing users
    test_user_id = "550e8400-e29b-41d4-a716-446655440001"  # Test user ID

    member_data = {
        "user_id": test_user_id
    }

    try:
        response = requests.post(
            f"{BASE_URL}/teams/{team_id}/members",
            json=member_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Member added successfully: {result['message']}")
            return result
        else:
            print(f"❌ Failed to add member: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_get_team_members(team_id: str):
    """Test getting team members"""
    print(f"\n🧪 Testing get team members for ID: {team_id}...")

    try:
        response = requests.get(
            f"{BASE_URL}/teams/{team_id}/members",
            timeout=10
        )

        if response.status_code == 200:
            members = response.json()
            print(f"✅ Retrieved {len(members)} members")
            for member in members:
                print(f"   - {member.get('name', 'Unknown')} ({member.get('email', 'No email')})")
            return members
        else:
            print(f"❌ Failed to get team members: {response.status_code}")
            print(f"   Response: {response.text}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return []

def test_get_team_stats(team_id: str):
    """Test getting team statistics"""
    print(f"\n🧪 Testing get team stats for ID: {team_id}...")

    try:
        response = requests.get(
            f"{BASE_URL}/teams/{team_id}/stats",
            timeout=10
        )

        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Retrieved team statistics")
            print(f"   Team name: {stats['team_name']}")
            print(f"   Member count: {stats['member_count']}")
            print(f"   Sub-team count: {stats['sub_team_count']}")
            print(f"   Total requests (30d): {stats['usage_stats']['total_requests_30d']}")
            print(f"   Total cost (30d): ${stats['usage_stats']['total_cost_30d']:.4f}")
            return stats
        else:
            print(f"❌ Failed to get team stats: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_team_hierarchy(organization_id: str):
    """Test getting team hierarchy"""
    print(f"\n🧪 Testing team hierarchy for organization {organization_id}...")

    try:
        response = requests.get(
            f"{BASE_URL}/organizations/{organization_id}/teams/hierarchy",
            timeout=10
        )

        if response.status_code == 200:
            hierarchy = response.json()
            print(f"✅ Retrieved team hierarchy with {len(hierarchy)} root teams")
            print_team_hierarchy(hierarchy)
            return hierarchy
        else:
            print(f"❌ Failed to get team hierarchy: {response.status_code}")
            print(f"   Response: {response.text}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return []

def print_team_hierarchy(hierarchy: list, indent: int = 0):
    """Print team hierarchy recursively"""
    for team in hierarchy:
        prefix = "  " * indent
        print(f"{prefix}- {team['name']} (ID: {team['id'][:8]}...)")
        if team.get('children'):
            print_team_hierarchy(team['children'], indent + 1)

def test_delete_team(team_id: str):
    """Test deleting a team"""
    print(f"\n🧪 Testing delete team for ID: {team_id}...")

    try:
        response = requests.delete(
            f"{BASE_URL}/teams/{team_id}",
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Team deleted successfully: {result['message']}")
            return True
        else:
            print(f"❌ Failed to delete team: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting Teams API Tests")
    print("=" * 50)

    # Test API connection
    if not test_api_connection():
        return

    # Get test organization
    organization_id = get_test_organization()
    if not organization_id:
        print("❌ Cannot proceed without a valid organization")
        return

    # Test creating team
    created_team = test_create_team(organization_id)
    if not created_team:
        print("❌ Cannot proceed without a valid team")
        return

    team_id = created_team['id']

    # Test getting organization teams
    teams = test_get_organization_teams(organization_id)

    # Test getting team details
    test_get_team_details(team_id)

    # Test updating team
    test_update_team(team_id)

    # Test team hierarchy
    test_team_hierarchy(organization_id)

    # Test team statistics
    test_get_team_stats(team_id)

    # Test adding member
    test_add_team_member(team_id)

    # Test getting team members
    test_get_team_members(team_id)

    # Test deleting team (cleanup)
    test_delete_team(team_id)

    print("\n" + "=" * 50)
    print("🎉 Teams API tests completed!")
    print(f"📝 Test team ID: {team_id}")
    print("💡 You can explore the API endpoints using this ID in the documentation")

if __name__ == "__main__":
    main()