"""Fixed negotiation_manager.py - Handles dict rate negotiation settings properly"""

from typing import Optional, Dict, Any
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider

from ..models.company import CompanyDetails
from ..config.prompts import NEGOTIATION_STATUS_CHECKER_SYSTEM_PROMPT
from ..config.settings import get_model_config
from ..utils.constants import NegotiationStep as ConstNegotiationStep
from ..utils.rate_calculator import calculate_strategic_rate

class NegotiationStatusResult(BaseModel):
    """Result of negotiation status check"""

    is_approved: bool
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


# Initialize negotiation status checker agent
negotiation_status_agent = Agent(
    model=get_azure_openai_model(),
    system_prompt=NEGOTIATION_STATUS_CHECKER_SYSTEM_PROMPT,
    result_type=NegotiationStatusResult,
)

def calculate_offering_rate(
    load_data: Dict[str, Any],
    company_details: CompanyDetails,
    current_step: Optional[int] = None
) -> Optional[float]:
    """
    ENHANCED: Use new strategic rate calculation
    """
    # Get rate info from load
    rate_info_dict = load_data.get("rateInfo", {})
    min_rate = rate_info_dict.get("minimumRate")
    max_rate = rate_info_dict.get("maximumRate")

    if not min_rate or not max_rate or min_rate >= max_rate:
        return None

    if not company_details.has_negotiation_settings():
        return None

    # Get current negotiation step
    if current_step is None:
        current_step = load_data.get("emailHistory", {}).get("negotitationStep", ConstNegotiationStep.FIRST_BID.value)

    # Get negotiation settings
    rate_negotiation = company_details.rate_negotiation
    if isinstance(rate_negotiation, dict):
        first_threshold = rate_negotiation.get("firstBidThreshold", 75)
        second_threshold = rate_negotiation.get("secondBidThreshold", 50)
        rounding = rate_negotiation.get("rounding", 25)
    else:
        first_threshold = rate_negotiation.first_bid_threshold
        second_threshold = rate_negotiation.second_bid_threshold
        rounding = rate_negotiation.rounding

    # Use enhanced strategic calculation
    return calculate_strategic_rate(
        min_rate, max_rate, current_step,
        first_threshold, second_threshold, rounding
    )
