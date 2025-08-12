"""
Material filter for checking restricted materials.
Simplified to use only AI analysis.
"""

import logging
import os
import asyncio
from typing import Optional
from openai import AsyncAzureOpenAI

from ..models import FilterResult, FilterSeverity, TruckCapabilities, LoadInfo
from ..ai.prompts import MATERIAL_FILTER_PROMPT
from ..ai.parsers import parse_material_filter_response

logger = logging.getLogger(__name__)


async def mock_azure_openai_call(model_name, messages, temperature, response_format):
    """Mock Azure OpenAI call with 3-second timeout - always returns static response"""
    print("Using mock Azure OpenAI for material filter - simulating 3s delay")
    await asyncio.sleep(3.0)  # 3-second timeout simulation

    # Mock response object
    class MockChoice:
        def __init__(self):
            self.message = MockMessage()

    class MockMessage:
        def __init__(self):
            # Always return that no restricted materials were found (safe response)
            self.content = '{"has_restricted_materials": false, "confidence": 0.1, "reason": "No restricted materials detected in load (static mock response)", "restricted_items": [], "severity": "info"}'

    class MockResponse:
        def __init__(self):
            self.choices = [MockChoice()]

    return MockResponse()


class MaterialFilter:
    """Filter to check load materials against truck restrictions."""

    def __init__(self, azure_client: AsyncAzureOpenAI):
        self.azure_client = azure_client
        self.filter_type = "restricted_materials"
        # Get the actual deployment name from environment
        self.model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")

    async def check_restricted_materials(
        self,
        load: LoadInfo,
        truck: TruckCapabilities,
        custom_prompt: Optional[str] = None
    ) -> FilterResult:
        """
        Check if load contains restricted materials using AI only.
        """
        try:
            # Quick check - if no restrictions, skip analysis
            if not truck.restrictions:
                return FilterResult(
                    warnings=[],
                    filter_type=self.filter_type,
                    severity=FilterSeverity.INFO,
                    details={"reason": "no_restrictions"}
                )

            # Use mock AI for analysis instead of real API
            prompt = custom_prompt.format(
                load_comments=load.comments,
                commodity=load.commodity or "",
                special_notes=load.special_notes or "",
                driver_should_load=load.driver_should_load,
                driver_should_unload=load.driver_should_unload,
                is_team_driver=load.is_team_driver,
                equipment_type=load.equipment_type,
                truck_restrictions=", ".join(truck.restrictions)
            ) if custom_prompt else MATERIAL_FILTER_PROMPT.format(
                load_comments=load.comments,
                commodity=load.commodity or "",
                special_notes=load.special_notes or "",
                driver_should_load=load.driver_should_load,
                driver_should_unload=load.driver_should_unload,
                is_team_driver=load.is_team_driver,
                equipment_type=load.equipment_type,
                truck_restrictions=", ".join(truck.restrictions)
            )

            # Use mock Azure OpenAI call instead of real API
            response = await mock_azure_openai_call(
                model=self.model_name,  # Use deployment name from environment
                messages=[
                    {"role": "system", "content": "You are a logistics analyst checking material restrictions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            response_text = response.choices[0].message.content
            return parse_material_filter_response(response_text, self.filter_type)

        except Exception as e:
            logger.error(f"Error in material filter: {str(e)}")
            # Return a warning result instead of re-raising
            return FilterResult(
                warnings=[f"AI service error in material filter: {str(e)}"],
                filter_type=self.filter_type,
                severity=FilterSeverity.WARNING,
                details={"error": str(e)}
            )
