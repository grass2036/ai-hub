#!/usr/bin/env python3
"""
Create Test Data for Multi-tenant Architecture
"""

import sqlite3
import json
import uuid
from datetime import datetime, timedelta

def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())

def main():
    """Create test data for multi-tenant tables"""
    db_path = "data/ai_hub.db"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("Creating test data for multi-tenant architecture...")

        # Create test users
        users = [
            {
                'id': generate_uuid(),
                'email': 'john.doe@company.com',
                'name': 'John Doe',
                'avatar_url': 'https://example.com/avatars/john.jpg',
                'settings': json.dumps({'theme': 'dark', 'language': 'en'})
            },
            {
                'id': generate_uuid(),
                'email': 'jane.smith@company.com',
                'name': 'Jane Smith',
                'avatar_url': 'https://example.com/avatars/jane.jpg',
                'settings': json.dumps({'theme': 'light', 'language': 'en'})
            },
            {
                'id': generate_uuid(),
                'email': 'bob.wilson@startup.io',
                'name': 'Bob Wilson',
                'avatar_url': 'https://example.com/avatars/bob.jpg',
                'settings': json.dumps({'theme': 'dark', 'language': 'en'})
            },
            {
                'id': generate_uuid(),
                'email': 'alice.chen@techcorp.com',
                'name': 'Alice Chen',
                'avatar_url': 'https://example.com/avatars/alice.jpg',
                'settings': json.dumps({'theme': 'light', 'language': 'zh'})
            }
        ]

        for user in users:
            cursor.execute("""
                INSERT OR IGNORE INTO users (id, email, name, avatar_url, settings)
                VALUES (?, ?, ?, ?, ?)
            """, (user['id'], user['email'], user['name'], user['avatar_url'], user['settings']))

        print(f"Created {len(users)} test users")

        # Create test organizations
        organizations = [
            {
                'id': generate_uuid(),
                'name': 'TechCorp Inc.',
                'slug': 'techcorp-inc',
                'description': 'Leading technology company specializing in AI solutions',
                'logo_url': 'https://example.com/logos/techcorp.png',
                'plan': 'enterprise',
                'status': 'active',
                'settings': json.dumps({'max_users': 1000, 'features': ['api-access', 'priority-support']})
            },
            {
                'id': generate_uuid(),
                'name': 'StartupIO',
                'slug': 'startupio',
                'description': 'Innovative startup building next-gen products',
                'logo_url': 'https://example.com/logos/startupio.png',
                'plan': 'pro',
                'status': 'active',
                'settings': json.dumps({'max_users': 50, 'features': ['api-access']})
            },
            {
                'id': generate_uuid(),
                'name': 'Digital Agency Ltd',
                'slug': 'digital-agency',
                'description': 'Full-service digital marketing agency',
                'logo_url': 'https://example.com/logos/digital-agency.png',
                'plan': 'free',
                'status': 'active',
                'settings': json.dumps({'max_users': 10, 'features': ['basic']})
            }
        ]

        for org in organizations:
            cursor.execute("""
                INSERT OR IGNORE INTO organizations (id, name, slug, description, logo_url, plan, status, settings)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (org['id'], org['name'], org['slug'], org['description'], org['logo_url'],
                  org['plan'], org['status'], org['settings']))

        print(f"Created {len(organizations)} test organizations")

        # Create test teams
        teams = []
        engineering_team_id = generate_uuid()
        frontend_team_id = generate_uuid()
        backend_team_id = generate_uuid()
        product_team_id = generate_uuid()

        teams = [
            {
                'id': engineering_team_id,
                'organization_id': organizations[0]['id'],  # TechCorp
                'name': 'Engineering Team',
                'description': 'Core engineering and development team',
                'parent_team_id': None,
                'settings': json.dumps({'max_members': 20, 'specialization': 'full-stack'})
            },
            {
                'id': frontend_team_id,
                'organization_id': organizations[0]['id'],  # TechCorp
                'name': 'Frontend Squad',
                'description': 'Frontend development specialists',
                'parent_team_id': engineering_team_id,  # Sub-team of Engineering
                'settings': json.dumps({'max_members': 8, 'specialization': 'frontend'})
            },
            {
                'id': backend_team_id,
                'organization_id': organizations[0]['id'],  # TechCorp
                'name': 'Backend Squad',
                'description': 'Backend development specialists',
                'parent_team_id': engineering_team_id,  # Sub-team of Engineering
                'settings': json.dumps({'max_members': 8, 'specialization': 'backend'})
            },
            {
                'id': product_team_id,
                'organization_id': organizations[1]['id'],  # StartupIO
                'name': 'Product Team',
                'description': 'Product development and management',
                'parent_team_id': None,
                'settings': json.dumps({'max_members': 10, 'specialization': 'product'})
            }
        ]

        for team in teams:
            cursor.execute("""
                INSERT OR IGNORE INTO teams (id, organization_id, name, description, parent_team_id, settings)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (team['id'], team['organization_id'], team['name'], team['description'],
                  team['parent_team_id'], team['settings']))

        print(f"Created {len(teams)} test teams")

        # Create test members
        members = [
            {
                'id': generate_uuid(),
                'user_id': users[0]['id'],  # John Doe
                'organization_id': organizations[0]['id'],  # TechCorp
                'team_id': teams[0]['id'],  # Engineering Team
                'role': 'owner',
                'permissions': json.dumps({'all': True}),
                'invited_by': users[0]['id']
            },
            {
                'id': generate_uuid(),
                'user_id': users[1]['id'],  # Jane Smith
                'organization_id': organizations[0]['id'],  # TechCorp
                'team_id': teams[1]['id'],  # Frontend Squad
                'role': 'admin',
                'permissions': json.dumps({'teams': ['read', 'write'], 'members': ['read', 'write']}),
                'invited_by': users[0]['id']
            },
            {
                'id': generate_uuid(),
                'user_id': users[2]['id'],  # Bob Wilson
                'organization_id': organizations[1]['id'],  # StartupIO
                'team_id': teams[3]['id'],  # Product Team
                'role': 'owner',
                'permissions': json.dumps({'all': True}),
                'invited_by': users[2]['id']
            },
            {
                'id': generate_uuid(),
                'user_id': users[3]['id'],  # Alice Chen
                'organization_id': organizations[0]['id'],  # TechCorp
                'team_id': teams[2]['id'],  # Backend Squad
                'role': 'member',
                'permissions': json.dumps({'basic': True}),
                'invited_by': users[0]['id']
            }
        ]

        for member in members:
            cursor.execute("""
                INSERT OR IGNORE INTO members (id, user_id, organization_id, team_id, role, permissions, invited_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (member['id'], member['user_id'], member['organization_id'], member['team_id'],
                  member['role'], member['permissions'], member['invited_by']))

        print(f"Created {len(members)} test members")

        # Create test budgets
        budgets = [
            {
                'id': generate_uuid(),
                'organization_id': organizations[0]['id'],  # TechCorp
                'monthly_limit': 5000.00,
                'current_spend': 1234.56,
                'alert_threshold': 80.0,
                'currency': 'USD',
                'status': 'active'
            },
            {
                'id': generate_uuid(),
                'organization_id': organizations[1]['id'],  # StartupIO
                'monthly_limit': 1000.00,
                'current_spend': 456.78,
                'alert_threshold': 75.0,
                'currency': 'USD',
                'status': 'active'
            },
            {
                'id': generate_uuid(),
                'organization_id': organizations[2]['id'],  # Digital Agency
                'monthly_limit': 100.00,
                'current_spend': 23.45,
                'alert_threshold': 90.0,
                'currency': 'USD',
                'status': 'active'
            }
        ]

        for budget in budgets:
            cursor.execute("""
                INSERT OR IGNORE INTO budgets (id, organization_id, monthly_limit, current_spend, alert_threshold, currency, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (budget['id'], budget['organization_id'], budget['monthly_limit'], budget['current_spend'],
                  budget['alert_threshold'], budget['currency'], budget['status']))

        print(f"Created {len(budgets)} test budgets")

        # Create test organization API keys
        api_keys = [
            {
                'id': generate_uuid(),
                'organization_id': organizations[0]['id'],  # TechCorp
                'name': 'Production API Key',
                'key_hash': 'hash1234567890abcdef',
                'key_prefix': 'org_prod_12',
                'permissions': json.dumps({'models': ['gpt-4', 'claude-3'], 'endpoints': ['chat', 'completion']}),
                'rate_limit': 1000,
                'monthly_quota': 10000000,
                'status': 'active',
                'created_by': users[0]['id']
            },
            {
                'id': generate_uuid(),
                'organization_id': organizations[1]['id'],  # StartupIO
                'name': 'Development API Key',
                'key_hash': 'hashabcdef1234567890',
                'key_prefix': 'org_dev_ab',
                'permissions': json.dumps({'models': ['gpt-3.5'], 'endpoints': ['chat']}),
                'rate_limit': 100,
                'monthly_quota': 1000000,
                'status': 'active',
                'created_by': users[2]['id']
            }
        ]

        for api_key in api_keys:
            cursor.execute("""
                INSERT OR IGNORE INTO org_api_keys (id, organization_id, name, key_hash, key_prefix, permissions, rate_limit, monthly_quota, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (api_key['id'], api_key['organization_id'], api_key['name'], api_key['key_hash'],
                  api_key['key_prefix'], api_key['permissions'], api_key['rate_limit'], api_key['monthly_quota'],
                  api_key['status'], api_key['created_by']))

        print(f"Created {len(api_keys)} test API keys")

        # Create test usage records
        usage_records = []
        base_time = datetime.utcnow() - timedelta(days=30)

        for i in range(100):  # Create 100 usage records over the last 30 days
            record = {
                'id': generate_uuid(),
                'session_id': f'session_{i % 10}',
                'model': ['gpt-4', 'gpt-3.5', 'claude-3'][i % 3],
                'service': ['openrouter', 'openai'][i % 2],
                'prompt_tokens': 100 + (i * 10),
                'completion_tokens': 50 + (i * 5),
                'total_tokens': 150 + (i * 15),
                'estimated_cost': round((150 + i * 15) * 0.00001, 4),
                'organization_id': organizations[i % 3]['id'],
                'team_id': teams[i % len(teams)]['id'] if i % 2 != 0 else None,
                'user_id': users[i % len(users)]['id'],
                'timestamp': (base_time + timedelta(hours=i * 7)).isoformat()
            }
            usage_records.append(record)

        for record in usage_records:
            cursor.execute("""
                INSERT OR IGNORE INTO usage_records (id, session_id, model, service, prompt_tokens, completion_tokens, total_tokens, estimated_cost, organization_id, team_id, user_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (record['id'], record['session_id'], record['model'], record['service'],
                  record['prompt_tokens'], record['completion_tokens'], record['total_tokens'],
                  record['estimated_cost'], record['organization_id'], record['team_id'],
                  record['user_id'], record['timestamp']))

        print(f"Created {len(usage_records)} test usage records")

        conn.commit()
        conn.close()

        print("\nTest data creation completed successfully!")
        print("\nSummary:")
        print(f"- Users: {len(users)}")
        print(f"- Organizations: {len(organizations)}")
        print(f"- Teams: {len(teams)}")
        print(f"- Members: {len(members)}")
        print(f"- Budgets: {len(budgets)}")
        print(f"- API Keys: {len(api_keys)}")
        print(f"- Usage Records: {len(usage_records)}")

        return True

    except Exception as e:
        print(f"Test data creation failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\nAll test data created successfully!")
    else:
        print("\nTest data creation failed!")