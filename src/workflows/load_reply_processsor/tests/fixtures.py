import os
import sys
from datetime import datetime
from unittest.mock import MagicMock

# Add the parent directory to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from workflows.load_reply_processsor.models import LoadContext, TruckContext, CompanyInfo


def mock_truck_context(load_id):
    """
    Create a mock TruckContext object for testing.
    
    Args:
        load_id: The ID of the load to associate with the truck context
        
    Returns:
        A TruckContext object with test data
    """
    # Create a protobuf-like mock object that mimics the structure expected by the code
    truck = MagicMock()
    
    # Set up the restrictions attribute
    truck.restrictions = ["alcohol", "tobacco"]
    
    # Set up the is_permitted attribute with a DESCRIPTOR for get_keys_with_value
    truck.is_permitted = MagicMock()
    truck.is_permitted.DESCRIPTOR = MagicMock()
    truck.is_permitted.DESCRIPTOR.fields_by_name = {
        "hazmat": True,
        "tanker": False,
        "oversize": True,
        "twic": False
    }
    
    # Set up the security attribute with a DESCRIPTOR for get_keys_with_value
    truck.security = MagicMock()
    truck.security.DESCRIPTOR = MagicMock()
    truck.security.DESCRIPTOR.fields_by_name = {
        "tsa": True,
        "twic": False,
        "heavy_duty_lock": True,
        "escort_driving": False
    }
    
    # Set up other truck attributes
    truck.team_solo = "SOLO"
    truck.length = "53"
    truck.weight = "45000"
    truck.load_id = load_id
    
    return truck


def mock_load_context(load_id):
    """
    Create a mock LoadContext object for testing.
    
    Args:
        load_id: The ID of the load
        
    Returns:
        A LoadContext object with test data
    """
    # Create a basic load context
    load_context = LoadContext(
        load_id=load_id,
        commodity="Electronics",
        weight="30000",
        equipment_type="Van",
        hazmat=False,
        pickup_date="2025-04-15",
        delivery_date="2025-04-18",
        origin_city="New York",
        origin_state="NY",
        destination_city="Los Angeles",
        destination_state="CA",
        rate="4500",
        miles="2800",
        permits_required=["Oversize"],
        certifications_required=["TSA"],
        session_start=datetime.now()
    )
    
    # Add rate_info dictionary
    load_context.rate_info = {
        "basis": "FLAT",
        "rateUsd": "4500",
        "minimum_rate": 3800,
        "maximum_rate": 5200
    }
    
    # Create protobuf-like structure for more complex access patterns
    load_context.origin = MagicMock()
    load_context.origin.city = "New York"
    load_context.origin.state_prov = "NY"
    
    load_context.destination = MagicMock()
    load_context.destination.city = "Los Angeles"
    load_context.destination.state_prov = "CA"
    
    load_context.shipment_details = MagicMock()
    load_context.shipment_details.type = "General Freight"
    load_context.shipment_details.full_partial = "FULL"
    load_context.shipment_details.maximum_weight_pounds = 45000
    load_context.shipment_details.maximum_length_feet = 53
    
    load_context.earliest_availability = "2025-04-15T08:00:00Z"
    load_context.latest_availability = "2025-04-15T16:00:00Z"
    load_context.comments = "Handle with care"
    load_context.trip_length = 2800
    
    return load_context


def mock_company_info():
    """
    Create a mock CompanyInfo object for testing.
    
    Returns:
        A CompanyInfo object with test data
    """
    company_info = CompanyInfo(
        name="Numeo Trucking Inc.",
        mc_number="MC-123456",
        details="Numeo Trucking is a reliable carrier specializing in nationwide freight transportation. "
                "We have a fleet of well-maintained trucks and professional drivers. "
                "Our company is fully insured with $1M in liability coverage and $100K in cargo insurance. "
                "Contact us at dispatch@numeo.ai or call (555) 123-4567."
    )
    
    # Add rate_negotiation dictionary
    company_info.rate_negotiation = {
        "first_bid_threshold": 0.8,
        "second_bid_threshold": 0.3,
        "strategy": "aggressive"
    }
    
    return company_info


def mock_run_context_wrapper():
    """
    Create a mock RunContextWrapper object for testing.
    
    Returns:
        A RunContextWrapper mock object
    """
    ctx = MagicMock()
    ctx.context = {}
    return ctx


# Mock database functions
def mock_get_conversation_history(thread_id):
    """
    Mock function to get conversation history.
    
    Args:
        thread_id: The ID of the thread
        
    Returns:
        A list of mock conversation messages
    """
    return [
        {
            "role": "user",
            "content": "I have a load from New York to Los Angeles. Rate is $4,500. Can you do it?"
        },
        {
            "role": "assistant",
            "content": "We'd need $5,000 for that route due to the distance and current fuel prices."
        },
        {
            "role": "user",
            "content": "Can you do it for $4,800?"
        }
    ]


def mock_format_conversation_for_llm(conversation_history):
    """
    Mock function to format conversation history for LLM.
    
    Args:
        conversation_history: The raw conversation history
        
    Returns:
        A formatted list of conversation messages
    """
    return [
        {"role": msg["role"], "content": msg["content"]}
        for msg in conversation_history
    ]
