"""Email type classification tool for freight negotiation"""

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider

from ..models.email import EmailType, EmailMessage
from ..models.responses import PluginResponse
from ..config.prompts import EMAIL_CLASSIFIER_SYSTEM_PROMPT
from ..config.settings import get_model_config
from .utils import format_email_for_ai

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

# Initialize the email classifier agent
email_classifier_agent = Agent(
    get_azure_openai_model(),
    system_prompt=EMAIL_CLASSIFIER_SYSTEM_PROMPT,
    result_type=EmailType,
)

async def classify_email_type(email: EmailMessage) -> PluginResponse:
    """
    Classify the type of email received from a broker.

    Args:
        email: Email message to classify

    Returns:
        PluginResponse containing the classification result
    """
    try:
        # Format email for AI processing
        email_content = format_email_for_ai(email, include_headers=False)
        print(email_content, "email_content")

        # Run the classification
        result = await email_classifier_agent.run(email_content)

        # Update the email with the classification
        email.email_type = result.data

        return PluginResponse(
            plugin_name="email_classifier",
            success=True,
            extracted_data=result.data.value,
            confidence_score=getattr(result, 'confidence', None)
        )

    except Exception as e:
        return PluginResponse(
            plugin_name="email_classifier",
            success=False,
            error_message=str(e),
            extracted_data=EmailType.OTHER.value
        )

def is_processable_email_type(email_type: EmailType) -> bool:
    """
    Check if the email type is processable by our system.

    Args:
        email_type: The classified email type

    Returns:
        True if the email type should be processed
    """
    processable_types = {
        EmailType.JUST_INFO,
        EmailType.JUST_QUESTION,
        EmailType.QUESTION_AND_INFO,
        EmailType.CANCELLATION_REPORT,
        EmailType.BID
    }

    return email_type in processable_types
