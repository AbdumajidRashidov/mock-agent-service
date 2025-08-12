
"""
Response parsers for AI filter outputs.
Clean, type-safe parsing of AI responses into FilterResult objects.
"""

import json
import logging
from typing import Dict, Any
from ..models import FilterResult, FilterSeverity

logger = logging.getLogger(__name__)


class ResponseParsingError(Exception):
    """Raised when AI response cannot be parsed properly."""
    pass


def safe_parse_json(response_text: str) -> Dict[str, Any]:
    """Safely parse JSON response with error handling."""
    try:
        # Remove any potential markdown formatting
        cleaned = response_text.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {response_text}")
        return {}


def parse_material_filter_response(response_text: str, filter_type: str) -> FilterResult:
    """Parse material filter AI response into FilterResult."""
    try:
        data = safe_parse_json(response_text)

        if data.get("has_issues", False):
            return FilterResult(
                warnings=data.get("warnings", []),
                filter_type=filter_type,
                severity=FilterSeverity.WARNING,
                details=data
            )

        # No restricted materials found
        return FilterResult(
            warnings=[],
            filter_type=filter_type,
            severity=FilterSeverity.INFO,
            details=data
        )

    except Exception as e:
        logger.error(f"Error parsing material filter response: {str(e)}")
        return FilterResult(
            warnings=[],
            filter_type=filter_type,
            severity=FilterSeverity.INFO,
            details={"error": str(e)}
        )


def parse_permit_filter_response(response_text: str, filter_type: str) -> FilterResult:
    """Parse permit filter AI response into FilterResult."""
    try:
        data = safe_parse_json(response_text)

        if data.get("has_issues", False):
            return FilterResult(
                warnings=data.get("warnings", []),
                filter_type=filter_type,
                severity=FilterSeverity.WARNING,
                details=data
            )

        # No permit issues
        return FilterResult(
            warnings=[],
            filter_type=filter_type,
            severity=FilterSeverity.INFO,
            details=data
        )

    except Exception as e:
        logger.error(f"Error parsing permit filter response: {str(e)}")
        return FilterResult(
            warnings=[],
            filter_type=filter_type,
            severity=FilterSeverity.INFO,
            details={"error": str(e)}
        )


def parse_security_filter_response(response_text: str, filter_type: str) -> FilterResult:
    """Parse security filter AI response into FilterResult."""
    try:
        data = safe_parse_json(response_text)

        if data.get("has_issues", False):
            return FilterResult(
                warnings=data.get("warnings", []),
                filter_type=filter_type,
                severity=FilterSeverity.WARNING,
                details=data
            )

        # No security issues
        return FilterResult(
            warnings=[],
            filter_type=filter_type,
            severity=FilterSeverity.INFO,
            details=data
        )

    except Exception as e:
        logger.error(f"Error parsing security filter response: {str(e)}")
        return FilterResult(
            warnings=[],
            filter_type=filter_type,
            severity=FilterSeverity.INFO,
            details={"error": str(e)}
        )

def parse_email_fraud_filter_response(response_text: str, filter_type: str) -> FilterResult:
    """Parse email fraud filter AI response into FilterResult."""
    try:
        data = safe_parse_json(response_text)

        if data.get("has_issues", False):
            return FilterResult(
                warnings=data.get("warnings", []),
                filter_type=filter_type,
                severity=FilterSeverity.WARNING,
                details=data
            )

        # No email fraud issues
        return FilterResult(
            warnings=[],
            filter_type=filter_type,
            severity=FilterSeverity.INFO,
            details=data
        )

    except Exception as e:
        logger.error(f"Error parsing email fraud filter response: {str(e)}")
        return FilterResult(
            warnings=[],
            filter_type=filter_type,
            severity=FilterSeverity.INFO,
            details={"error": str(e)}
        )
