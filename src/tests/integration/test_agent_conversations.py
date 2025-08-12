"""Integration tests for the AI agents in the load reply processor workflow.

This module contains tests for the conversation flow with different types of emails,
verifying that the appropriate agent is triggered based on the email content:

1. info_master - Responds to questions about company information
2. load_scan - Extracts structured data from unstructured text
3. warnings_ai - Identifies warnings based on truck attributes and load details
4. rate_negotiator - Calculates rates based on thresholds and applies rounding rules
"""

import pytest
import sys
import os
from unittest.mock import patch, AsyncMock, MagicMock

# Add the parent directories to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Import test data and mocks
from src.tests.integration.data import emails
from workflows.load_reply_processsor.orchestrator import run_load_reply_processsor
from workflows.load_reply_processsor.sub_agents import load_scan, warnings_ai, rate_negotiator


# in_memory_conversation fixture is now imported from conftest.py
@pytest.fixture
def mock_update_load_reply_status(monkeypatch):
    """Mock the update_load_reply_status function to prevent actual API calls."""
    # Create a mock function that captures the arguments
    captured_args = []

    async def mock_func(load_id, application_name=None, details=None):
        print(f"\nMock update_load_reply_status called with:")
        print(f"  load_id: {load_id}")
        print(f"  application_name: {application_name}")
        print(f"  details: {details}")

        captured_args.append({
            "load_id": load_id,
            "application_name": application_name,
            "details": details
        })

        return {
            "success": True,
            "status_code": 200,
            "data": {"id": load_id},
            "message": "Status updated successfully"
        }

    # Replace the real function with our mock
    monkeypatch.setattr(load_scan, "update_load_reply_status", mock_func)

    return captured_args


@pytest.fixture
def mock_upsert_load_warnings(monkeypatch):
    """Mock the upsert_load_warnings function to prevent actual API calls."""
    # Create a mock function that captures the arguments
    captured_args = []

    def mock_func(load_id, warnings, application_name):
        print(f"\nMock upsert_load_warnings called with:")
        print(f"  load_id: {load_id}")
        print(f"  warnings: {warnings}")
        print(f"  application_name: {application_name}")

        captured_args.append({
            "load_id": load_id,
            "warnings": warnings,
            "application_name": application_name
        })

        return {
            "success": True,
            "status_code": 200,
            "data": {"id": load_id, "warnings": warnings},
            "message": "Warnings updated successfully"
        }

    # Replace the real function with our mock
    monkeypatch.setattr(warnings_ai, "upsert_load_warnings", mock_func)

    return captured_args


@pytest.fixture
def mock_send_draft(monkeypatch):
    """Mock the send_draft function to prevent actual API calls."""
    # Create a mock function that captures the arguments
    captured_args = []

    async def mock_func(project_name, load_id, email_body, email_subject, thread_id, draft):
        print(f"\nMock send_draft called with:")
        print(f"  project_name: {project_name}")
        print(f"  load_id: {load_id}")
        print(f"  email_subject: {email_subject}")
        print(f"  thread_id: {thread_id}")
        print(f"  draft length: {len(draft) if draft else 0}")

        captured_args.append({
            "project_name": project_name,
            "load_id": load_id,
            "email_body": email_body,
            "email_subject": email_subject,
            "thread_id": thread_id,
            "draft": draft
        })

        return {
            "success": True,
            "status_code": 200,
            "data": {
                "id": "mock-draft-id",
                "threadId": thread_id,
                "loadId": load_id
            },
            "message": "Draft successfully sent"
        }

    # Replace the real function with our mock
    monkeypatch.setattr(rate_negotiator, "send_draft", mock_func)

    return captured_args


@pytest.fixture
def mock_send_reply(monkeypatch):
    """Mock the send_reply function to prevent actual API calls."""
    # Create a mock function that captures the arguments
    captured_args = []

    async def mock_func(body, subject, thread_id, email_id, project_name):
        print(f"\nMock send_reply called with:")
        print(f"  body: {body[:100]}..." if body and len(body) > 100 else f"  body: {body}")
        print(f"  subject: {subject}")
        print(f"  thread_id: {thread_id}")
        print(f"  email_id: {email_id}")
        print(f"  project_name: {project_name}")

        captured_args.append({
            "body": body,
            "subject": subject,
            "thread_id": thread_id,
            "email_id": email_id,
            "project_name": project_name
        })

        return {
            "success": True,
            "status_code": 200,
            "data": {
                "id": "mock-reply-id",
                "threadId": thread_id,
                "emailId": email_id
            },
            "message": "Reply successfully sent"
        }

    # Replace the real send_reply function with our mock version
    monkeypatch.setattr("workflows.load_reply_processsor.sub_agents.info_master.send_reply", mock_func)

    return captured_args


# ============================
# INFO MASTER AGENT TESTS
# ============================

@pytest.mark.asyncio
async def test_info_master_agent(in_memory_conversation, mock_send_reply, mock_update_load_reply_status, mock_upsert_load_warnings, mock_send_draft):
    """Test that the info_master agent correctly responds to questions about company information."""
    # Use the MC number inquiry email (Scenario 0)
    test_email = emails[0]  # "What is your MC number?"

    # Run the load reply processor with the test email
    await run_load_reply_processsor(test_email)

    # Verify that the conversation has been updated with the user's message and the agent's response
    assert len(in_memory_conversation) >= 2, "There should be at least 2 messages in the conversation"

    # The first message should be the user's question
    assert in_memory_conversation[0]["role"] == "user", "First message should be from the user"
    assert in_memory_conversation[0]["thread_id"] == test_email.thread_id, "Thread ID should match"

    # The second message should be the agent's response containing the MC number
    assert in_memory_conversation[1]["role"] == "assistant", "Second message should be from the assistant"
    assert test_email.company_details.mc_number in in_memory_conversation[1]["content"], "Response should contain the MC number"

    # Verify that the send_reply function was called
    assert len(mock_send_reply) > 0, "send_reply was not called"

    # Verify that the update_load_reply_status, upsert_load_warnings, and send_draft functions were NOT called
    # since this is an info_master query, not a load scan, warnings, or rate negotiation
    assert len(mock_update_load_reply_status) == 0, "update_load_reply_status should not be called for info_master queries"
    assert len(mock_upsert_load_warnings) == 0, "upsert_load_warnings should not be called for info_master queries"
    assert len(mock_send_draft) == 0, "send_draft should not be called for info_master queries"

    print("\nu2705 info_master agent correctly responded to the MC number inquiry")


# ============================
# LOAD SCAN AGENT TESTS
# ============================

@pytest.mark.asyncio
async def test_load_scan_agent(in_memory_conversation, mock_send_reply, mock_update_load_reply_status, mock_upsert_load_warnings, mock_send_draft):
    """Test that the load_scan agent correctly extracts load details from the email."""
    # Clear the conversation from previous tests
    in_memory_conversation.clear()

    # Import the predefined load_scan_test_email from data.py
    from src.tests.integration.data import load_scan_test_email

    # Use the predefined test email
    test_email = load_scan_test_email

    # Run the load reply processor with the test email
    await run_load_reply_processsor(test_email)

    # Verify that the conversation has been updated with the user's message and the agent's response
    assert len(in_memory_conversation) >= 2, "There should be at least 2 messages in the conversation"

    # The first message should be the user's message with load details
    assert in_memory_conversation[0]["role"] == "user", "First message should be from the user"
    assert in_memory_conversation[0]["thread_id"] == test_email.thread_id, "Thread ID should match"

    # Verify that the update_load_reply_status function was called
    assert len(mock_update_load_reply_status) > 0, "update_load_reply_status was not called"

    # Get the arguments passed to update_load_reply_status
    update_args = mock_update_load_reply_status[0]

    # Verify that the load_id was passed correctly
    assert update_args["load_id"] == test_email.load_id, "update_load_reply_status was not called with the correct load_id"

    print("\nu2705 load_scan agent correctly extracted load details from the email")


# ============================
# WARNINGS AI AGENT TESTS
# ============================

@pytest.mark.asyncio
async def test_warnings_ai_agent(in_memory_conversation, mock_send_reply, mock_update_load_reply_status, mock_upsert_load_warnings, mock_send_draft):
    """Test that the warnings_ai agent correctly identifies warnings based on truck attributes and load details."""
    # Clear the conversation from previous tests
    in_memory_conversation.clear()

    # Import the predefined warnings_test_email from data.py
    from src.tests.integration.data import warnings_test_email

    # Use the predefined test email
    test_email = warnings_test_email

    # Update the email body to include explicit mention of alcohol
    test_email.reply_email.body = """<p>Can you handle this alcohol shipment? It requires hazmat certification.</p>"""

    # Run the load reply processor with the test email
    await run_load_reply_processsor(test_email)

    # Verify that the conversation has been updated with the user's message and the agent's response
    assert len(in_memory_conversation) >= 2, "There should be at least 2 messages in the conversation"

    # The first message should be the user's message about alcohol shipment
    assert in_memory_conversation[0]["role"] == "user", "First message should be from the user"
    assert in_memory_conversation[0]["thread_id"] == test_email.thread_id, "Thread ID should match"

    # No need to restore anything since we created a custom test email

    # Verify that the upsert_load_warnings function was called
    assert len(mock_upsert_load_warnings) > 0, "upsert_load_warnings was not called"

    # Get the arguments passed to upsert_load_warnings
    warnings_args = mock_upsert_load_warnings[0]

    # Verify that the load_id was passed correctly
    assert warnings_args["load_id"] == test_email.load_id, "upsert_load_warnings was not called with the correct load_id"

    # Verify that the warnings list was passed
    assert "warnings" in warnings_args, "upsert_load_warnings was not called with 'warnings' argument"
    assert isinstance(warnings_args["warnings"], list), "'warnings' argument is not a list"

    print("\nu2705 warnings_ai agent correctly identified warnings based on truck attributes and load details")


# ============================
# RATE NEGOTIATOR AGENT TESTS
# ============================

@pytest.mark.asyncio
async def test_rate_negotiator_agent(in_memory_conversation, mock_send_reply, mock_update_load_reply_status, mock_upsert_load_warnings, mock_send_draft):
    """Test that the rate_negotiator agent correctly calculates rates and generates a negotiation response."""
    # Clear the conversation from previous tests
    in_memory_conversation.clear()

    # Import the predefined rate_negotiator_test_email from data.py
    from src.tests.integration.data import rate_negotiator_test_email

    # Use the predefined test email
    test_email = rate_negotiator_test_email

    # Update the email body to include an explicit rate offer
    test_email.reply_email.body = """<p>We can offer $4,000 for this load.</p>"""

    # Set up the rate negotiation parameters
    test_email.company_details.rate_negotiation.first_bid_threshold = 70  # 70%
    test_email.company_details.rate_negotiation.second_bid_threshold = 40  # 40%
    test_email.company_details.rate_negotiation.min_gap = 0

    # Set the min/max rates
    test_email.load.rate_info.minimum_rate = 3000
    test_email.load.rate_info.maximum_rate = 5000
    test_email.load.rate_info.rate_usd = 5000

    # Run the load reply processor with the test email
    await run_load_reply_processsor(test_email)

    # Verify that the conversation has been updated with the user's message and the agent's response
    assert len(in_memory_conversation) >= 2, "There should be at least 2 messages in the conversation"

    # The first message should be the user's message with rate offer
    assert in_memory_conversation[0]["role"] == "user", "First message should be from the user"
    assert in_memory_conversation[0]["thread_id"] == test_email.thread_id, "Thread ID should match"

    # Verify that the send_draft function was called
    assert len(mock_send_draft) > 0, "send_draft was not called"

    # Get the arguments passed to send_draft
    draft_args = mock_send_draft[0]

    # Verify that the load_id was passed correctly
    assert draft_args["load_id"] == test_email.load_id, "send_draft was not called with the correct load_id"

    # Verify that the draft was included
    assert "draft" in draft_args, "send_draft was not called with 'draft' argument"
    assert isinstance(draft_args["draft"], str), "'draft' argument is not a string"
    assert len(draft_args["draft"]) > 0, "'draft' argument is empty"

    print("\nu2705 rate_negotiator agent correctly generated a negotiation response")


# ============================
# FULL CONVERSATION FLOW TEST
# ============================

@pytest.mark.asyncio
async def test_full_conversation_flow(in_memory_conversation, mock_send_reply, mock_update_load_reply_status, mock_upsert_load_warnings, mock_send_draft):
    """Test the full conversation flow with multiple emails triggering different agents."""
    # Clear the conversation from previous tests
    in_memory_conversation.clear()

    # 1. Start with the MC number inquiry (info_master)
    print("\n1. Testing info_master agent with MC number inquiry")
    await run_load_reply_processsor(emails[0])

    # Verify that the conversation has the user's question and the agent's response
    assert len(in_memory_conversation) == 2, "There should be 2 messages in the conversation after the first email"
    assert emails[0].company_details.mc_number in in_memory_conversation[1]["content"], "Response should contain the MC number"

    # 2. Continue with load details (load_scan)
    print("\n2. Testing load_scan agent with load details")
    # Update the email body to include explicit load details
    emails[1].reply_email.body = """<p>Rate: $2,000, Commodity: General Freight, Weight: 45,000 lbs, Equipment: DRY_VAN,
    Pickup Location: New York, NY, Delivery Location: Boston, MA</p>"""
    await run_load_reply_processsor(emails[1])

    # Verify that the conversation has been updated with the user's message and the agent's response
    assert len(in_memory_conversation) == 4, "There should be 4 messages in the conversation after the second email"
    assert len(mock_update_load_reply_status) > 0, "update_load_reply_status should be called for load_scan queries"

    # 3. Continue with hazmat load (warnings_ai)
    print("\n3. Testing warnings_ai agent with hazmat load")

    # Import the predefined warnings_test_email from data.py
    from src.tests.integration.data import warnings_test_email

    # Run the processor with our predefined test email
    await run_load_reply_processsor(warnings_test_email)

    # Verify that the conversation has been updated with the user's message and the agent's response
    assert len(in_memory_conversation) == 6, "There should be 6 messages in the conversation after the third email"
    assert len(mock_upsert_load_warnings) > 0, "upsert_load_warnings should be called for warnings_ai queries"

    # 4. Finish with rate offer (rate_negotiator)
    print("\n4. Testing rate_negotiator agent with rate offer")
    # Update the email body to include an explicit rate offer
    emails[3].reply_email.body = """<p>We can offer $4,000 for this load.</p>"""
    # Set up the rate negotiation parameters
    emails[3].company_details.rate_negotiation.first_bid_threshold = 70  # 70%
    emails[3].company_details.rate_negotiation.second_bid_threshold = 40  # 40%
    emails[3].company_details.rate_negotiation.min_gap = 0
    # Set the min/max rates
    emails[3].load.rate_info.minimum_rate = 3000
    emails[3].load.rate_info.maximum_rate = 5000
    emails[3].load.rate_info.rate_usd = 5000
    await run_load_reply_processsor(emails[3])

    # Verify that the conversation has been updated with the user's message and the agent's response
    assert len(in_memory_conversation) == 8, "There should be 8 messages in the conversation after the fourth email"
    assert len(mock_send_draft) > 0, "send_draft should be called for rate_negotiator queries"

    print("\nu2705 Full conversation flow successfully tested all agents")


# Run the tests if executed directly
if __name__ == "__main__":
    pytest.main(['-xvs', __file__])
