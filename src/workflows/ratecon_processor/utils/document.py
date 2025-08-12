#!/usr/bin/env python3
"""
Utility functions for document processing and data sanitization.
"""
import json
import logging
import requests
import time
from typing import Dict, Any, Optional

# Configure logger
logger = logging.getLogger(__name__)


def download_document(document_url: str) -> Optional[bytes]:
    """Download a document from a GCS URL."""
    try:
        response = requests.get(document_url)
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"Failed to download document: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error downloading document: {str(e)}")
        return None


def sanitize_processing_result(result: Dict[Any, Any]) -> Dict[Any, Any]:
    """Sanitize and validate the processing result."""
    # Create a deep copy to avoid modifying the original
    sanitized = json.loads(json.dumps(result))

    # Generate a document ID if not present
    if not sanitized.get("documentId"):
        sanitized["documentId"] = f"ratecon-{int(time.time())}"

    # Ensure rate amount is a number
    if sanitized.get("rate", {}).get("amount") and isinstance(
        sanitized["rate"]["amount"], str
    ):
        try:
            sanitized["rate"]["amount"] = float(
                sanitized["rate"]["amount"].replace(",", "").replace("$", "")
            )
        except (ValueError, TypeError):
            sanitized["rate"]["amount"] = 0

    # Ensure route has at least pickup and delivery
    if not sanitized.get("route") or len(sanitized.get("route", [])) < 2:
        sanitized["route"] = sanitized.get("route", [])
        if not any(stop.get("type") == "pickup" for stop in sanitized["route"]):
            sanitized["route"].append(
                {
                    "type": "pickup",
                    "location": {
                        "address": "",
                        "city": "",
                        "state": "",
                        "zipCode": "",
                        "country": "USA",
                    },
                }
            )
        if not any(stop.get("type") == "delivery" for stop in sanitized["route"]):
            sanitized["route"].append(
                {
                    "type": "delivery",
                    "location": {
                        "address": "",
                        "city": "",
                        "state": "",
                        "zipCode": "",
                        "country": "USA",
                    },
                }
            )

    # Standardize equipment types
    sanitized = standardize_equipment_types(sanitized)

    # Normalize emails
    sanitized = normalize_emails(sanitized)

    return sanitized


def normalize_emails(obj: Any) -> Any:
    """Ensure all email addresses in an object are lowercase.
    This recursively processes objects and arrays to find and convert email fields.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "email" and isinstance(value, str):
                obj[key] = value.lower()
            else:
                obj[key] = normalize_emails(value)
        return obj
    elif isinstance(obj, list):
        return [normalize_emails(item) for item in obj]
    else:
        return obj


def standardize_equipment_types(result: Dict[Any, Any]) -> Dict[Any, Any]:
    """Standardize freight type and trailer type.
    This ensures consistent terminology across all rate confirmations.
    """
    # Create a deep copy to avoid modifying the original
    result = json.loads(json.dumps(result))

    # Standardize freight type
    if result.get("freightDetails", {}).get("type"):
        freight_type = result["freightDetails"]["type"].lower()

        if "dry" in freight_type or "van" in freight_type:
            result["freightDetails"]["type"] = "Dry Van"
        elif "reefer" in freight_type or "refrigerated" in freight_type:
            result["freightDetails"]["type"] = "Reefer"
        elif "flat" in freight_type or "flatbed" in freight_type:
            result["freightDetails"]["type"] = "Flatbed"
        elif "step" in freight_type or "stepdeck" in freight_type:
            result["freightDetails"]["type"] = "Step Deck"
        elif "low" in freight_type and "boy" in freight_type:
            result["freightDetails"]["type"] = "Lowboy"
        elif (
            "rgn" in freight_type
            or "removable" in freight_type
            and "gooseneck" in freight_type
        ):
            result["freightDetails"]["type"] = "RGN"
        elif "power" in freight_type and "only" in freight_type:
            result["freightDetails"]["type"] = "Power Only"
        elif "hotshot" in freight_type:
            result["freightDetails"]["type"] = "Hotshot"
        elif "conestoga" in freight_type:
            result["freightDetails"]["type"] = "Conestoga"
        else:
            # Capitalize each word
            result["freightDetails"]["type"] = " ".join(
                word.capitalize() for word in result["freightDetails"]["type"].split()
            )

    # Standardize trailer type
    if result.get("driver", {}).get("trailerType"):
        trailer_type = result["driver"]["trailerType"].lower()

        if "dry" in trailer_type or "van" in trailer_type:
            result["driver"]["trailerType"] = "Dry Van"
        elif "reefer" in trailer_type or "refrigerated" in trailer_type:
            result["driver"]["trailerType"] = "Reefer"
        elif "flat" in trailer_type or "flatbed" in trailer_type:
            result["driver"]["trailerType"] = "Flatbed"
        elif "step" in trailer_type or "stepdeck" in trailer_type:
            result["driver"]["trailerType"] = "Step Deck"
        elif "low" in trailer_type and "boy" in trailer_type:
            result["driver"]["trailerType"] = "Lowboy"
        elif (
            "rgn" in trailer_type
            or "removable" in trailer_type
            and "gooseneck" in trailer_type
        ):
            result["driver"]["trailerType"] = "RGN"
        else:
            # Capitalize each word
            result["driver"]["trailerType"] = " ".join(
                word.capitalize() for word in result["driver"]["trailerType"].split()
            )

    return result
