from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.chat_models import init_chat_model
from ..utils.convert_emails_to_messages import get_conversation_context
from ..const import EmailHistoryStatus
from langgraph.errors import NodeInterrupt

class RateAnalysisResponse(BaseModel):
    """Response model for rate analysis."""
    status: Literal["accepted", "rejected", "only_question_asked"] = Field(..., description="The status of the rate analysis: 'accepted', 'rejected', or 'only_question_asked'")
    broker_rate: Optional[int] = Field(None, description="The latest rate broker agreed to")
    reasoning: str = Field(..., description="Explanation of the analysis")

RATE_ANALYSIS_PROMPT = """You are a freight rate negotiation expert analyzing broker responses. You'll be provided with messages of an email thread, and where a dispatcher has been trying to negotiate a rate for a load and the broker has responded to his offer.

Analyze the broker's message and determine:
1. If they have explicitly or implicitly accepted our rate
2. If they have countered with a different rate

Important notes about broker behavior:
- Brokers are paying money, so they will typically try to negotiate a lower rate
- They rarely say "too low" as they want to pay less
- They often counter with a higher rate than their initial offer
- They might accept if our rate is close to their target

Consider these STRONG indicators of rate acceptance (any of these should be considered acceptance):
- Explicit acceptance ("we accept", "that works", "book it", "confirmed", "agreed", "let's cover it")
- Positive confirmation ("sounds good", "let's do it", "perfect", "great")
- Requesting next steps ("send BOL", "what's next", "proceed")
- Agreement without countering ("okay", "proceed", "go ahead")
- Any positive response without a counter offer

Consider these indicators of a counteroffer (only if no acceptance indicators are present):
- Mentioning a specific rate ("can you do $X", "our rate is $X", "how about $X", "we can do $X", "can you go lower", "what's your best rate", "No, I can do $X")

Your response has to be like this (reference only):
{
    status: "accepted" | "rejected" | "only_question_asked" (if broker just asked question like "what's your MC ?" it's not either acceptance or rejection, so status has to be "only_question_asked", but if it's like "$X is my best, btw what's your mc ?", it's rejection because it's not only asking questions, it's also rejecting our offer),
    broker_rate: number | null (if broker accepted our offer, this will be the latest rate we've offered, if it's rejected and broker offered rate, it'll broker's latest offered rate),
    reasoning: string (explain why you chose this status)
}


Respond with your analysis, including the broker's counter rate if provided."""

def create_rate_analyzer_llm():
    """Create an LLM instance for rate analysis with structured output."""
    llm = init_chat_model(
        "azure_openai:gpt-4o",
        temperature=0.3
    )
    return llm.with_structured_output(RateAnalysisResponse)

def analyze_rate(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """Analyze broker's response to determine if they accepted/rejected the rate.

    Args:
        state: Current workflow state
        llm: Initialized LLM with structured output

    Returns:
        Updated state with rate analysis
    """
    messages = [
        SystemMessage(RATE_ANALYSIS_PROMPT),
        HumanMessage(f"Email messages:\n\n{get_conversation_context(state)}")
    ]

    # analysis = llm.invoke(messages)
    analysis = {
        "status": "accepted",
        "broker_rate": 1000,
        "reasoning": "Broker accepted our rate"
    }

    if analysis.status == "accepted" and analysis.broker_rate:
        state["updated_load_fields"]["rateInfo.rateUsd"] = analysis.broker_rate
        if state.get("load_info", {}).get("emailHistory", {}).get("status") == EmailHistoryStatus.get("OFFERED_FIRST_BID"):
            state["updated_load_fields"]["emailHistory.status"] = EmailHistoryStatus.get("FIRST_BID_ACCEPTED")
        else:
            state["updated_load_fields"]["emailHistory.status"] = EmailHistoryStatus.get("SECOND_BID_ACCEPTED")
    elif analysis.status == "rejected":
        if state.get("load_info", {}).get("emailHistory", {}).get("status") == EmailHistoryStatus.get("OFFERED_FIRST_BID"):
            state["updated_load_fields"]["emailHistory.status"] = EmailHistoryStatus.get("FIRST_BID_REJECTED")
        else:
            state["updated_load_fields"]["emailHistory.status"] = EmailHistoryStatus.get("SECOND_BID_REJECTED")

    if state.get("updated_load_fields", {}).get("emailHistory.status") == EmailHistoryStatus.get("FIRST_BID_REJECTED"):
        current_rate = int(state.get("load_info", {}).get("rateInfo", {}).get("rate"))
        if not current_rate:
            raise NodeInterrupt("Current rate is required for negotiation email generation")

        if current_rate >= 3000:
            next_proposing_rate = current_rate + 250
        elif current_rate < 3000 and current_rate >= 2000:
            next_proposing_rate = current_rate + 200
        elif current_rate < 2000 and current_rate >= 1000:
            next_proposing_rate = current_rate + 150
        else:
            next_proposing_rate = current_rate + 100

        next_proposing_rate = int(round(next_proposing_rate / 50) * 50)

        if analysis.broker_rate and next_proposing_rate <= analysis.broker_rate:
            state["updated_load_fields"]["emailHistory.status"] = EmailHistoryStatus.get("BLOCKED")
            raise NodeInterrupt("Broker offered higher rate than our next proposing rate")

    return state
