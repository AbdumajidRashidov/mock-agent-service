# Updated filters/email_filter.py
"""
Email filter for checking fraud emails in load comment.
Simplified to use only AI analysis.
"""

import logging
import os
import asyncio
from typing import Optional
from openai import AsyncAzureOpenAI

from ..models import FilterResult, FilterSeverity, LoadInfo
from ..ai.prompts import EMAIL_FRAUD_FILTER_PROMPT
from ..ai.parsers import parse_email_fraud_filter_response

logger = logging.getLogger(__name__)


async def mock_azure_openai_call(model_name, messages, temperature, response_format):
    """Mock Azure OpenAI call with 3-second timeout - always returns static response"""
    print("Using mock Azure OpenAI for email fraud filter - simulating 3s delay")
    await asyncio.sleep(3.0)  # 3-second timeout simulation

    # Mock response object
    class MockChoice:
        def __init__(self):
            self.message = MockMessage()

    class MockMessage:
        def __init__(self):
            # Always return that no fraud was detected (safe response)
            self.content = '{"is_fraud": false, "confidence": 0.1, "reason": "No fraud indicators detected in load comments (static mock response)", "fraud_type": null}'

    class MockResponse:
        def __init__(self):
            self.choices = [MockChoice()]

    return MockResponse()


class EmailFraudFilter:
    """Filter to check for potential email fraud in load comments."""

    def __init__(self, azure_client: AsyncAzureOpenAI):
        self.azure_client = azure_client
        self.filter_type = "email_fraud"
        # Get the actual deployment name from environment
        self.model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")

    async def check_email_fraud(
        self,
        load: LoadInfo,
        custom_prompt: Optional[str] = None
    ) -> FilterResult:
        """
        Check if load contains fraud email using AI only.
        """
        try:
            # Quick check - if no load comment, skip analysis
            if not load.comments:
                return FilterResult(
                    warnings=[],
                    filter_type=self.filter_type,
                    severity=FilterSeverity.WARNING,
                    details={"reason": "no_load_comment"}
                )

            # Use mock AI for analysis instead of real API
            prompt = custom_prompt.format(
                load_comments=load.comments,
            ) if custom_prompt else EMAIL_FRAUD_FILTER_PROMPT.format(
                load_comments=load.comments,
            )

            # Use mock Azure OpenAI call instead of real API
            response = await mock_azure_openai_call(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a fraud analyst checking for email fraud."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            response_text = response.choices[0].message.content
            return parse_email_fraud_filter_response(response_text, self.filter_type)

        except Exception as e:
            logger.error(f"Error in email fraud filter: {str(e)}")
            # Return a warning result instead of re-raising
            return FilterResult(
                warnings=[f"AI service error in email fraud filter: {str(e)}"],
                filter_type=self.filter_type,
                severity=FilterSeverity.WARNING,
                details={"error": str(e)}
            )
