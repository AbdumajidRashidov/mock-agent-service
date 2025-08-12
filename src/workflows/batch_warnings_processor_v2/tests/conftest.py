"""
Pytest configuration and shared fixtures for batch warnings processor tests.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_azure_client():
    """Mock Azure OpenAI client for testing."""
    client = AsyncMock()

    # Default successful response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "has_issues": False,
        "warnings": [],
        "severity": "info",
        "reasoning": "No issues detected"
    })

    client.chat.completions.create = AsyncMock(return_value=mock_response)
    return client

def _protobuf_to_dict(pb):
    d = {}
    if isinstance(pb, MagicMock):
        # In tests, the mock object might have mock attributes.
        # We need to extract the actual values from them.
        mock_attrs = {}
        for key, value in pb.items():
            mock_attrs[key] = value
        # If items() is not available or returns nothing, fallback to iterating spec
        if not mock_attrs and hasattr(pb, '_spec_set'):
            for key in pb._spec_set:
                if hasattr(pb, key):
                    mock_attrs[key] = getattr(pb, key)

        # A bit of a hack for performance tests where mocks are nested
        if 'origin' in mock_attrs and isinstance(mock_attrs['origin'], MagicMock):
            mock_attrs['origin'] = {
                'stateProv': mock_attrs['origin'].stateProv,
                'city': mock_attrs['origin'].city
            }
        if 'destination' in mock_attrs and isinstance(mock_attrs['destination'], MagicMock):
            mock_attrs['destination'] = {
                'stateProv': mock_attrs['destination'].stateProv,
                'city': mock_attrs['destination'].city
            }
        return mock_attrs

    if hasattr(pb, 'DESCRIPTOR'):
        # Handle Protobuf messages
        for field in pb.DESCRIPTOR.fields:
            value = getattr(pb, field.name)
            if field.type == field.TYPE_MESSAGE:
                if field.label == field.LABEL_REPEATED:
                    d[field.name] = [_protobuf_to_dict(v) for v in value]
                else:
                    d[field.name] = _protobuf_to_dict(value)
            else:
                d[field.name] = value
    return d

class AIResponseBuilder:
    """Helper class to build AI response mocks."""

    @staticmethod
    def success_response(has_issues=False, warnings=None, severity="info"):
        """Build successful AI response."""
        return json.dumps({
            "has_issues": has_issues,
            "warnings": warnings or [],
            "severity": severity,
            "reasoning": f"Analysis completed - {'issues found' if has_issues else 'clean'}"
        })

    @staticmethod
    def material_violation_response(materials):
        """Build material violation response."""
        return json.dumps({
            "has_issues": True,
            "warnings": [f"Load contains restricted material: {material}" for material in materials],
            "severity": "warning",
            "match_type": "direct",
            "reasoning": f"Found restricted materials: {', '.join(materials)}"
        })

    @staticmethod
    def permit_violation_response(permits):
        """Build permit violation response."""
        return json.dumps({
            "has_issues": True,
            "warnings": [f"Load requires {permit} permit - truck not certified" for permit in permits],
            "severity": "warning",
            "requirement_source": "explicit_load_requirement",
            "reasoning": f"Missing required permits: {', '.join(permits)}"
        })

@pytest.fixture
def ai_response_builder():
    """Provide AI response builder utility."""
    return AIResponseBuilder
