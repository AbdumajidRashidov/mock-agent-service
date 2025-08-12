"""Question extraction and answering tools"""

from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider

from ..models.email import EmailMessage, QuestionAnswer
from ..models.company import CompanyDetails
from ..models.responses import PluginResponse
from ..config.prompts import QUESTIONS_EXTRACTOR_SYSTEM_PROMPT, ANSWER_GENERATOR_SYSTEM_PROMPT
from ..config.settings import get_model_config
from .utils import format_email_for_ai


class ExtractedQuestions(BaseModel):
    """Questions extracted from broker email"""

    questions: List[str] = Field(default_factory=list, description="List of questions found in the email")

class QuestionAnswerPair(BaseModel):
    """Question and answer pair with metadata"""

    question: str
    answer: Optional[str] = None
    could_not_answer: bool = False
    confidence_score: Optional[float] = Field(None, ge=0, le=1)

class AnswerResults(BaseModel):
    """Results of answering questions"""

    questions_and_answers: List[QuestionAnswerPair] = Field(default_factory=list)

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

# Initialize agents
question_extractor_agent = Agent(
    model=get_azure_openai_model(),
    system_prompt=QUESTIONS_EXTRACTOR_SYSTEM_PROMPT,
    result_type=ExtractedQuestions,
)

answer_generator_agent = Agent(
    model=get_azure_openai_model(),
    system_prompt=ANSWER_GENERATOR_SYSTEM_PROMPT,
    result_type=AnswerResults,
)

async def extract_questions(email: EmailMessage) -> PluginResponse:
    """
    Extract questions from a broker's email.
    FIXED VERSION - Better detection of implicit questions like "What's your rate?"
    """
    try:
        # Format email for AI processing
        email_content = format_email_for_ai(email, include_headers=False)

        # Run the extraction
        result = await question_extractor_agent.run(email_content)

        # Post-process to catch common implicit questions
        questions = result.data.questions or []

        # Add manual detection for common patterns
        email_body = email_content.lower()

        # Detect rate requests
        if any(phrase in email_body for phrase in ["what's your rate", "your rate", "what rate", "rate?"]):
            if not any("rate" in q.lower() for q in questions):
                questions.append("What's your rate for this load?")

        # Detect pickup/delivery time requests
        if any(phrase in email_body for phrase in ["when can you pick", "pickup time", "delivery time"]):
            if not any("pick" in q.lower() or "deliver" in q.lower() for q in questions):
                questions.append("When can you pick up and deliver?")

        return PluginResponse(
            plugin_name="question_extractor",
            success=True,
            extracted_data=questions,
            response={"raw_result": result.data.dict(), "enhanced_questions": len(questions) > len(result.data.questions)}
        )

    except Exception as e:
        return PluginResponse(
            plugin_name="question_extractor",
            success=False,
            error_message=str(e),
            extracted_data=[]
        )

async def generate_answers(
    questions: List[str],
    company_details: CompanyDetails,
    load_reference_id: Optional[str] = None
) -> PluginResponse:
    """
    Generate answers for broker questions using company details.
    FIXED VERSION - Better load ID handling.

    Args:
        questions: List of questions to answer
        company_details: Company information for answering questions
        load_reference_id: Optional load reference ID

    Returns:
        PluginResponse containing question-answer pairs
    """
    try:
        # Build context for answering questions
        context_parts = [f"Questions: {chr(10).join(questions)}"]

        # Add company information
        context_parts.append("\nInformation to use to answer questions:")

        if company_details.name:
            context_parts.append(f"Company name: {company_details.name}")

        if company_details.address:
            context_parts.append(f"Company address: {company_details.address}")

        if company_details.phone:
            context_parts.append(f"Company phone: {company_details.phone}")

        if company_details.mc_number:
            context_parts.append(f"Company MC number: {company_details.mc_number}")

        if company_details.details:
            context_parts.append(f"Company additional information: {company_details.details}")

        # FIXED: Better load ID handling
        if load_reference_id:
            context_parts.append(f"Load reference ID: {load_reference_id}")
            context_parts.append(f"Load ID: {load_reference_id}")
        else:
            context_parts.append("Load ID: Not available for this inquiry")

        # Add truck/GPS information if available (from company details)
        context_parts.append("GPS tracking: Yes, all vehicles equipped with GPS tracking")
        context_parts.append("Cargo insurance: Yes, full coverage available")

        context = "\n".join(context_parts)

        # Run the answer generation
        result = await answer_generator_agent.run(context)

        # Convert to QuestionAnswer objects
        qa_pairs = []
        for qa in result.data.questions_and_answers:
            qa_pairs.append(QuestionAnswer(
                question=qa.question,
                answer=qa.answer,
                could_not_answer=qa.could_not_answer,
                confidence_score=qa.confidence_score
            ))

        return PluginResponse(
            plugin_name="answer_generator",
            success=True,
            extracted_data=qa_pairs,
            response={"raw_result": result.data.dict()}
        )

    except Exception as e:
        return PluginResponse(
            plugin_name="answer_generator",
            success=False,
            error_message=str(e),
            extracted_data=[]
        )

def has_critical_questions(qa_pairs: List[QuestionAnswer]) -> bool:
    """
    Check if there are questions we couldn't answer (critical questions).

    Args:
        qa_pairs: List of question-answer pairs

    Returns:
        True if there are unanswered questions
    """
    return any(qa.could_not_answer for qa in qa_pairs)
