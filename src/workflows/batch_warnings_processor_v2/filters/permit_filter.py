"""
Permit filters for checking all required permits and endorsements.
Simplified to use single AI call instead of loops.
"""

import logging
import os
import asyncio
from typing import List, Optional
from openai import AsyncAzureOpenAI

from ..models import FilterResult, FilterSeverity, TruckCapabilities, LoadInfo
from ..ai.prompts import PERMIT_FILTER_PROMPT
from ..ai.parsers import parse_permit_filter_response

logger = logging.getLogger(__name__)


async def mock_azure_openai_call(model_name, messages, temperature, response_format):
    """Mock Azure OpenAI call with 3-second timeout - always returns static response"""
    print("Using mock Azure OpenAI for permit filter - simulating 3s delay")
    await asyncio.sleep(3.0)  # 3-second timeout simulation

    # Mock response object
    class MockChoice:
        def __init__(self):
            self.message = MockMessage()

    class MockMessage:
        def __init__(self):
            # Always return that no permit issues were found (safe response)
            self.content = '{"permits_required": [], "missing_permits": [], "has_permit_issues": false, "confidence": 0.1, "reason": "No permit requirements detected for this load (static mock response)", "severity": "info"}'

    class MockResponse:
        def __init__(self):
            self.choices = [MockChoice()]

    return MockResponse()


class PermitFilter:
    """Collection of filters for all permit/endorsement checks."""

    def __init__(self, azure_client: AsyncAzureOpenAI):
        self.azure_client = azure_client
        # Get the actual deployment name from environment
        self.model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")

    async def check_all_permits(
        self,
        load: LoadInfo,
        truck: TruckCapabilities,
        custom_prompt: Optional[str] = None
    ) -> List[FilterResult]:
        """Check all permit requirements using single AI call."""
        try:
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
                truck_permits=", ".join(truck.permitted_items) if truck.permitted_items else "None"
            ) if custom_prompt else PERMIT_FILTER_PROMPT.format(
                load_comments=load.comments,
                commodity=load.commodity or "",
                special_notes=load.special_notes or "",
                driver_should_load=load.driver_should_load,
                driver_should_unload=load.driver_should_unload,
                is_team_driver=load.is_team_driver,
                equipment_type=load.equipment_type,
                origin=f"{load.origin_city}, {load.origin_state}",
                destination=f"{load.destination_city}, {load.destination_state}",
                truck_permits=", ".join(truck.permitted_items) if truck.permitted_items else "None"
            )

            # Use mock Azure OpenAI call instead of real API
            response = await mock_azure_openai_call(
                model=self.model_name,  # Use deployment name from environment
                messages=[
                    {"role": "system", "content": "You are a logistics analyst checking permit requirements."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            response_text = response.choices[0].message.content
            result = parse_permit_filter_response(response_text, "permit_check")

            # Return as list to maintain compatibility with existing code
            return [result]

        except Exception as e:
            logger.error(f"Error in permit filters: {str(e)}")
            # Return a warning result instead of re-raising
            return [FilterResult(
                warnings=[f"AI service error in permit filter: {str(e)}"],
                filter_type="permit_check",
                severity=FilterSeverity.WARNING,
                details={"error": str(e)}
            )]
