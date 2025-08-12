"""Common fixtures for integration tests.

This module contains fixtures that are shared across multiple test files.
"""

import pytest

@pytest.fixture
def in_memory_conversation(monkeypatch):
    """Fixture that provides an in-memory conversation store for testing."""
    # Simple list to store messages
    memory = []

    #  mock db save function
    def fake_save_message(role, content, load_id=None, thread_id=None):
        print(f"Saving message: role={role}, thread_id={thread_id}")
        message = {
            "role": role,
            "content": content,
            "thread_id": thread_id or "1234567890"  # Default thread_id if none provided
        }
        memory.append(message)
        return {"success": True, "id": "test-message-id"}

    def fake_get_conversation_history(thread_id):
        print(f"Getting conversation history for thread_id={thread_id}")
        return [msg for msg in memory if msg["thread_id"] == thread_id]

    def fake_format_conversation_for_llm(conversation):
        return [{"role": msg["role"], "content": msg["content"]} for msg in conversation]

    # Import the orchestrator module where these functions are used
    from workflows.load_reply_processsor import orchestrator

    # Replace the functions in the orchestrator module directly
    monkeypatch.setattr(orchestrator, "save_message", fake_save_message)
    monkeypatch.setattr(orchestrator, "get_conversation_history", fake_get_conversation_history)
    monkeypatch.setattr(orchestrator, "format_conversation_for_llm", fake_format_conversation_for_llm)

    print("Successfully mocked database functions")

    return memory
