#!/usr/bin/env python3
"""
Utility functions for broker information processing.
Simplified version with core functionality only.
"""
import logging
from typing import Dict, Any

# Configure logger
logger = logging.getLogger(__name__)

def extract_sender_info(message: Dict[str, Any]) -> Dict[str, str]:
    """Extract email sender information."""
    sender_email = ""
    sender_name = ""

    if (
        message.get("from")
        and isinstance(message["from"], list)
        and len(message["from"]) > 0
    ):
        sender = message["from"][0]
        sender_email = sender.get("email", "")
        sender_name = sender.get("name", "")

    return {"email": sender_email, "name": sender_name}


def add_broker_contact_from_email(
    broker: Dict[str, Any], from_email: str = None, from_name: str = None
) -> Dict[str, Any]:
    """Add broker contact from email if not already present."""
    if not broker:
        broker = {
            "companyName": "",
            "contact": {"name": None, "phone": None, "email": None},
        }

    # Create contact if it doesn't exist
    if not broker.get("contact"):
        broker["contact"] = {"name": None, "phone": None, "email": None}

    # Add email if not present
    if not broker["contact"].get("email") and from_email:
        broker["contact"]["email"] = from_email.lower()

    # Add name if not present
    if not broker["contact"].get("name") and from_name:
        broker["contact"]["name"] = from_name

    return broker


# Note: The get_mc_number function has been moved to the temporary file
# for future relocation to a dedicated broker information service.
