"""Utilities for freight processing"""

from .email_parser import parse_email_messages, convert_email_dict_to_message
from .rate_calculator import validate_rate_range
from .validation import validate_inputs, validate_load_processable
from .constants import NegotiationStep, RateOfferer, EmailType
from .exceptions import FreightProcessingError

__all__ = [
    # Email parsing
    "parse_email_messages",
    "convert_email_dict_to_message",

    # Rate calculation
    "evaluate_broker_offer",
    "calculate_strategic_rate",
    "validate_rate_range",

    # Validation
    "validate_inputs",
    "validate_load_processable",

    # Constants
    "NegotiationStep",
    "RateOfferer",
    "EmailType",

    # Exceptions
    "FreightProcessingError",
]
