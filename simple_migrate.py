#!/usr/bin/env python3
"""
Simple SQLite Migration for Multi-tenant Schema
"""

import sqlite3
import os
from pathlib import Path

def main():
    """Execute multi-tenant schema migration"""
    # Database path
    db_path = "data/ai_hub.db"

    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("Creating multi-tenant tables...")

        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                avatar_url TEXT,
                settings TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create organizations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                description TEXT,
                logo_url TEXT,
                plan TEXT DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'enterprise')),
                status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
                settings TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create teams table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
                organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                description TEXT,
                parent_team_id TEXT REFERENCES teams(id) ON DELETE SET NULL,
                settings TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create members table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                team_id TEXT REFERENCES teams(id) ON DELETE SET NULL,
                role TEXT DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
                permissions TEXT DEFAULT '{}',
                invited_by TEXT REFERENCES users(id),
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, organization_id)
            )
        """)

        # Create org_api_keys table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS org_api_keys (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
                organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                key_hash TEXT UNIQUE NOT NULL,
                key_prefix TEXT NOT NULL,
                permissions TEXT DEFAULT '{}',
                rate_limit INTEGER DEFAULT 100,
                monthly_quota INTEGER DEFAULT 1000000,
                status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'revoked')),
                last_used_at TIMESTAMP,
                created_by TEXT REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)

        # Create budgets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
                organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                monthly_limit REAL NOT NULL DEFAULT 0.00,
                current_spend REAL DEFAULT 0.00,
                alert_threshold REAL DEFAULT 80.0,
                currency TEXT DEFAULT 'USD',
                status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'exceeded')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(organization_id)
            )
        """)

        # Create usage_records table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_records (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
                session_id TEXT,
                model TEXT NOT NULL,
                service TEXT NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                estimated_cost REAL DEFAULT 0.0000,
                organization_id TEXT REFERENCES organizations(id) ON DELETE SET NULL,
                team_id TEXT REFERENCES teams(id) ON DELETE SET NULL,
                user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug)",
            "CREATE INDEX IF NOT EXISTS idx_organizations_status ON organizations(status)",
            "CREATE INDEX IF NOT EXISTS idx_teams_organization_id ON teams(organization_id)",
            "CREATE INDEX IF NOT EXISTS idx_teams_parent_team_id ON teams(parent_team_id)",
            "CREATE INDEX IF NOT EXISTS idx_members_user_id ON members(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_members_organization_id ON members(organization_id)",
            "CREATE INDEX IF NOT EXISTS idx_members_team_id ON members(team_id)",
            "CREATE INDEX IF NOT EXISTS idx_members_role ON members(role)",
            "CREATE INDEX IF NOT EXISTS idx_org_api_keys_organization_id ON org_api_keys(organization_id)",
            "CREATE INDEX IF NOT EXISTS idx_org_api_keys_key_hash ON org_api_keys(key_hash)",
            "CREATE INDEX IF NOT EXISTS idx_budgets_organization_id ON budgets(organization_id)",
            "CREATE INDEX IF NOT EXISTS idx_usage_records_organization_id ON usage_records(organization_id)",
            "CREATE INDEX IF NOT EXISTS idx_usage_records_team_id ON usage_records(team_id)",
            "CREATE INDEX IF NOT EXISTS idx_usage_records_user_id ON usage_records(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_usage_records_timestamp ON usage_records(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"
        ]

        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                print(f"Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
            except sqlite3.Error as e:
                print(f"Index already exists or error: {e}")

        conn.commit()
        conn.close()

        print("Migration completed successfully!")

        # Verify tables were created
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables in database: {[table[0] for table in tables]}")
        conn.close()

        return True

    except Exception as e:
        print(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("All multi-tenant tables created successfully!")
    else:
        print("Migration failed!")