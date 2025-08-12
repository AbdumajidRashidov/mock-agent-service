from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.chat_models import init_chat_model
from pydantic import BaseModel
from langgraph.errors import NodeInterrupt
from ..const import EmailHistoryStatus

class LoadCancellationCheckerResponse(BaseModel):
    """Response model for the load cancellation checker."""
    is_cancelled: bool
    proof: str = ""

LOAD_CANCELLATION_CHECK_PROMPT = """
You are a truck industry expert that analyzes broker replies to determine if a load has been cancelled.

Analyze the broker's reply and determine if they are indicating that the load has been cancelled.
Consider the following indicators of cancellation:
- Explicit statements about cancellation
- References to the load no longer being available
- Mentions of the load being covered or given to another carrier
- Any other language that suggests the load is no longer available

Return a JSON object with:
- is_cancelled: boolean indicating if the load is cancelled
- proof: a brief explanation of why you came to this conclusion

ONLY mark it as cancelled when the latest email is like:
 - "it's gone"
 - "it's cancelled"
 - "it's not available"
 - "it's covered"
 - "it's given to another carrier"
 - "covered"
 - "already gone"

No need to mark it as cancelled when the latest email is like:
 - "I've cc'd my colleague who will take it from here"
 - "See posting!!!"
 - "asjhdkgvjksac" (non-sense emails)
 - "Sorry guys we can't work with you"
 - "I'm out of office"
 - "it's not my load"
"""

def create_load_cancellation_checker_llm():
    """Create an LLM instance for load cancellation checking with structured output."""
    llm = init_chat_model(
        "azure_openai:gpt-4o",
        temperature=0.3,
    )

    return llm.with_structured_output(LoadCancellationCheckerResponse)

def load_cancellation_checker(state: Dict[str, Any], llm):
    """
    Check if the broker's reply indicates load cancellation.

    Args:
        state: Current workflow state containing the broker's reply
        llm: Initialized language model with structured output

    Returns:
        Updated state
    """
    # response = llm.invoke([
    #     SystemMessage(content=LOAD_CANCELLATION_CHECK_PROMPT),
    #     HumanMessage(content=f"Broker's reply:\n{state['reply']}")
    # ])

    response = {
        "is_cancelled": False,
        "proof": ""
    }

    if response.get("is_cancelled", False):
        state["updated_load_fields"]["status"] = "cancelled"
        state["updated_load_fields"]["emailHistory.status"] = EmailHistoryStatus.get("BLOCKED")
        raise NodeInterrupt("Load cancelled")

    return state

