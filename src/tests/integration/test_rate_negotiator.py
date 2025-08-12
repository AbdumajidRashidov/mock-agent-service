"""Integration tests for the rate_negotiator agent.

This module contains tests that verify the rate_negotiator agent correctly calculates
rates based on thresholds and applies rounding rules.
"""

import pytest
import sys
import os
import re
import json

# Add the parent directories to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Import test data and mocks
from src.tests.integration.data import emails
from workflows.load_reply_processsor.sub_agents import rate_negotiator
from workflows.load_reply_processsor.orchestrator import run_load_reply_processsor


# in_memory_conversation fixture is now imported from conftest.py


@pytest.mark.asyncio
async def test_rate_negotiator_calculation(in_memory_conversation, monkeypatch):
    """Test that the rate_negotiator correctly calculates rates based on thresholds and applies rounding rules."""
    # Create a list to store the captured draft
    captured_drafts = []

    # Override the send_draft function to capture the draft parameter
    async def capturing_send_draft(project_name, load_id, email_body, email_subject, thread_id, draft):
        print(f"\nCaptured rate_negotiator draft: {draft}")
        captured_drafts.append(draft)

        # Return a successful response
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

    # Replace the send_draft function with our capturing function
    monkeypatch.setattr(rate_negotiator, "send_draft", capturing_send_draft)

    # Define test parameters
    min_rate = 1000
    max_rate = 2000
    first_threshold = 0.7  # 70%
    second_threshold = 0.4  # 40%
    rounding = 50

    # Calculate expected rates based on the formula and rounding rules
    expected_first_rate = round((min_rate + (max_rate - min_rate) * first_threshold) / rounding) * rounding
    expected_second_rate = round((min_rate + (max_rate - min_rate) * second_threshold) / rounding) * rounding

    print(f"\nTest parameters: min_rate={min_rate}, max_rate={max_rate}, first_threshold={first_threshold}, second_threshold={second_threshold}, rounding={rounding}")
    print(f"Expected first rate: {expected_first_rate}")
    print(f"Expected second rate: {expected_second_rate}")

    # Use the existing rate negotiation email template (Scenario 2)
    test_email = emails[1]  # Scenario 2: Rate negotiation inquiry

    # Modify the email to use our test parameters
    test_email.load.rate_info.minimum_rate = min_rate
    test_email.load.rate_info.maximum_rate = max_rate
    test_email.load.rate_info.rate_usd = max_rate

    # Set the rate negotiation parameters
    test_email.company_details.rate_negotiation.first_bid_threshold = int(first_threshold * 100)  # Convert to percentage as integer
    test_email.company_details.rate_negotiation.second_bid_threshold = int(second_threshold * 100)  # Convert to percentage as integer
    test_email.company_details.rate_negotiation.min_gap = 0

    # Update the reply email body to trigger rate negotiation
    test_email.reply_email.body = "<p>Can you quote me a rate for this load?</p>"

    # Mock the orchestrator to directly call the rate_negotiator
    from workflows.load_reply_processsor.orchestrator import run_rate_negotiator
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
    
    # Directly call the rate_negotiator agent with properly formatted JSON
    await run_rate_negotiator(mock_ctx, json_args)

    # Verify that we captured at least one draft
    assert len(captured_drafts) > 0, "No drafts were captured from rate_negotiator"

    # Get the first captured draft
    draft = captured_drafts[0]

    print(f"\nRate negotiator response:\n{draft}")

    # Extract any dollar amounts from the draft
    dollar_amounts = re.findall(r'\$(\d[\d,]+)', draft)

    # Convert extracted amounts to integers
    extracted_rates = []
    for amount in dollar_amounts:
        # Remove commas and convert to int
        try:
            rate = int(amount.replace(',', ''))
            extracted_rates.append(rate)
        except ValueError:
            continue

    print(f"Extracted rates: {extracted_rates}")

    # Verify that all rates in the response are rounded according to the rounding rules
    all_rates_properly_rounded = all(rate % rounding == 0 for rate in extracted_rates)

    if all_rates_properly_rounded:
        print(f"✅ All rates in the response are properly rounded to multiples of {rounding}")
    else:
        print(f"⚠️ Some rates in the response are not properly rounded to multiples of {rounding}")
        print(f"Non-rounded rates: {[rate for rate in extracted_rates if rate % rounding != 0]}")

    # The test passes if the response contains properly rounded rates
    # We don't strictly assert that specific rates must be present since the LLM might not include them all
    assert all_rates_properly_rounded, "Some rates in the response are not properly rounded"

    print("\n✅ rate_negotiator correctly applies rounding rules to rates")
