"""
Initial migration to create the basic tables for the agents service.
"""


def up(cursor):
    """
    Create initial tables for the agents service.

    Args:
        cursor: Database cursor for executing SQL commands
    """
    # Create load_replies table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS load_replies (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        thread_id VARCHAR(255) NOT NULL,
        email_id VARCHAR(255) NOT NULL,
        subject VARCHAR(255),
        sender VARCHAR(255) NOT NULL,
        recipient VARCHAR(255) NOT NULL,
        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        processed_at TIMESTAMP,
        content TEXT NOT NULL,
        is_processed BOOLEAN DEFAULT FALSE,
        processing_status VARCHAR(50) DEFAULT 'pending'
    );
    CREATE INDEX IF NOT EXISTS idx_load_replies_thread_id ON load_replies(thread_id);
    CREATE INDEX IF NOT EXISTS idx_load_replies_email_id ON load_replies(email_id);
    """
    )

    # Create warnings table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS warnings (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        load_reply_id UUID REFERENCES load_replies(id),
        warning_type VARCHAR(50) NOT NULL,
        description TEXT NOT NULL,
        severity VARCHAR(50) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metadata JSONB
    );
    CREATE INDEX IF NOT EXISTS idx_warnings_load_reply_id ON warnings(load_reply_id);
    """
    )

    # Create rates table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS rates (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        load_reply_id UUID REFERENCES load_replies(id),
        rate_per_mile DECIMAL(10, 2) NOT NULL,
        total_rate DECIMAL(10, 2) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metadata JSONB
    );
    CREATE INDEX IF NOT EXISTS idx_rates_load_reply_id ON rates(load_reply_id);
    """
    )

    # Create load_details table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS load_details (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        load_reply_id UUID REFERENCES load_replies(id),
        origin VARCHAR(255) NOT NULL,
        destination VARCHAR(255) NOT NULL,
        distance DECIMAL(10, 2),
        weight DECIMAL(10, 2),
        dimensions VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metadata JSONB
    );
    CREATE INDEX IF NOT EXISTS idx_load_details_load_reply_id ON load_details(load_reply_id);
    """
    )

    # Create conversation_history table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS conversation_history (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        role VARCHAR(50) NOT NULL,
        content TEXT NOT NULL,
        load_id VARCHAR(255),
        thread_id VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_conversation_history_load_id ON conversation_history(load_id);
    CREATE INDEX IF NOT EXISTS idx_conversation_history_thread_id ON conversation_history(thread_id);
    """
    )
