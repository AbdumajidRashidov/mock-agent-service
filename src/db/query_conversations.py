"""
Script to query conversation history from the database.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the src directory to Python path
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.insert(0, src_dir)

load_dotenv()

from db.main import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def query_conversations(limit=5):
    """Query the most recent conversations from the database."""
    logger.info(f"Querying the {limit} most recent conversation messages...")

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, role, content, load_id, thread_id, created_at 
                FROM conversation_history 
                ORDER BY created_at DESC 
                LIMIT %s
            """,
                (limit,),
            )

            rows = cursor.fetchall()

            if not rows:
                logger.info("No conversation messages found in the database.")
                return

            logger.info(f"Found {len(rows)} conversation messages:")
            for row in rows:
                id, role, content, load_id, thread_id, created_at = row
                print(f"\nID: {id}")
                print(f"Role: {role}")
                print(f"Content: {content[:100]}{'...' if len(content) > 100 else ''}")
                print(f"Load ID: {load_id}")
                print(f"Thread ID: {thread_id}")
                print(f"Created At: {created_at}")
                print("-" * 50)


if __name__ == "__main__":
    query_conversations()
