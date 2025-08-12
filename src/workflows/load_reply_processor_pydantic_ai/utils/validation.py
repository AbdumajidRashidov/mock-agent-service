"""Data validation helpers for freight processing"""

from typing import Dict, Any, List
from ..models.base import ValidationResult
from ..models.load import LoadInfo

REQUIRED_COMPANY_FIELDS = ['name', 'mcNumber']

def validate_inputs(
    company_details: Dict[str, Any],
    our_emails: List[str],
    truck: Dict[str, Any],
    load: Dict[str, Any],
    emails: List[Dict[str, Any]]
) -> ValidationResult:
    """
    Validate all input parameters for freight processing.

    Args:
        company_details: Company information
        our_emails: List of dispatcher emails
        truck: Truck information
        load: Load information
        emails: Email thread

    Returns:
        ValidationResult with validation status and errors
    """
    errors = []
    warnings = []

    # Validate company details
    company_validation = validate_company_details(company_details)
    if not company_validation.is_valid:
        errors.extend(company_validation.errors)
    warnings.extend(company_validation.warnings)

    # Validate our emails
    if not our_emails or not isinstance(our_emails, list):
        errors.append("our_emails must be a non-empty list")
    else:
        for email in our_emails:
            if not isinstance(email, str) or '@' not in email:
                errors.append(f"Invalid email format: {email}")

    # Validate truck information
    truck_validation = validate_truck_info(truck)
    if not truck_validation.is_valid:
        errors.extend(truck_validation.errors)
    warnings.extend(truck_validation.warnings)

    # Validate load information
    load_validation = validate_load_info(load)
    if not load_validation.is_valid:
        errors.extend(load_validation.errors)
    warnings.extend(load_validation.warnings)

    # Validate email thread
    email_validation = validate_email_thread(emails)
    if not email_validation.is_valid:
        errors.extend(email_validation.errors)
    warnings.extend(email_validation.warnings)

    return ValidationResult(
        is_valid=len(errors) == 0,
        error=errors[0] if errors else None,
        errors=errors,
        warnings=warnings
    )


def validate_company_details(company_details: Dict[str, Any]) -> ValidationResult:
    """Validate company details structure and required fields"""

    errors = []
    warnings = []

    if not isinstance(company_details, dict):
        return ValidationResult(
            is_valid=False,
            error="company_details must be a dictionary"
        )

    # Check required fields
    for field in REQUIRED_COMPANY_FIELDS:
        if field not in company_details or not company_details[field]:
            errors.append(f"Missing required company field: {field}")

    # Validate MC number format
    if 'mcNumber' in company_details and company_details['mcNumber']:
        mc_number = str(company_details['mcNumber'])
        if not mc_number.replace('#', '').replace('MC', '').strip().isdigit():
            warnings.append("MC number should be numeric")

    # Validate negotiation settings if present
    if 'rateNegotiation' in company_details and company_details['rateNegotiation']:
        negotiation_validation = validate_negotiation_settings(company_details['rateNegotiation'])
        if not negotiation_validation.is_valid:
            errors.extend(negotiation_validation.errors)
        warnings.extend(negotiation_validation.warnings)

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )

def validate_negotiation_settings(settings: Dict[str, Any]) -> ValidationResult:
    """Validate rate negotiation settings with type conversion"""

    errors = []
    warnings = []

    required_fields = ['firstBidThreshold', 'secondBidThreshold', 'rounding']

    for field in required_fields:
        if field not in settings:
            errors.append(f"Missing negotiation setting: {field}")
            continue

        value = settings[field]

        if field in ['firstBidThreshold', 'secondBidThreshold']:
            try:
                # Convert to float first
                threshold = float(value)

                # Handle percentage conversion (0.8 -> 80)
                if threshold <= 1.0:
                    threshold = threshold * 100
                    settings[field] = threshold  # Update the original

                if not 0 <= threshold <= 100:
                    errors.append(f"{field} must be between 0 and 100 (got {threshold})")
            except (ValueError, TypeError):
                errors.append(f"{field} must be a number")

        elif field == 'rounding':
            try:
                rounding = int(float(value))  # Convert via float first
                if rounding <= 0:
                    errors.append(f"{field} must be a positive integer")
                settings[field] = rounding  # Update the original
            except (ValueError, TypeError):
                errors.append(f"{field} must be a positive integer")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )
def validate_truck_info(truck: Dict[str, Any]) -> ValidationResult:
    """Validate truck information with type conversion"""

    errors = []
    warnings = []

    if not isinstance(truck, dict):
        return ValidationResult(
            is_valid=False,
            error="truck must be a dictionary"
        )

    # Check capacity fields with type conversion
    for field in ['maxWeight', 'maxLength']:
        if field in truck and truck[field] is not None:
            try:
                value = float(truck[field])
                if value <= 0:
                    # Allow zero values but convert them to None (unlimited)
                    if value == 0:
                        truck[field] = None  # Convert 0 to None
                        warnings.append(f"{field} set to unlimited (was 0)")
                    else:
                        errors.append(f"{field} must be positive")
                else:
                    truck[field] = value  # Ensure it's stored as number
            except (ValueError, TypeError):
                errors.append(f"{field} must be a number")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )

def validate_load_info(load: Dict[str, Any]) -> ValidationResult:
    """Validate load information with better origin/destination handling"""

    errors = []
    warnings = []

    if not isinstance(load, dict):
        return ValidationResult(
            is_valid=False,
            error="load must be a dictionary"
        )

    if 'rateInfo' not in load or not load['rateInfo']:
        load['rateInfo'] = {
            "minimumRate": 1500,  # Default minimum
            "maximumRate": 3000   # Default maximum
        }
        warnings.append("Added default rate range for negotiation")

    # Check for origin/destination - they might be missing from the current data
    # We'll create them from equipment_type if needed
    if 'origin' not in load or not load['origin']:
        # For this specific case, we can derive from the subject line or equipment type
        if load.get('equipment_type') == 'PO':  # Power Only
            warnings.append("Missing origin - will need to be provided in email")
        else:
            errors.append("Missing required field: origin")

    if 'destination' not in load or not load['destination']:
        if load.get('equipment_type') == 'PO':  # Power Only
            warnings.append("Missing destination - will need to be provided in email")
        else:
            errors.append("Missing required field: destination")

    # If we have origin/destination, validate their structure
    for location_field in ['origin', 'destination']:
        if location_field in load and load[location_field]:
            location = load[location_field]
            if not isinstance(location, dict):
                errors.append(f"{location_field} must be a dictionary")
                continue

            for field in ['city', 'stateProv']:
                if field not in location or not location[field]:
                    errors.append(f"Missing {field} in {location_field}")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )
def validate_email_thread(emails: List[Dict[str, Any]]) -> ValidationResult:
    """Validate email thread structure"""

    errors = []
    warnings = []

    if not isinstance(emails, list):
        return ValidationResult(
            is_valid=False,
            error="emails must be a list"
        )

    if len(emails) == 0:
        return ValidationResult(
            is_valid=False,
            error="emails list cannot be empty"
        )

    # Validate each email
    for i, email in enumerate(emails):
        if not isinstance(email, dict):
            errors.append(f"Email {i} must be a dictionary")
            continue

        # Check required email fields
        required_email_fields = ['subject', 'body', 'from']
        for field in required_email_fields:
            if field not in email:
                errors.append(f"Email {i} missing required field: {field}")

        # Validate 'from' field structure
        if 'from' in email and email['from']:
            from_field = email['from']
            if not isinstance(from_field, list):
                errors.append(f"Email {i} 'from' field must be a list")
            elif len(from_field) == 0:
                errors.append(f"Email {i} 'from' field cannot be empty")
            else:
                for j, sender in enumerate(from_field):
                    if not isinstance(sender, dict):
                        errors.append(f"Email {i} sender {j} must be a dictionary")
                    elif 'email' not in sender:
                        errors.append(f"Email {i} sender {j} missing email field")

    if len(emails) > 50:
        warnings.append("Very long email thread (>50 emails) may impact processing performance")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )

def validate_load_processable(load_info: LoadInfo) -> bool:
    """
    Check if a load is in a state that can be processed.

    Args:
        load_info: Load information to validate

    Returns:
        True if the load can be processed
    """
    # Handle status as string (not enum)
    status = load_info.status
    if hasattr(status, 'value'):
        status = status.value

    return (
        status != "cancelled"
        and not load_info.warnings
        and not load_info.email_history.suspicious_email_type
        # and not load_info.email_history.critical_questions
        and load_info.email_history.negotiation_step not in [4, 5]  # FAILED, SUCCEEDED
    )

def validate_rate_range(min_rate: float, max_rate: float) -> ValidationResult:
    """
    Validate a rate range for negotiation.

    Args:
        min_rate: Minimum acceptable rate
        max_rate: Maximum rate willing to pay

    Returns:
        ValidationResult with validation status
    """
    errors = []
    warnings = []

    # Check types
    try:
        min_rate = float(min_rate)
        max_rate = float(max_rate)
    except (ValueError, TypeError):
        return ValidationResult(
            is_valid=False,
            error="Rates must be numeric values"
        )

    # Check positive values
    if min_rate <= 0:
        errors.append("Minimum rate must be positive")

    if max_rate <= 0:
        errors.append("Maximum rate must be positive")

    # Check range order
    if min_rate >= max_rate:
        errors.append("Minimum rate must be less than maximum rate")

    # Check reasonable ranges
    if min_rate < 100:
        warnings.append("Minimum rate seems very low (< $100)")

    if max_rate > 50000:
        warnings.append("Maximum rate seems very high (> $50,000)")

    # Check range spread
    if max_rate > 0 and min_rate > 0:
        range_ratio = max_rate / min_rate
        if range_ratio > 3:
            warnings.append("Rate range is very wide (max > 3x min)")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )
