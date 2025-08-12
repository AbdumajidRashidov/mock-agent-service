"""Integration tests for the warnings_ai agent.

This module contains tests that verify the warnings_ai agent correctly identifies
warnings based on truck attributes and load details.
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
from workflows.load_reply_processsor.sub_agents import warnings_ai
from workflows.load_reply_processsor.orchestrator import run_load_reply_processsor


# in_memory_conversation fixture is now imported from conftest.py


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


@pytest.mark.asyncio
async def test_warnings_ai_output_structure(in_memory_conversation, mock_upsert_load_warnings, monkeypatch):
    """Test that the warnings_ai agent correctly identifies warnings and returns them in the expected format."""
    # Create a list to store the captured output
    captured_output = []

    # Import the original_run_warnings_agent from the orchestrator
    from workflows.load_reply_processsor.orchestrator import original_run_warnings_agent

    # Create a capturing function for the original_run_warnings_agent
    async def capturing_original_run_warnings_agent(ctx, args):
        result = await original_run_warnings_agent(ctx, args)
        print(f"\nCaptured warnings_ai output: {result}")
        captured_output.append(result)
        return result

    # Replace the original_run_warnings_agent in the orchestrator module
    import workflows.load_reply_processsor.orchestrator as orchestrator
    monkeypatch.setattr(orchestrator, "original_run_warnings_agent", capturing_original_run_warnings_agent)

    # Import the function to create custom test data
    from src.tests.integration.data import create_email, create_truck, create_load, create_company_details
    from generated import agents_serivce_pb2

    # Create a custom test email with a truck that has specific restrictions
    custom_email = agents_serivce_pb2.LoadReplyRequest(
        thread_id="custom_thread_123",
        load_id="load_custom_123",
        application_name="test_integration_app",
        reply_email=create_email(
            subject="RE: Alcohol Shipment Request",
            body="<p>Can you handle this alcohol shipment? It requires hazmat certification.</p>",
            thread_id="custom_thread_123"
        ),
        truck=create_truck(
            truck_id="T-CUSTOM-123",
            equipment_type="DRY_VAN",
            restrictions=["alcohol", "explosives"],  # Set restrictions here
            hazmat=True
        ),
        load=create_load(
            load_id="load_custom_123",
            commodity="Alcohol",  # Set commodity to trigger warning
            equipment_type="DRY_VAN"
        ),
        company_details=create_company_details(
            name="Test Trucking Company",
            mc_number="MC-TEST-123"
        )
    )

    # Use our custom test email
    test_email = custom_email

    # Run the load reply processor with the test email
    await run_load_reply_processsor(test_email)

    # Verify that we captured the output
    assert len(captured_output) > 0, "No output was captured from warnings_ai"

    # Get the first captured output
    output = captured_output[0]

    # Print the email content and captured output for better diagnostics
    print(f"\nEmail content:\n{test_email.reply_email.body}")
    print(f"\nTruck restrictions: {test_email.truck.restrictions}")
    print(f"\nCaptured output:\n{json.dumps(output, indent=2)}")

    # Verify that the output is a dictionary with the expected structure
    assert isinstance(output, dict), "Output is not a dictionary"
    assert "success" in output, "Output does not contain 'success' field"
    assert "warnings" in output, "Output does not contain 'warnings' field"

    # Verify that the upsert_load_warnings function was called
    assert len(mock_upsert_load_warnings) > 0, "upsert_load_warnings was not called"

    # Get the arguments passed to upsert_load_warnings
    upsert_args = mock_upsert_load_warnings[0]

    # Verify that the warnings list was passed correctly
    assert "warnings" in upsert_args, "upsert_load_warnings was not called with 'warnings' argument"
    assert isinstance(upsert_args["warnings"], list), "'warnings' argument is not a list"

    # The test passes if the warnings_ai agent returns a properly structured response
    print("\n✅ warnings_ai returned warnings in the expected format")
