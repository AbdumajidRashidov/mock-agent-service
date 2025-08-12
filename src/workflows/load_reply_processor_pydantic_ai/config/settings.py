"""Application settings for freight processor"""

import os
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
env_path = Path(__file__).resolve().parent.parent.parent.parent.parent / '.env'

load_dotenv(dotenv_path=env_path)


class FreightProcessorSettings(BaseModel):
    """Configuration settings for the freight processor"""

    # AI Model settings - Only Azure OpenAI
    azure_openai_api_key: str = Field(description="Azure OpenAI API key")
    azure_openai_endpoint: str = Field(description="Azure OpenAI endpoint")
    azure_openai_deployment: str = Field(description="Azure OpenAI deployment name")
    azure_openai_api_version: str = Field(description="Azure OpenAI API version")

    # Processing settings - Static configuration
    processing_config: Dict[str, Any] = Field(default_factory=lambda: {
        "email": {
            "max_word_count": 2000,
            "min_word_count": 2,
            "enable_html_parsing": True,
            "remove_signatures": True,
            "extract_quoted_text": True
        },
        "rates": {
            "min_rate": 100.0,
            "max_rate": 50000.0,
            "min_weight": 100.0,
            "max_weight": 80000.0,
            "default_rounding": 25
        },
        "negotiation": {
            "timeout_hours": 24,
            "max_rounds": 5,
            "enable_optimization": True
        },
        "ai": {
            "confidence_threshold": 0.7,
            "max_retries": 3,
            "retry_delay": 1.0,
            "enable_fallback": True
        },
        "features": {
            "advanced_extraction": True,
            "sentiment_analysis": False,
            "auto_booking": False,
            "performance_monitoring": True,
            "plugin_logging": True
        },
        "logging": {
            "level": "INFO",
            "enable_plugin_logging": True,
            "enable_performance_monitoring": True
        }
    })

    class Config:
        case_sensitive = False


@lru_cache()
def get_settings() -> FreightProcessorSettings:
    """
    Get application settings from environment variables.
    Loads from .env file if present, otherwise from system environment.

    Returns:
        FreightProcessorSettings instance

    Raises:
        ValueError: If required Azure OpenAI environment variables are missing
    """
    # Get required Azure OpenAI settings from environment
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
    azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")

    if not azure_api_key:
        raise ValueError("AZURE_OPENAI_API_KEY environment variable is required")

    if not azure_endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")

    return FreightProcessorSettings(
        azure_openai_api_key=azure_api_key,
        azure_openai_endpoint=azure_endpoint,
        azure_openai_deployment=azure_deployment,
        azure_openai_api_version=azure_api_version
    )


def get_model_config() -> Dict[str, str]:
    """
    Get AI model configuration for Azure OpenAI.

    Returns:
        Model configuration dictionary
    """
    settings = get_settings()

    return {
        "provider": "azure",
        "model": settings.azure_openai_deployment,
        "api_key": settings.azure_openai_api_key,
        "endpoint": settings.azure_openai_endpoint,
        "api_version": settings.azure_openai_api_version
    }

def get_processing_config() -> Dict[str, Any]:
    """
    Get processing configuration settings.

    Returns:
        Processing configuration dictionary
    """
    settings = get_settings()
    return settings.processing_config
