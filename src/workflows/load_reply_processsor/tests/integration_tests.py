import os
import sys
import json
import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add the parent directory to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Import the modules to test
from workflows.load_reply_processsor.orchestrator import process_message, run_load_reply_processsor
from workflows.load_reply_processsor.sub_agents.info_master import run_info_master
from workflows.load_reply_processsor.sub_agents.warnings_ai import run_warnings_agent
from workflows.load_reply_processsor.sub_agents.load_scan import run_load_scan
from workflows.load_reply_processsor.sub_agents.rate_negotiator import run_rate_negotiator
from workflows.load_reply_processsor.models import AgentsReq, LoadContext, TruckContext, CompanyInfo

# Import test fixtures and utilities
from .fixtures import (
    mock_truck_context,
    mock_load_context,
    mock_company_info,
    mock_run_context_wrapper
)

# Test configuration
TEST_TIMEOUT = 60  # seconds


@pytest.mark.asyncio
async def test_orchestrator_process_message():
    """Test the orchestrator's process_message function with a simple query."""
    # Arrange
    text_query = "What is our company's MC number?"
    thread_id = "test-thread-123"
    email_id = "test-email-123"
    load_id = "test-load-123"
    application_name = "test-app"
    
    # Create test contexts
    truck_context = mock_truck_context(load_id)
    load_context = mock_load_context(load_id)
    company_info = mock_company_info()
    
    # Act
    with patch('workflows.load_reply_processsor.orchestrator.send_reply') as mock_send_reply:
        mock_send_reply.return_value = {"success": True}
        
        result = await process_message(
            text_query=text_query,
            thread_id=thread_id,
            email_id=email_id,
            load_id=load_id,
            application_name=application_name,
            truck_context=truck_context,
            load_context=load_context,
            company_info=company_info
        )
    
    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert "response" in result
    assert len(result["response"]) > 0


@pytest.mark.asyncio
async def test_info_master_agent():
    """Test the info_master agent with a company information query."""
    # Arrange
    ctx = mock_run_context_wrapper()
    ctx.context["company_info"] = mock_company_info()
    ctx.context["thread_id"] = "test-thread-123"
    ctx.context["load_id"] = "test-load-123"
    ctx.context["application_name"] = "test-app"
    ctx.context["email_id"] = "test-email-123"
    ctx.context["email_subject"] = "Test Subject"
    
    query = "What is our company's MC number?"
    args = json.dumps({"query": query})
    
    # Act
    with patch('workflows.load_reply_processsor.sub_agents.info_master.send_reply') as mock_send_reply:
        mock_send_reply.return_value = {"success": True}
        
        result = await run_info_master(ctx, args)
    
    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert "found" in result
    if result["found"]:
        assert "reply" in result
        assert len(result["reply"]) > 0


@pytest.mark.asyncio
async def test_warnings_ai_agent():
    """Test the warnings_ai agent with a load containing potential warnings."""
    # Arrange
    ctx = mock_run_context_wrapper()
    ctx.context["truck_context"] = mock_truck_context("test-load-123")
    ctx.context["load_id"] = "test-load-123"
    ctx.context["application_name"] = "test-app"
    ctx.context["full_text"] = "This is a load of alcohol requiring TWIC certification."
    
    query = "Check for warnings on this load."
    args = json.dumps({"query": query})
    
    # Act
    with patch('workflows.load_reply_processsor.sub_agents.warnings_ai.upsert_load_warnings') as mock_upsert:
        mock_upsert.return_value = {"success": True}
        
        result = await run_warnings_agent(ctx, args)
    
    # Assert
    assert result is not None
    if isinstance(result, dict) and "success" in result:
        assert result["success"]
        if "warnings" in result:
            assert isinstance(result["warnings"], list)


@pytest.mark.asyncio
async def test_load_scan_agent():
    """Test the load_scan agent with a sample load description."""
    # Arrange
    ctx = mock_run_context_wrapper()
    ctx.context["load_id"] = "test-load-123"
    ctx.context["application_name"] = "test-app"
    ctx.context["thread_id"] = "test-thread-123"
    
    query = """Looking for a flatbed to haul 30,000 lbs of steel beams from Chicago, IL to Indianapolis, IN.
    Pickup on Monday, February 17th. Offering $3,500 for the load."""
    args = json.dumps({"query": query})
    
    # Act
    with patch('workflows.load_reply_processsor.sub_agents.load_scan.update_load_reply_status') as mock_update:
        mock_update.return_value = {"success": True}
        
        result = await run_load_scan(ctx, args)
    
    # Assert
    assert result is not None
    try:
        parsed_result = json.loads(result)
        assert "pickup_date" in parsed_result
        assert "equipment_required" in parsed_result
        assert "commodity" in parsed_result
        assert "weight" in parsed_result
        assert "pickup_location" in parsed_result
        assert "delivery_location" in parsed_result
        assert "offered_rate" in parsed_result
    except json.JSONDecodeError:
        pytest.fail("Result is not valid JSON")


@pytest.mark.asyncio
async def test_rate_negotiator_agent():
    """Test the rate_negotiator agent with a rate negotiation query."""
    # Arrange
    ctx = mock_run_context_wrapper()
    ctx.context["load_id"] = "test-load-123"
    ctx.context["application_name"] = "test-app"
    ctx.context["thread_id"] = "test-thread-123"
    ctx.context["email_subject"] = "Rate Negotiation"
    ctx.context["company_info"] = mock_company_info()
    ctx.context["load_context"] = mock_load_context("test-load-123")
    
    query = "Can you do this load for $3,000?"
    args = json.dumps({"query": query})
    
    # Act
    with patch('workflows.load_reply_processsor.sub_agents.rate_negotiator.get_conversation_history') as mock_get_history:
        mock_get_history.return_value = []
        
        with patch('workflows.load_reply_processsor.sub_agents.rate_negotiator.save_message') as mock_save:
            mock_save.return_value = {"success": True}
            
            with patch('workflows.load_reply_processsor.sub_agents.rate_negotiator.send_draft') as mock_send_draft:
                mock_send_draft.return_value = {"success": True}
                
                result = await run_rate_negotiator(ctx, args)
    
    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_full_workflow_integration():
    """Test the full workflow integration with a complete load reply process."""
    # Arrange
    req = {
        "text_query": "We have a load of electronics from New York to Los Angeles. Rate is $4,500. Can you do it?",
        "thread_id": "test-thread-full-123",
        "email_id": "test-email-full-123",
        "load_id": "test-load-full-123",
        "application_name": "test-app-full",
        "email_body": "Full email body with load details",
        "email_subject": "Load from NY to LA"
    }
    
    # Mock the necessary components
    with patch('workflows.load_reply_processsor.orchestrator.get_truck_context') as mock_get_truck:
        mock_get_truck.return_value = mock_truck_context(req["load_id"])
        
        with patch('workflows.load_reply_processsor.orchestrator.get_company_info') as mock_get_company:
            mock_get_company.return_value = mock_company_info()
            
            with patch('workflows.load_reply_processsor.orchestrator.send_reply') as mock_send_reply:
                mock_send_reply.return_value = {"success": True}
                
                # Act
                result = await run_load_reply_processsor(req)
    
    # Assert
    assert result is not None
    assert isinstance(result, dict)
    assert "response" in result
    assert len(result["response"]) > 0


# Run the tests if executed directly
if __name__ == "__main__":
    pytest.main(['-xvs', __file__])
