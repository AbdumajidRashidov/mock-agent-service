"""
Database utility functions for the agents service.
"""

import logging
import uuid
import datetime
from typing import Dict, List, Any, Optional
import json

from .main import get_connection

logger = logging.getLogger(__name__)


def execute_query(
    query: str, params: Optional[tuple] = None, fetch: bool = True
) -> Any:
    """
    Execute a SQL query and return the results.

    Args:
        query: SQL query to execute
        params: Query parameters
        fetch: Whether to fetch and return results

    Returns:
        Query results if fetch=True, otherwise None
    """
    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(query, params)

            if fetch:
                results = cursor.fetchall()
                connection.commit()
                return results
            else:
                connection.commit()
                return None
        except Exception as e:
            connection.rollback()
            logger.error(f"Error executing query: {e}")
            raise


def save_message(
    role: str,
    content: str,
    load_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> Dict:
    """
    Save a message to the conversation history.

    Args:
        role: Message role ('user' or 'assistant')
        content: Message content
        load_id: Optional load identifier
        thread_id: Optional thread identifier

    Returns:
        Dictionary with message details
    """
    message_id = str(uuid.uuid4())

    query = """
    INSERT INTO test_conversation_history
    (id, role, content, load_id, thread_id)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id, created_at
    """

    params = (
        message_id,
        role,
        content,
        load_id,
        thread_id,
    )

    try:
        result = execute_query(query, params, fetch=True)
        created_at = result[0][1] if result else None

        return {
            "id": message_id,
            "role": role,
            "content": content,
            "load_id": load_id,
            "thread_id": thread_id,
            "created_at": created_at,
        }
    except Exception as e:
        logger.error(f"Error saving message: {e}")
        raise


def get_conversation_history(
    load_id: Optional[str] = None, thread_id: Optional[str] = None, limit: int = 100
) -> List[Dict]:
    """
    Get conversation history from the database.

    Args:
        load_id: Optional load ID to filter by
        thread_id: Optional thread ID to filter by
        limit: Maximum number of messages to return

    Returns:
        List of conversation messages
    """
    query = "SELECT * FROM test_conversation_history WHERE 1=1"
    params = []

    if load_id:
        query += " AND load_id = %s"
        params.append(load_id)

    query += " ORDER BY created_at ASC LIMIT %s"
    params.append(limit)

    try:
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query, tuple(params))
            columns = [desc[0] for desc in cursor.description]
            results = cursor.fetchall()

            conversation_history = []
            for row in results:
                message = dict(zip(columns, row))
                # Convert datetime objects to strings to ensure JSON serialization
                for key, value in message.items():
                    if isinstance(value, datetime.datetime) or isinstance(value, datetime.date):
                        message[key] = value.isoformat()
                
                conversation_history.append(message)

            return conversation_history
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise


def format_conversation_for_llm(conversation_history: List[Dict]) -> List[Dict]:
    """
    Format conversation history for use with LLMs.

    Args:
        conversation_history: List of conversation messages

    Returns:
        List of formatted messages for LLM consumption
    """
    formatted_history = []

    for message in conversation_history:
        # Only include role and content fields to ensure compatibility with AI models
        if "role" in message and "content" in message:
            formatted_message = {"role": message["role"], "content": message["content"]}
            formatted_history.append(formatted_message)
        else:
            logger.warning(f"Skipping message with missing role or content: {message}")

    return formatted_history


def get_conversation_by_load_id(load_id: str, limit: int = 100) -> List[Dict]:
    """
    Get conversation history for a specific load ID.

    Args:
        load_id: Load ID to filter by
        limit: Maximum number of messages to return

    Returns:
        List of conversation messages
    """
    return get_conversation_history(load_id=load_id, limit=limit)
