"""Cancellation detection tool for freight loads"""

from typing import Optional
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider

from ..models.email import EmailMessage
from ..models.responses import PluginResponse
from ..config.prompts import CANCELLATION_CHECKER_SYSTEM_PROMPT
from ..config.settings import get_model_config
from .utils import format_email_for_ai

class CancellationResult(BaseModel):
    """Result of cancellation check"""

    cancelled: bool
    confidence_score: Optional[float] = None
    reason: Optional[str] = None

def get_azure_openai_model():
    """Get configured Azure OpenAI model"""
    config = get_model_config()

    model = OpenAIModel(
        config['model'],
        provider=AzureProvider(
            azure_endpoint=config['endpoint'],
            api_version='2024-06-01',
            api_key=config['api_key'],
        ),
    )

    return model

# Initialize the cancellation checker agent
cancellation_checker_agent = Agent(
    model=get_azure_openai_model(),
    system_prompt=CANCELLATION_CHECKER_SYSTEM_PROMPT,
    result_type=CancellationResult,
)

async def check_cancellation(email: EmailMessage) -> PluginResponse:
    """
    Check if a broker's email indicates load cancellation.

    Args:
        email: Email message to check for cancellation

    Returns:
        PluginResponse containing cancellation status
    """
    try:
        # Format email for AI processing
        email_content = format_email_for_ai(email, include_headers=False)

        # Run the cancellation check
        result = await cancellation_checker_agent.run(email_content)

        return PluginResponse(
            plugin_name="cancellation_checker",
            success=True,
            extracted_data=result.data.cancelled,
            response={
                "cancelled": result.data.cancelled,
                "confidence_score": result.data.confidence_score,
                "reason": result.data.reason
            }
        )

    except Exception as e:
        return PluginResponse(
            plugin_name="cancellation_checker",
            success=False,
            error_message=str(e),
            extracted_data=False
        )
