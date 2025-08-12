import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def run_migration():
    """
    Run the migration to create the test_conversation_history table.
    """
    # Get database connection parameters from environment variables
    db_host = os.getenv("POSTGRES_HOST")
    db_port = os.getenv("POSTGRES_PORT")
    db_name = os.getenv("POSTGRES_DB")
    db_user = os.getenv("POSTGRES_USER")
    db_password = os.getenv("POSTGRES_PASSWORD")

    if not db_host or not db_port or not db_name or not db_user or not db_password:
        raise ValueError("Missing required database connection parameters")

    # Connect to the database
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password
    )
    conn.autocommit = True

    try:
        # Create a cursor
        cursor = conn.cursor()

        # Create test_conversation_history table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS test_conversation_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            role VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            load_id VARCHAR(255),
            thread_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_test_conversation_history_load_id ON test_conversation_history(load_id);
        CREATE INDEX IF NOT EXISTS idx_test_conversation_history_thread_id ON test_conversation_history(thread_id);
        """
        )

        print("Migration completed successfully: Created test_conversation_history table")

    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        # Close the cursor and connection
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
