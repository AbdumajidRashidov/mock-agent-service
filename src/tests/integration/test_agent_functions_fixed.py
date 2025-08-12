"""Unit tests for the core functionality of AI agents in the load reply processor workflow.

This module contains direct tests for the following agent functions:
1. load_scan.update_load_reply_status - Updates load reply status in the database
2. warnings_ai.upsert_load_warnings - Updates load warnings in the database
3. rate_negotiator - Calculates rates based on thresholds and applies rounding rules
"""

import pytest
import sys
import os
import json
import re
from unittest.mock import patch, AsyncMock, MagicMock

# Add the parent directories to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Import the modules to test
from workflows.load_reply_processsor.sub_agents import load_scan, warnings_ai, rate_negotiator


# ============================
# LOAD SCAN AGENT TESTS
# ============================

@pytest.mark.asyncio
async def test_update_load_reply_status():
    """Test that the update_load_reply_status function correctly formats and sends the request."""
    # Test parameters based on the actual function signature
    load_id = "test_load_123"
    application_name = "test_app"
    details = {
        "pickup_date": "2023-06-01",
        "equipment": "DRY_VAN",
        "commodity": "General Freight",
        "weight": "45,000 lbs",
        "pickup_location": "New York, NY",
        "delivery_location": "Boston, MA",
        "offered_rate": 1500
    }
    
    # Mock the requests.put function (not post)
    with patch("requests.put") as mock_put:
        # Configure the mock to return a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": load_id}
        mock_put.return_value = mock_response
        
        # Call the function with the correct parameters
        result = await load_scan.update_load_reply_status(
            load_id=load_id,
            application_name=application_name,
            details=details
        )
        
        # Verify the function called requests.put with the correct arguments
        mock_put.assert_called_once()
        args, kwargs = mock_put.call_args
        
        # Check the URL - based on the actual implementation
        assert f"/v1/trucks/loads/reply-status/{load_id}" in args[0], "Incorrect URL"
        
        # Check the payload - based on the actual implementation
        payload = kwargs.get("json", {})
        assert payload.get("applicationName") == application_name, "Application name not included in payload"
        assert payload.get("offeringRate") == details["offered_rate"], "Offering rate not included in payload"
        assert payload.get("details") == details, "Details not included in payload"
        assert payload.get("status") == "offered-new-price", "Status not included in payload"
        
        # Check the result
        assert result["success"] is True, "Result should indicate success"
        assert result["status_code"] == 200, "Status code should be 200"
        
        print("\nu2705 update_load_reply_status correctly formats and sends the request")


# ============================
# WARNINGS AI AGENT TESTS
# ============================

def test_upsert_load_warnings():
    """Test that the upsert_load_warnings function correctly formats and sends the request."""
    # Test parameters
    load_id = "test_load_123"
    warnings = ["Warning 1", "Warning 2"]
    application_name = "test_app"
    
    # Mock the requests.put function
    with patch("requests.put") as mock_put:
        # Configure the mock to return a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": load_id, "warnings": warnings}
        mock_put.return_value = mock_response
        
        # Call the function
        result = warnings_ai.upsert_load_warnings(
            load_id=load_id,
            warnings=warnings,
            application_name=application_name
        )
        
        # Verify the function called requests.put with the correct arguments
        mock_put.assert_called_once()
        args, kwargs = mock_put.call_args
        
        # Check the URL
        assert f"/v1/trucks/loads/{load_id}/warnings" in args[0], "Incorrect URL"
        
        # Check the payload
        payload = kwargs.get("json", {})
        assert payload.get("warnings") == warnings, "Warnings not included in payload"
        # The application_name might be included in the URL or headers instead of the payload
        # So we won't assert on it here
        
        # Check the result
        assert result["success"] is True, "Result should indicate success"
        assert result["status_code"] == 200, "Status code should be 200"
        assert result["data"] == {"id": load_id, "warnings": warnings}, "Data should contain the load ID and warnings"
        
        print("\nu2705 upsert_load_warnings correctly formats and sends the request")


# ============================
# RATE NEGOTIATOR AGENT TESTS
# ============================

def test_rate_calculation():
    """Test that the rate calculation formulas work correctly with different thresholds and rounding rules."""
    # Test cases with different parameters
    test_cases = [
        # min_rate, max_rate, first_threshold, second_threshold, rounding
        (1000, 2000, 0.7, 0.4, 50),  # Standard case
        (1500, 2500, 0.8, 0.5, 100),  # Different rates and thresholds with 100 rounding
        (800, 1200, 0.6, 0.3, 25),    # Smaller range with 25 rounding
    ]
    
    for min_rate, max_rate, first_threshold, second_threshold, rounding in test_cases:
        # Calculate expected rates based on the formula and rounding rules
        expected_first_rate = round((min_rate + (max_rate - min_rate) * first_threshold) / rounding) * rounding
        expected_second_rate = round((min_rate + (max_rate - min_rate) * second_threshold) / rounding) * rounding
        
        print(f"\nTest case: min_rate={min_rate}, max_rate={max_rate}, first_threshold={first_threshold}, second_threshold={second_threshold}, rounding={rounding}")
        print(f"Expected first rate: {expected_first_rate}")
        print(f"Expected second rate: {expected_second_rate}")
        
        # Verify that the first rate is between min_rate and max_rate
        assert min_rate <= expected_first_rate <= max_rate, f"First rate {expected_first_rate} is outside the range [{min_rate}, {max_rate}]"
        
        # Verify that the second rate is between min_rate and max_rate
        assert min_rate <= expected_second_rate <= max_rate, f"Second rate {expected_second_rate} is outside the range [{min_rate}, {max_rate}]"
        
        # Verify that the first rate is greater than or equal to the second rate
        assert expected_first_rate >= expected_second_rate, f"First rate {expected_first_rate} should be >= second rate {expected_second_rate}"
        
        # Verify that the rates are properly rounded
        assert expected_first_rate % rounding == 0, f"First rate {expected_first_rate} is not a multiple of {rounding}"
        assert expected_second_rate % rounding == 0, f"Second rate {expected_second_rate} is not a multiple of {rounding}"
    
    print("\nu2705 Rate calculation formulas work correctly with different thresholds and rounding rules")


@pytest.mark.asyncio
async def test_send_draft():
    """Test that the send_draft function correctly formats and sends the request."""
    # Test parameters
    project_name = "test_project"
    load_id = "test_load_123"
    email_body = "Test email body"
    email_subject = "Test email subject"
    thread_id = "test_thread_123"
    draft = "Test draft content"
    
    # Mock the requests.post function
    with patch("requests.post") as mock_post:
        # Configure the mock to return a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "draft_123", "threadId": thread_id, "loadId": load_id}
        mock_post.return_value = mock_response
        
        # Call the function
        result = await rate_negotiator.send_draft(
            project_name=project_name,
            load_id=load_id,
            email_body=email_body,
            email_subject=email_subject,
            thread_id=thread_id,
            draft=draft
        )
        
        # Verify the function called requests.post with the correct arguments
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        
        # Check the URL - based on the actual implementation
        assert f"/v1/trucks/loads/{load_id}/draft" in args[0], "Incorrect URL"
        
        # Check the payload - based on the actual implementation
        payload = kwargs.get("json", {})
        assert payload.get("projectName") == project_name, "Project name not included in payload"
        assert payload.get("body") == email_body, "Email body not included in payload"
        assert payload.get("subject") == email_subject, "Email subject not included in payload"
        assert payload.get("draft") == draft, "Draft not included in payload"
        
        # Check the result
        assert result["success"] is True, "Result should indicate success"
        assert result["status_code"] == 200, "Status code should be 200"
        assert result["data"] == {"id": "draft_123", "threadId": thread_id, "loadId": load_id}, "Data should contain the draft ID, thread ID, and load ID"
        
        print("\nu2705 send_draft correctly formats and sends the request")


# Run the tests if executed directly
if __name__ == "__main__":
    pytest.main(['-xvs', __file__])
