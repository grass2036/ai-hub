#!/usr/bin/env python3
"""
Simple Database Verification
"""

import sqlite3

def main():
    """Verify database schema and test data"""
    db_path = "data/ai_hub.db"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("=== Multi-tenant Database Verification ===")
        print()

        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]

        print("Tables created:")
        for table in sorted(tables):
            print(f"  - {table}")

        print()
        print("=== Table Contents ===")
        print()

        # Check data counts
        counts = {}
        for table in ['users', 'organizations', 'teams', 'members', 'budgets', 'org_api_keys', 'usage_records']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            counts[table] = count
            print(f"{table}: {count} records")

        print()
        print("=== Sample Data ===")
        print()

        # Organizations
        cursor.execute("SELECT id, name, slug, plan FROM organizations")
        orgs = cursor.fetchall()
        print("Organizations:")
        for org in orgs:
            print(f"  {org[1]} ({org[2]}) - {org[3]}")

        # Teams
        cursor.execute("SELECT name, organization_id FROM teams")
        teams = cursor.fetchall()
        print()
        print("Teams:")
        for team in teams:
            print(f"  {team[0]}")

        # Members
        cursor.execute("SELECT role, COUNT(*) FROM members GROUP BY role")
        members = cursor.fetchall()
        print()
        print("Members by role:")
        for role, count in members:
            print(f"  {role}: {count}")

        # Budgets
        cursor.execute("SELECT monthly_limit, current_spend FROM budgets")
        budgets = cursor.fetchall()
        print()
        print("Budgets:")
        for budget in budgets:
            usage_pct = (budget[1] / budget[0] * 100) if budget[0] > 0 else 0
            print(f"  Limit: ${budget[0]:.2f}, Spent: ${budget[1]:.2f} ({usage_pct:.1f}%)")

        print()
        print("=== Verification Summary ===")
        print(f"Total tables: {len(tables)}")
        print(f"Users: {counts['users']}")
        print(f"Organizations: {counts['organizations']}")
        print(f"Teams: {counts['teams']}")
        print(f"Members: {counts['members']}")
        print(f"Budgets: {counts['budgets']}")
        print(f"API Keys: {counts['org_api_keys']}")
        print(f"Usage Records: {counts['usage_records']}")

        conn.close()
        print()
        print("Multi-tenant schema verification completed successfully!")

        return True

    except Exception as e:
        print(f"Verification failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print()
        print("All verifications passed! Multi-tenant architecture is ready.")
    else:
        print()
        print("Verification failed!")