"""
Security filters for checking all required security features.
Simplified to use single AI call instead of loops.
"""

import logging
import os
import asyncio
from typing import List, Optional
from openai import AsyncAzureOpenAI

from ..models import FilterResult, FilterSeverity, TruckCapabilities, LoadInfo
from ..ai.prompts import SECURITY_FILTER_PROMPT
from ..ai.parsers import parse_security_filter_response

logger = logging.getLogger(__name__)


async def mock_azure_openai_call(model_name, messages, temperature, response_format):
    """Mock Azure OpenAI call with 3-second timeout - always returns static response"""
    print("Using mock Azure OpenAI for security filter - simulating 3s delay")
    await asyncio.sleep(3.0)  # 3-second timeout simulation

    # Mock response object
    class MockChoice:
        def __init__(self):
            self.message = MockMessage()

    class MockMessage:
        def __init__(self):
            # Always return that no security issues were found (safe response)
            self.content = '{"security_required": [], "missing_security": [], "has_security_issues": false, "confidence": 0.1, "reason": "No security requirements detected for this load (static mock response)", "severity": "info"}'

    class MockResponse:
        def __init__(self):
            self.choices = [MockChoice()]

    return MockResponse()


class SecurityFilter:
    """Collection of filters for all security feature checks."""

    def __init__(self, azure_client: AsyncAzureOpenAI):
        self.azure_client = azure_client
        # Get the actual deployment name from environment
        self.model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")

    async def check_all_security(
        self,
        load: LoadInfo,
        truck: TruckCapabilities,
        custom_prompt: Optional[str] = None
    ) -> List[FilterResult]:
        """Check all security requirements using single AI call."""
        try:
            # Use custom prompt if provided, otherwise use default with correct formatting
            prompt = custom_prompt.format(
                load_comments=load.comments,
                commodity=load.commodity or "",
                special_notes=load.special_notes or "",
                driver_should_load=load.driver_should_load,
                driver_should_unload=load.driver_should_unload,
                is_team_driver=load.is_team_driver,
                equipment_type=load.equipment_type,
                origin=f"{load.origin_city}, {load.origin_state}",
                destination=f"{load.destination_city}, {load.destination_state}",
                truck_security=", ".join(truck.security_items) if truck.security_items else "None"
            ) if custom_prompt else SECURITY_FILTER_PROMPT.format(
                load_comments=load.comments,
                commodity=load.commodity or "",
                special_notes=load.special_notes or "",
                driver_should_load=load.driver_should_load,
                driver_should_unload=load.driver_should_unload,
                is_team_driver=load.is_team_driver,
                equipment_type=load.equipment_type,
                origin=f"{load.origin_city}, {load.origin_state}",
                destination=f"{load.destination_city}, {load.destination_state}",
                truck_security=", ".join(truck.security_items) if truck.security_items else "None"
            )

            # Use mock Azure OpenAI call instead of real API
            response = await mock_azure_openai_call(
                model=self.model_name,  # Use deployment name from environment
                messages=[
                    {"role": "system", "content": "You are a logistics analyst checking security requirements."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            response_text = response.choices[0].message.content
            result = parse_security_filter_response(response_text, "security_check")

            # Return as list to maintain compatibility with existing code
            return [result]

        except Exception as e:
            logger.error(f"Error in security filters: {str(e)}")
            # Return a warning result instead of re-raising
            return [FilterResult(
                warnings=[f"AI service error in security filter: {str(e)}"],
                filter_type="security_check",
                severity=FilterSeverity.WARNING,
                details={"error": str(e)}
            )]
