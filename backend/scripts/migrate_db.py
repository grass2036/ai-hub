#!/usr/bin/env python3
"""
Database Migration Script
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from backend.core.database import get_sync_engine
from backend.config.settings import get_settings
import sqlite3
import sqlalchemy as sa


def run_sqlite_migration():
    """Run migration for SQLite database"""
    settings = get_settings()
    db_path = settings.database_url.replace("sqlite:///", "")

    if not os.path.exists(db_path):
        print(f"Database file does not exist: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Read and execute migration file
        migration_path = Path(__file__).parent.parent.parent / "migrations" / "003_multi_tenant_schema.sql"

        with open(migration_path, 'r') as f:
            migration_sql = f.read()

        # For SQLite, we need to modify some PostgreSQL-specific syntax
        migration_sql = migration_sql.replace("uuid_generate_v4()", "randomblob(16)")
        migration_sql = migration_sql.replace("UUID", "TEXT")
        migration_sql = migration_sql.replace("JSONB", "TEXT")
        migration_sql = migration_sql.replace("DECIMAL", "REAL")
        migration_sql = migration_sql.replace("TIMESTAMP WITH TIME ZONE", "TIMESTAMP")
        migration_sql = migration_sql.replace("NOW()", "datetime('now')")
        migration_sql = migration_sql.replace("gen_random_uuid()", "randomblob(16)")

        # Split and execute statements
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]

        for statement in statements:
            if statement:
                try:
                    cursor.execute(statement)
                    print(f"✅ Executed: {statement[:50]}...")
                except sqlite3.Error as e:
                    if "already exists" in str(e) or "duplicate column" in str(e).lower():
                        print(f"⚠️  Skipping (already exists): {statement[:50]}...")
                    else:
                        print(f"❌ Error in statement: {e}")
                        print(f"Statement: {statement[:100]}...")
                        return False

        conn.commit()
        conn.close()

        print("✅ SQLite migration completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


def run_postgresql_migration():
    """Run migration for PostgreSQL database"""
    settings = get_settings()

    try:
        engine = get_sync_engine()

        # Read migration file
        migration_path = Path(__file__).parent.parent.parent / "migrations" / "003_multi_tenant_schema.sql"

        with open(migration_path, 'r') as f:
            migration_sql = f.read()

        # Execute migration
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            try:
                conn.execute(sa.text(migration_sql))
                trans.commit()
                print("✅ PostgreSQL migration completed successfully!")
                return True
            except Exception as e:
                trans.rollback()
                print(f"❌ PostgreSQL migration failed: {e}")
                return False

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def main():
    """Main migration function"""
    settings = get_settings()

    print(f"Running migration for database: {settings.database_url}")

    if settings.database_url.startswith("sqlite"):
        success = run_sqlite_migration()
    elif settings.database_url.startswith("postgresql"):
        success = run_postgresql_migration()
    else:
        print(f"❌ Unsupported database type: {settings.database_url}")
        success = False

    if success:
        print("🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        print("💥 Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()