"""Agent tools for freight load processing"""

from .email_classifier import classify_email_type, is_processable_email_type
from .info_extractor import extract_load_info, merge_extracted_info_with_load
from .question_handler import extract_questions, generate_answers
from .cancellation_checker import check_cancellation
from .negotiation_manager import calculate_offering_rate
from .requirements_checker import check_requirements
from .email_generator import generate_email_response
from .utils import format_email_for_ai, parse_rate_from_text, clean_email_content, extract_rate_context

# Export all tools for easy importing
__all__ = [
    # Email classification
    "classify_email_type",
    "is_processable_email_type",

    # Information extraction
    "extract_load_info",
    "extract_rate_context",
    "merge_extracted_info_with_load",

    # Question handling
    "extract_questions",
    "generate_answers",

    # Cancellation checking
    "check_cancellation",

    # Negotiation management
    "calculate_offering_rate",

    # Requirements checking
    "check_requirements",

    # Email generation
    "generate_email_response",

    # Utils
    "format_email_for_ai",
    "parse_rate_from_text",
    "clean_email_content"
]
