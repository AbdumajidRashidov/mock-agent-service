"""Integration tests for the negotiation reply processor agent.

This module contains tests that verify the negotiation reply processor agent
correctly processes broker replies to rate offers and generates appropriate responses.
"""

import pytest
import sys
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, ANY, mock_open
from typing import Dict, Any, List, Optional, Callable

# Add the parent directories to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Import the negotiation reply processor
from workflows.load_reply_processor_langgraph_based.negotiation.main import process_negotiation_reply, create_workflow
from workflows.load_reply_processor_langgraph_based.negotiation.agents_nodes.rate_analyzer import RateAnalysisResponse, analyze_rate
from workflows.load_reply_processor_langgraph_based.info_request.agents_nodes.negotiation_email_generator import negotiation_email_generator

@pytest.fixture
def mock_workflow():
    """Fixture to mock the workflow creation and execution."""
    async def mock_workflow_ainvoke(state):
        # Simulate workflow execution
        if state.get("rate_analysis", {}).get("is_rate_accepted", False):
            return {
                "email_to_send": "Test accepted email body",
                "email_subject": "Re: Test Accepted Subject",
                "suggested_emails": []
            }
        else:
            return {
                "email_to_send": "Test email body",
                "email_subject": "Re: Test Subject",
                "suggested_emails": [
                    "First suggested email",
                    "Second suggested email",
                    "Third suggested email"
                ]
            }
    
    with patch('workflows.load_reply_processor_langgraph_based.negotiation.main.create_workflow') as mock_create_workflow:
        mock_workflow = AsyncMock()
        mock_workflow.ainvoke.side_effect = mock_workflow_ainvoke
        mock_create_workflow.return_value = mock_workflow
        yield mock_create_workflow

@pytest.fixture
def mock_email_generator():
    """Fixture to mock the email generator responses."""
    with patch('workflows.load_reply_processor_langgraph_based.info_request.agents_nodes.negotiation_email_generator.negotiation_email_generator') as mock_gen:
        # Mock the email generator to return some test emails
        mock_gen.return_value = {
            "email_to_send": "Test email body",
            "email_subject": "Re: Test Subject",
            "suggested_emails": [
                "First suggested email",
                "Second suggested email",
                "Third suggested email"
            ]
        }
        yield mock_gen

@pytest.fixture
def test_data():
    """Fixture providing test data for the negotiation reply processor."""
    return {
        "company_details": {
            "id": "test_company",
            "name": "Test Company",
            "email": "test@example.com"
        },
        "our_emails": ["test@example.com"],
        "truck": {
            "id": "truck_123",
            "type": "Semi"
        },
        "load": {
            "id": "load_123",
            "pickupLocation": "New York, NY",
            "deliveryLocation": "Los Angeles, CA",
            "emailHistory": {
                "details": {
                    "isInfoRequestFinished": True
                },
                "emails": [
                    {
                        "id": "email_1",
                        "from": [{"email": "test@example.com"}],
                        "to": [{"email": "broker@example.com"}],
                        "subject": "Rate Offer: $2000",
                        "body": "We can offer $2000 for this load.",
                        "timestamp": "2025-01-01T00:00:00Z"
                    },
                    {
                        "id": "email_2",
                        "from": [{"email": "broker@example.com"}],
                        "to": [{"email": "test@example.com"}],
                        "subject": "Re: Rate Offer: $2000",
                        "body": "Can you do better than $2000?",
                        "timestamp": "2025-01-01T00:05:00Z"
                    }
                ]
            },
            "rateInfo": {
                "rateUsd": 2000,
                "minimumRate": 1800,
                "maximumRate": 2200
            }
        }
    }

@pytest.mark.asyncio
async def test_process_negotiation_reply_rate_rejected(mock_workflow, test_data):
    """Test that the negotiation reply processor correctly handles a rate rejection."""
    # Mock the response callback
    response_callback = AsyncMock()
    
    # Call the function under test
    await process_negotiation_reply(
        company_details=test_data["company_details"],
        our_emails=test_data["our_emails"],
        truck=test_data["truck"],
        load=test_data["load"],
        emails=test_data["load"]["emailHistory"]["emails"],
        response_callback=response_callback
    )
    
    # Verify the response callback was called with the expected arguments
    response_callback.assert_called_once()
    args, _ = response_callback.call_args
    response = args[0]
    
    # Check that the response contains the expected fields
    assert "email_to_send" in response, "Response should contain email_to_send"
    assert "field_updates" in response, "Response should contain field_updates"
    assert "metadata" in response, "Response should contain metadata"
    assert "rate_analysis" in response["metadata"], "Metadata should contain rate_analysis"
    assert "timestamp" in response["metadata"], "Metadata should contain timestamp"

@pytest.mark.asyncio
async def test_process_negotiation_reply_rate_accepted(mock_workflow, test_data):
    """Test that the negotiation reply processor correctly handles a rate acceptance."""
    # Mock the response callback
    response_callback = AsyncMock()
    
    # Update the workflow mock to simulate rate acceptance
    async def mock_workflow_ainvoke(state):
        return {
            "email_to_send": "Test accepted email body",
            "email_subject": "Re: Test Accepted Subject",
            "suggested_emails": []
        }
    
    mock_workflow.return_value.ainvoke.side_effect = mock_workflow_ainvoke
    
    # Call the function under test
    await process_negotiation_reply(
        company_details=test_data["company_details"],
        our_emails=test_data["our_emails"],
        truck=test_data["truck"],
        load=test_data["load"],
        emails=test_data["load"]["emailHistory"]["emails"],
        response_callback=response_callback
    )
    
    # Verify the response callback was called with the expected arguments
    response_callback.assert_called_once()
    args, _ = response_callback.call_args
    response = args[0]
    
    # Check that the response contains the expected fields
    assert "email_to_send" in response, "Response should contain email_to_send"
    assert "field_updates" in response, "Response should contain field_updates"
    assert "metadata" in response, "Response should contain metadata"
    assert "rate_analysis" in response["metadata"], "Metadata should contain rate_analysis"
    assert "timestamp" in response["metadata"], "Metadata should contain timestamp"

@pytest.mark.asyncio
async def test_process_negotiation_reply_info_request_not_finished(mock_workflow, test_data):
    """Test that the negotiation reply processor skips processing if info request is not finished."""
    # Set isInfoRequestFinished to False
    test_data["load"]["emailHistory"]["details"]["isInfoRequestFinished"] = False
    
    # Mock the response callback
    response_callback = AsyncMock()
    
    # Call the function under test
    await process_negotiation_reply(
        company_details=test_data["company_details"],
        our_emails=test_data["our_emails"],
        truck=test_data["truck"],
        load=test_data["load"],
        emails=test_data["load"]["emailHistory"]["emails"],
        response_callback=response_callback
    )
    
    # Verify the response callback was not called and workflow was not created
    response_callback.assert_not_called()
    mock_workflow.assert_not_called()
