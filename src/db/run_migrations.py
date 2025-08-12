"""
Script to run database migrations for the agents service.
"""

import os
import sys
import logging
import importlib.util
from dotenv import load_dotenv

# Add the src directory to Python path
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.insert(0, src_dir)

load_dotenv()

from db.main import get_connection

# Import the migration module dynamically
migration_path = os.path.join(
    os.path.dirname(__file__), "migrations/001_create_initial_tables.py"
)
spec = importlib.util.spec_from_file_location("migration_001", migration_path)
migration_001 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration_001)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migrations():
    """Run all database migrations in order."""
    logger.info("Running database migrations...")

    # Check if migrations table exists
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS migrations (
                    id VARCHAR PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """
            )
            conn.commit()

    # Check if migration 001 has been run
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM migrations WHERE id = '001_create_initial_tables'"
            )
            result = cursor.fetchone()

            if not result:
                logger.info("Running migration: 001_create_initial_tables")
                migration_001.up(cursor)
                cursor.execute(
                    "INSERT INTO migrations (id, created_at) VALUES ('001_create_initial_tables', NOW())"
                )
                conn.commit()
                logger.info(
                    "Migration 001_create_initial_tables completed successfully"
                )
            else:
                logger.info("Migration 001_create_initial_tables already applied")


if __name__ == "__main__":
    run_migrations()
