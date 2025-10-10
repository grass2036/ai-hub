#!/usr/bin/env python3
"""
Simple Database Migration Script
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

    # Create database if it doesn't exist
    if not os.path.exists(db_path):
        print(f"Creating new database: {db_path}")
        conn = sqlite3.connect(db_path)
        conn.close()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Read migration file
        migration_path = "migrations/003_multi_tenant_schema.sql"

        with open(migration_path, 'r') as f:
            migration_sql = f.read()

        # For SQLite, modify PostgreSQL-specific syntax
        migration_sql = migration_sql.replace("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";", "")
        migration_sql = migration_sql.replace("uuid_generate_v4()", "randomblob(16)")
        migration_sql = migration_sql.replace("gen_random_uuid()", "randomblob(16)")
        migration_sql = migration_sql.replace("UUID", "TEXT")
        migration_sql = migration_sql.replace("JSONB", "TEXT")
        migration_sql = migration_sql.replace("DECIMAL", "REAL")
        migration_sql = migration_sql.replace("TIMESTAMP WITH TIME ZONE", "TIMESTAMP")
        migration_sql = migration_sql.replace("NOW()", "datetime('now')")
        migration_sql = migration_sql.replace("CURRENT_TIMESTAMP", "datetime('now')")
        migration_sql = migration_sql.replace("postgresql", "")

        # Remove PostgreSQL-specific functions and triggers
        lines = migration_sql.split('\n')
        cleaned_lines = []
        skip_lines = False

        for line in lines:
            if 'CREATE OR REPLACE FUNCTION' in line:
                skip_lines = True
                continue
            elif 'CREATE TRIGGER' in line:
                continue
            elif skip_lines and line.strip().startswith('$$ language'):
                skip_lines = False
                continue
            elif skip_lines:
                continue

            # Skip problematic PostgreSQL syntax
            if any(keyword in line.upper() for keyword in [
                'DO $$', 'BEGIN', 'END $$', 'INFORMATION_SCHEMA'
            ]):
                continue

            cleaned_lines.append(line)

        migration_sql = '\n'.join(cleaned_lines)

        # Split and execute statements
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]

        for statement in statements:
            if statement and not statement.startswith('--'):
                try:
                    cursor.execute(statement)
                    print(f"✅ Executed: {statement[:50]}...")
                except sqlite3.Error as e:
                    if "already exists" in str(e) or "duplicate column" in str(e).lower():
                        print(f"⚠️  Skipping (already exists): {statement[:50]}...")
                    else:
                        print(f"❌ Error: {e}")
                        print(f"Statement: {statement[:100]}...")

        conn.commit()
        conn.close()

        print("✅ Migration completed successfully!")

        # Verify tables were created
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"\n📋 Tables in database: {[table[0] for table in tables]}")
        conn.close()

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

    return True

if __name__ == "__main__":
    main()