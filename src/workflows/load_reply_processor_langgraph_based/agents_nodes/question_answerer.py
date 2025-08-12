from typing import Dict, Any
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage

class QuestionAnswerResponse(BaseModel):
    """Response model for question answerer."""
    email_to_send: str = Field(..., description="Reply email to send")

def create_question_answerer_llm():
    """Create an LLM instance for question answerer with structured output."""
    llm = init_chat_model(
        "azure_openai:gpt-4o",
        temperature=0.3
    )
    return llm.with_structured_output(QuestionAnswerResponse)


QUESTION_ANSWERER_PROMPT = """
You are a truck industry expert that analyzes replies received from brokers and understands all the industry jargon.

You've been communicating with a broker regarding a load and the broker just asked a question. Your task is to provide a concise, direct answer to their question without any additional text, signatures, or placeholders.

RULES:
1. Only provide the exact information requested, nothing more
2. Do not include any signatures, closings, or placeholders like "Best regards" or "[Your Name]"
3. Keep the response brief and to the point
4. Do not make up any information - only use what's provided in the context

Examples of questions and how to answer them:
- If asked "What's your MC?", respond with exactly: "Our company MC is {company_mc_number}"
- If asked "What's your DOT number?", respond with exactly: {company_dot_number}
- If asked "What's the load reference number?", respond with exactly: "Load reference number is {posters_reference_id}"

Remember: Only answer the specific question asked, and include only the requested information in your response.
"""

def question_answerer(state: Dict[str, Any], llm) -> Dict[str, Any]:
    company_dot_number = state.get("company_info", {}).get("dotNumber", "")

    if company_dot_number:
        company_dot_number = f" - Our company DOT number is {company_dot_number}"
    else:
        company_dot_number = ""

    messages = [
        SystemMessage(
            QUESTION_ANSWERER_PROMPT
                .format(
                    company_mc_number=state.get("company_info", {}).get("mcNumber", ""),
                    company_dot_number=company_dot_number,
                    posters_reference_id=state.get("load_info", {}).get("postersReferenceId", "")
                )
        ),
        *state["email_generator_agent_messages"],
        HumanMessage(content=state["reply"])
    ]

    # response = llm.invoke(messages)
    response = {
        "email_to_send": "Email to send"
    }

    return {"email_to_send": response["email_to_send"]}

