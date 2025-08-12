"""Configuration for Pydantic AI freight processor"""

from .settings import get_settings, FreightProcessorSettings
from .prompts import *

__all__ = [
    "get_settings",
    "FreightProcessorSettings",
    # Prompts
    "FREIGHT_AGENT_SYSTEM_PROMPT",
    "EMAIL_CLASSIFIER_SYSTEM_PROMPT",
    "INFO_EXTRACTOR_SYSTEM_PROMPT",
    "QUESTIONS_EXTRACTOR_SYSTEM_PROMPT",
    "ANSWER_GENERATOR_SYSTEM_PROMPT",
    "CANCELLATION_CHECKER_SYSTEM_PROMPT",
    "NEGOTIATION_STATUS_CHECKER_SYSTEM_PROMPT",
    "REQUIREMENTS_CHECKER_SYSTEM_PROMPT",
    "INFO_REQUEST_EMAIL_GENERATOR_SYSTEM_PROMPT",
    "NEGOTIATION_EMAIL_GENERATOR_SYSTEM_PROMPT"
]
