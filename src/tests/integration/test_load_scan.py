"""Integration tests for the load_scan agent.

This module contains tests that verify the load_scan agent correctly extracts
structured data from unstructured text and sends it to the main service.
"""

import pytest
import sys
import os
import json

# Add the parent directories to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Import test data and mocks
from src.tests.integration.data import emails
from workflows.load_reply_processsor.sub_agents import load_scan
from workflows.load_reply_processsor.orchestrator import run_load_reply_processsor


@pytest.fixture
def in_memory_conversation(monkeypatch):
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


@pytest.fixture
def mock_update_load_reply_status(monkeypatch):
    """Mock the update_load_reply_status function to prevent actual API calls."""
    # Create a mock function that captures the arguments
    captured_args = []

    async def mock_func(load_id, status=None, offering_rate=None, application_name=None, warnings=None):
        print(f"\nMock update_load_reply_status called with:")
        print(f"  load_id: {load_id}")
        print(f"  status: {status}")
        print(f"  offering_rate: {offering_rate}")
        print(f"  application_name: {application_name}")
        print(f"  warnings: {warnings}")
        
        captured_args.append({
            "load_id": load_id,
            "status": status,
            "offering_rate": offering_rate,
            "application_name": application_name,
            "warnings": warnings
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


@pytest.mark.asyncio
async def test_load_scan_output_structure(in_memory_conversation, mock_update_load_reply_status, monkeypatch):
    """Test that the load_scan agent returns the expected JSON structure."""
    # Create a list to store the captured output
    captured_output = []
    
    # Override the run_load_scan function to capture its output
    original_run_load_scan = load_scan.run_load_scan
    
    async def capturing_run_load_scan(ctx, args):
        result = await original_run_load_scan(ctx, args)
        print(f"\nCaptured load_scan output: {result}")
        captured_output.append(result)
        return result
    
    # Replace the run_load_scan function with our capturing function
    monkeypatch.setattr(load_scan, "run_load_scan", capturing_run_load_scan)
    
    # Use the rate negotiation email from the test data
    test_email = emails[1]  # Scenario 2: Rate negotiation inquiry
    
    # Update the email body to include more explicit load details for testing
    test_email.reply_email.body = """<p>Rate: $2,000, Commodity: General Freight, Weight: 45,000 lbs, Equipment: DRY_VAN, 
    Pickup Location: New York, NY, Delivery Location: Boston, MA</p>"""
    
    # Mock the orchestrator to directly call the load_scan agent
    from workflows.load_reply_processsor.orchestrator import run_load_scan
    import json
    
    # Create a context object similar to what the orchestrator would create
    class MockContext:
        def __init__(self, context):
            self.context = context
    
    # Create a mock context with the necessary data
    mock_ctx = MockContext({
        'thread_id': test_email.thread_id,
        'load_id': test_email.load_id,
        'application_name': test_email.application_name,
        'email_subject': test_email.reply_email.subject,
        'email_body': test_email.reply_email.body,
        'load_context': test_email.load,
        'truck_context': test_email.truck,
        'company_info': test_email.company_details
    })
    
    # Format the input as JSON for the AgentsReq model
    json_args = json.dumps({
        'query': test_email.reply_email.body
    })
    
    # Directly call the load_scan agent with properly formatted JSON
    await load_scan.run_load_scan(mock_ctx, json_args)
    
    # Verify that we captured the output
    assert len(captured_output) > 0, "No output was captured from load_scan"
    
    # Get the first captured output
    output = captured_output[0]
    
    # Print the email content and captured output for better diagnostics
    print(f"\nEmail content:\n{test_email.reply_email.body}")
    print(f"\nCaptured output:\n{output}")
    
    # If the output is a JSON string, parse it into a dictionary
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
    
    # Verify that the output is a dictionary (JSON structure)
    assert isinstance(output, dict), "Output is not a dictionary"
    
    # Check for required fields in the output
    required_fields = [
        "pickup_date", "equipment", "commodity", "weight", 
        "pickup_location", "delivery_location", "offered_rate"
    ]
    
    for field in required_fields:
        assert field in output, f"Required field '{field}' not found in output"
    
    # Verify that the update_load_reply_status function was called
    assert len(mock_update_load_reply_status) > 0, "update_load_reply_status was not called"
    
    # The test passes if the load_scan agent returns a properly structured output
    print("\n✅ load_scan returned data in the expected format")
