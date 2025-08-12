"""
Main entry point for Pydantic AI Load Reply Processor.
Compatible with existing gRPC interface for seamless integration.
"""
from typing import Dict, Any, List, Callable, Optional
import logging
import re
from datetime import datetime

from .agents.freight_agent import process_freight_email
from .utils.exceptions import FreightProcessingError
from .utils.validation import validate_inputs

logger = logging.getLogger(__name__)


def extract_route_from_emails(emails: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Extract route information from email subject lines"""

    for email in emails:
        subject = email.get('subject', '')

        # Look for pattern like "Oak Lawn, IL -> Botines, TX" or "Monon, IN -> W Monroe, LA"
        route_match = re.search(r'([^,]+),\s*([A-Z]{2})\s*->\s*([^,]+),\s*([A-Z]{2})', subject)

        if route_match:
            origin_city, origin_state, dest_city, dest_state = route_match.groups()
            return {
                'origin': {
                    'city': origin_city.strip(),
                    'stateProv': origin_state.strip()
                },
                'destination': {
                    'city': dest_city.strip(),
                    'stateProv': dest_state.strip()
                }
            }

    return None


def preprocess_company_settings(company_details: Dict[str, Any]) -> None:
    """Preprocess company negotiation settings to fix data type issues"""

    if 'rateNegotiation' not in company_details:
        return

    settings = company_details['rateNegotiation']

    # Convert decimal thresholds to percentages (0.8 -> 80)
    if 'firstBidThreshold' in settings and settings['firstBidThreshold'] <= 1:
        settings['firstBidThreshold'] = settings['firstBidThreshold'] * 100
        logger.info(f"🔧 Converted firstBidThreshold: {settings['firstBidThreshold']/100} -> {settings['firstBidThreshold']}")

    if 'secondBidThreshold' in settings and settings['secondBidThreshold'] <= 1:
        settings['secondBidThreshold'] = settings['secondBidThreshold'] * 100
        logger.info(f"🔧 Converted secondBidThreshold: {settings['secondBidThreshold']/100} -> {settings['secondBidThreshold']}")

    # Ensure rounding is integer
    if 'rounding' in settings:
        old_value = settings['rounding']
        settings['rounding'] = int(float(settings['rounding']))
        logger.info(f"🔧 Converted rounding: {old_value} -> {settings['rounding']}")


def preprocess_truck_info(truck: Dict[str, Any]) -> None:
    """Preprocess truck information to fix data type issues"""

    # Fix capacity fields - convert strings to numbers, handle zeros
    for field in ['maxWeight', 'maxLength']:
        if field in truck:
            try:
                old_value = truck[field]
                value = float(truck[field])

                # Convert 0 to None (unlimited capacity)
                truck[field] = value if value > 0 else None

                logger.info(f"🔧 Converted truck {field}: {old_value} -> {truck[field]}")

            except (ValueError, TypeError):
                truck[field] = None
                logger.warning(f"⚠️ Invalid truck {field}, set to None")


def preprocess_load_info(load: Dict[str, Any], emails: List[Dict[str, Any]]) -> None:
    """Preprocess load information to ensure required fields"""

    # 1. Fix missing origin/destination
    if not load.get('origin') or not load.get('destination'):
        logger.info("🔧 Load missing origin/destination, attempting extraction from emails")

        if emails:
            route_info = extract_route_from_emails(emails)
            if route_info:
                load.update(route_info)
                logger.info(f"✅ Extracted route: {route_info['origin']['city']}, {route_info['origin']['stateProv']} -> {route_info['destination']['city']}, {route_info['destination']['stateProv']}")
            else:
                # Create placeholders
                load['origin'] = {'city': 'TBD', 'stateProv': 'TBD'}
                load['destination'] = {'city': 'TBD', 'stateProv': 'TBD'}
                logger.warning("⚠️ Could not extract route, using placeholders")
        else:
            # No emails to extract from
            load['origin'] = {'city': 'TBD', 'stateProv': 'TBD'}
            load['destination'] = {'city': 'TBD', 'stateProv': 'TBD'}

    # 2. Ensure rate info exists for negotiation
    if 'rateInfo' not in load or not load['rateInfo']:
        load['rateInfo'] = {}

    rate_info = load['rateInfo']

    # Add default rate ranges if missing
    if not rate_info.get('minimumRate') or not rate_info.get('maximumRate'):
        # Smart defaults based on distance/route
        origin = load.get('origin', {})
        destination = load.get('destination', {})

        # Simple route classification for rate ranges
        default_ranges = {
            "short": {"min": 800, "max": 1500},    # < 500 miles
            "medium": {"min": 1500, "max": 3000},  # 500-1000 miles
            "long": {"min": 2500, "max": 4500},    # 1000+ miles
        }

        # Default to medium range (you can enhance with actual distance calculation)
        route_type = "medium"

        # Simple heuristic: if states are far apart, assume long haul
        origin_state = origin.get('stateProv', '')
        dest_state = destination.get('stateProv', '')

        if origin_state and dest_state and origin_state != dest_state:
            # Different states - check if they're far apart
            east_coast = ['NY', 'MA', 'CT', 'NJ', 'PA', 'VA', 'NC', 'SC', 'GA', 'FL']
            west_coast = ['CA', 'OR', 'WA', 'NV', 'AZ']

            if (origin_state in east_coast and dest_state in west_coast) or \
               (origin_state in west_coast and dest_state in east_coast):
                route_type = "long"
            elif origin_state == dest_state:
                route_type = "short"

        rate_info['minimumRate'] = default_ranges[route_type]["min"]
        rate_info['maximumRate'] = default_ranges[route_type]["max"]

        logger.info(f"🔧 Added default rate range ({route_type}): ${rate_info['minimumRate']} - ${rate_info['maximumRate']}")


def preprocess_input_data(
    company_details: Dict[str, Any],
    truck: Dict[str, Any],
    load: Dict[str, Any],
    emails: List[Dict[str, Any]]
) -> None:
    """
    Comprehensive preprocessing of all input data to fix common format issues.
    Modifies data in-place.
    """

    logger.info("🔧 Starting input data preprocessing...")

    # 1. Fix company settings
    preprocess_company_settings(company_details)

    # 2. Fix truck information
    preprocess_truck_info(truck)

    # 3. Fix load information
    preprocess_load_info(load, emails)

    logger.info("✅ Input data preprocessing completed")


async def process_reply(
    company_details: Dict[str, Any],
    our_emails: List[str],
    truck: Dict[str, Any],
    load: Dict[str, Any],
    emails: List[Dict[str, Any]],
    response_callback: Callable
) -> Dict[str, Any]:
    """
    Process a freight load reply email using Pydantic AI agents.

    This function signature matches the existing workflow-based processor
    to ensure drop-in compatibility with the gRPC server.

    Args:
        company_details: Company information and settings
        our_emails: List of dispatcher email addresses
        truck: Truck capabilities and restrictions
        load: Load information and history
        emails: Email conversation thread
        response_callback: Callback for streaming responses

    Returns:
        Dict containing processing results:
        - email_to_send: Generated email content if any
        - field_updates: Database field updates
        - message: Processing status message
        - metadata: Additional processing information
    """
    try:
        # Log the start of processing
        await response_callback({
            "message": "Starting Pydantic AI freight processing with preprocessing",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "processor_version": "pydantic_ai_v3.0_modular",
                "load_id": load.get("id"),
                "email_count": len(emails)
            }
        })

        # CRITICAL: Preprocess data BEFORE validation
        preprocess_input_data(company_details, truck, load, emails)

        await response_callback({
            "message": "Input data preprocessing completed",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "rate_range": f"${load.get('rateInfo', {}).get('minimumRate', 0)}-${load.get('rateInfo', {}).get('maximumRate', 0)}",
                "company_negotiation": bool(company_details.get('rateNegotiation')),
                "truck_max_weight": truck.get('maxWeight'),
                "has_route": bool(load.get('origin') and load.get('destination'))
            }
        })

        # Validate the preprocessed data
        validation_result = validate_inputs(
            company_details, our_emails, truck, load, emails
        )

        if not validation_result.is_valid:
            error_msg = f"Input validation failed: {validation_result.error}"
            await response_callback({
                "message": error_msg,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "validation_errors": validation_result.errors,
                    "validation_warnings": validation_result.warnings
                }
            })
            return {
                "field_updates": {},
                "message": error_msg,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "validation_errors": validation_result.errors
                }
            }

        # Process the freight email using AI agent
        result = await process_freight_email(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            response_callback=response_callback
        )

        # Log successful completion
        await response_callback({
            "message": "Pydantic AI processing completed successfully",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "has_email": bool(result.get("email_to_send")),
                "field_update_count": len(result.get("field_updates", {})),
                "final_message": result.get("message", "")
            }
        })

        return result

    except FreightProcessingError as e:
        logger.error(f"Freight processing error: {e}")
        await response_callback({
            "message": f"Processing failed: {e.message}",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "error_type": "FreightProcessingError",
                "error_code": e.code
            }
        })
        return {
            "field_updates": {},
            "message": f"Processing failed: {e.message}",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        }

    except Exception as e:
        logger.exception("Unexpected error in freight processing")
        await response_callback({
            "message": f"Unexpected error: {str(e)}",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "error_type": type(e).__name__
            }
        })
        return {
            "field_updates": {},
            "message": f"Unexpected error: {str(e)}",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        }


# Additional utility functions for testing and debugging

def debug_input_data(company_details, truck, load, emails):
    """Debug function to inspect input data before processing"""

    print("🔍 DEBUG: Input Data Analysis")
    print("-" * 50)

    # Company analysis
    print(f"Company: {company_details.get('name', 'N/A')}")
    if 'rateNegotiation' in company_details:
        settings = company_details['rateNegotiation']
        print(f"  Negotiation: {settings.get('firstBidThreshold')}/{settings.get('secondBidThreshold')}/{settings.get('rounding')}")

    # Truck analysis
    print(f"Truck: Weight={truck.get('maxWeight')}, Length={truck.get('maxLength')}")

    # Load analysis
    origin = load.get('origin', {})
    destination = load.get('destination', {})
    print(f"Route: {origin.get('city', 'N/A')}, {origin.get('stateProv', 'N/A')} -> {destination.get('city', 'N/A')}, {destination.get('stateProv', 'N/A')}")

    rate_info = load.get('rateInfo', {})
    print(f"Rate Range: ${rate_info.get('minimumRate', 'N/A')} - ${rate_info.get('maximumRate', 'N/A')}")

    # Email analysis
    print(f"Emails: {len(emails)} messages")
    for i, email in enumerate(emails):
        sender = email.get('from', [{}])[0].get('email', 'Unknown')
        subject = email.get('subject', '')[:50]
        print(f"  {i+1}. {sender}: {subject}...")

    print("-" * 50)


def validate_preprocessing_result(company_details, truck, load):
    """Validate that preprocessing worked correctly"""

    issues = []

    # Check company settings
    if 'rateNegotiation' in company_details:
        settings = company_details['rateNegotiation']
        if settings.get('firstBidThreshold', 0) <= 1:
            issues.append("firstBidThreshold still in decimal format")
        if settings.get('secondBidThreshold', 0) <= 1:
            issues.append("secondBidThreshold still in decimal format")
        if not isinstance(settings.get('rounding'), int):
            issues.append("rounding is not an integer")

    # Check truck data
    for field in ['maxWeight', 'maxLength']:
        if field in truck and isinstance(truck[field], str):
            issues.append(f"truck {field} is still a string")

    # Check load data
    if not load.get('origin') or not load.get('destination'):
        issues.append("load missing origin or destination")

    if not load.get('rateInfo'):
        issues.append("load missing rateInfo")
    else:
        rate_info = load['rateInfo']
        if not rate_info.get('minimumRate') or not rate_info.get('maximumRate'):
            issues.append("load missing rate range")

    if issues:
        logger.warning(f"⚠️ Preprocessing issues found: {issues}")
        return False, issues
    else:
        logger.info("✅ Preprocessing validation passed")
        return True, []
