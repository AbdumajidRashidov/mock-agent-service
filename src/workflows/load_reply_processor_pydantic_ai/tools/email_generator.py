"""Email response generation tool"""

from typing import Optional, List
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider

from ..models.email import EmailThread, QuestionAnswer
from ..models.company import CompanyDetails
from ..models.responses import PluginResponse
from ..config.prompts import INFO_REQUEST_EMAIL_GENERATOR_SYSTEM_PROMPT, NEGOTIATION_EMAIL_GENERATOR_SYSTEM_PROMPT
from ..config.settings import get_model_config

class EmailGenerationRequest(BaseModel):
    """Request for email generation"""

    missing_info: Optional[List[str]] = None
    questions_and_answers: Optional[List[QuestionAnswer]] = None
    email_thread: EmailThread
    offering_rate: Optional[float] = None

class GeneratedEmail(BaseModel):
    """Generated email response"""

    email_body: str
    email_type: str  # "info_request" or "negotiation"
    confidence_score: Optional[float] = None

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

# Initialize email generator agents
info_request_agent = Agent(
    model=get_azure_openai_model(),
    system_prompt=INFO_REQUEST_EMAIL_GENERATOR_SYSTEM_PROMPT,
    result_type=GeneratedEmail,
)

negotiation_agent = Agent(
    model=get_azure_openai_model(),
    system_prompt=NEGOTIATION_EMAIL_GENERATOR_SYSTEM_PROMPT,
    result_type=GeneratedEmail,
)

async def generate_email_response(
    email_thread: EmailThread,
    company_details: CompanyDetails,
    missing_info: Optional[List[str]] = None,
    questions_and_answers: Optional[List[QuestionAnswer]] = None,
    offering_rate: Optional[float] = None
) -> PluginResponse:
    """
    Generate an email response based on conversation context.
    FIXED VERSION - Better logic for different scenarios.

    Args:
        email_thread: Email conversation thread
        company_details: Company information for signature
        missing_info: List of missing information to request
        questions_and_answers: Q&A pairs to include in response
        offering_rate: Rate to offer if this is a negotiation email

    Returns:
        PluginResponse containing generated email
    """
    try:
        # Determine email type and priority
        is_rate_negotiation = offering_rate is not None
        has_questions_to_answer = questions_and_answers and any(qa.is_answered() for qa in questions_and_answers)
        has_missing_info = missing_info and len(missing_info) > 0

        # Use appropriate agent based on scenario
        if is_rate_negotiation:
            agent = negotiation_agent
            email_type = "negotiation"
        else:
            agent = info_request_agent
            email_type = "info_request"

        # Build the request context with BETTER logic
        context = _build_enhanced_email_context(
            email_thread=email_thread,
            missing_info=missing_info,
            questions_and_answers=questions_and_answers,
            offering_rate=offering_rate,
            email_type=email_type
        )

        # Generate the email
        result = await agent.run(context)

        # Add company signature
        full_email = _add_company_signature(result.data.email_body, company_details)

        return PluginResponse(
            plugin_name="email_generator",
            success=True,
            extracted_data=full_email,
            response={
                "email_type": email_type,
                "confidence_score": result.data.confidence_score,
                "raw_body": result.data.email_body
            }
        )

    except Exception as e:
        return PluginResponse(
            plugin_name="email_generator",
            success=False,
            error_message=str(e),
            extracted_data=None
        )

def _build_enhanced_email_context(
    email_thread: EmailThread,
    missing_info: Optional[List[str]] = None,
    questions_and_answers: Optional[List[QuestionAnswer]] = None,
    offering_rate: Optional[float] = None,
    email_type: str = "info_request"
) -> str:
    """Build enhanced context for email generation with better logic"""

    context_data = {}

    # Get the broker's latest email for context
    latest_broker_email = email_thread.get_latest_broker_message()
    broker_content = latest_broker_email.get_plain_content() if latest_broker_email else ""

    # Add email thread context
    emails_data = []
    for msg in email_thread.messages:
        sender_type = "user (dispatcher)" if msg.is_from_dispatcher else "broker"
        emails_data.append({
            "subject": msg.subject,
            "body": msg.content.plain_text if msg.content else msg.body,
            "from": sender_type
        })
    context_data["emails"] = emails_data

    if email_type == "negotiation":
        # NEGOTIATION EMAIL - Focus on rate counter-offer
        context_data["rate_we_ask_if_broker_can_offer"] = offering_rate
        context_data["scenario"] = "rate_negotiation"

        # Only include critical missing info for negotiations
        if missing_info:
            critical_missing = [info for info in missing_info if "delivery" in info.lower() or "pickup" in info.lower()]
            if critical_missing:
                context_data["missing_info"] = critical_missing

    else:
        # INFO REQUEST EMAIL - Handle questions and missing info
        context_data["scenario"] = "info_request"

        # Add answered questions
        if questions_and_answers:
            qa_list = []
            for qa in questions_and_answers:
                if qa.is_answered():  # Only include answered questions
                    qa_dict = {
                        "question": qa.question,
                        "answer": qa.answer
                    }
                    qa_list.append(qa_dict)

            if qa_list:
                context_data["questions_asked_by_broker_in_received_email_and_answers_to_include_generating_email"] = qa_list

        # Add missing info - but filter out redundant requests
        if missing_info:
            # Filter out info that's already been provided
            filtered_missing = _filter_redundant_missing_info(missing_info, broker_content)
            if filtered_missing:
                context_data["missing_info"] = filtered_missing

    # Convert to JSON string for the AI
    import json
    return json.dumps(context_data, indent=2)

def _add_company_signature(email_body: str, company_details: CompanyDetails) -> str:
    """Add company signature to the email"""

    # The email body from AI should not contain greeting/signature
    # We add the full template here

    signature_parts = ["Hello", "", email_body, ""]

    # Add company signature
    if company_details.name:
        signature_parts.append(f"Best Regards\n{company_details.name}")
    else:
        signature_parts.append("Best Regards")

    if company_details.mc_number:
        signature_parts.append(f"MC #{company_details.mc_number}")

    signature_parts.append("Powered by Numeo")

    return "\n".join(signature_parts)

def _filter_redundant_missing_info(missing_info: List[str], broker_content: str) -> List[str]:
    """Filter out missing info that broker already provided"""

    filtered = []
    broker_lower = broker_content.lower()

    for info in missing_info:
        info_lower = info.lower()

        # Skip if broker already provided this info
        if "commodity" in info_lower:
            # Check if broker mentioned what they're shipping
            if not any(word in broker_lower for word in ["electronics", "steel", "food", "parts", "goods", "product"]):
                filtered.append(info)

        elif "weight" in info_lower:
            # Check if broker mentioned weight
            if not any(word in broker_lower for word in ["lbs", "pounds", "kg", "ton"]):
                filtered.append(info)

        elif "delivery" in info_lower:
            # Check if broker gave specific delivery appointment (not just "by Wednesday")
            if "delivery" in broker_lower or "deliver" in broker_lower:
                # If they said "by 6PM" but no specific appointment, ask for appointment
                if "appointment" not in broker_lower and "schedule" not in broker_lower:
                    filtered.append("specific delivery appointment time")
            else:
                filtered.append(info)

        else:
            filtered.append(info)

    return filtered
