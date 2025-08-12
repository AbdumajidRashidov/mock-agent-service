import logging
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from langgraph.errors import NodeInterrupt
from ..const import EmailHistoryStatus

logger = logging.getLogger(__name__)

class ReplyNecessityCheckerAgentResponse(BaseModel):
    """Response model for the reply necessity checker."""
    is_necessary: bool
    asked_critical_question: bool = Field(..., description="If broker asks any other questions except mc number, dot number, load reference number and rate, mark it as true (e.g. Where is your truck -> asked_critical_question=True (because it's not asking about mc number, dot number, load reference number or rate))")
    reason_for_is_necessary_result: str = ""
    reason_for_asked_critical_question_result: str = ""

REPLY_NECESSITY_PROMPT = """
You're a professional truck dispatcher. Your job is to analyze emails and determine if a reply is needed to the latest message received from broker in an email thread about a load.

## Email Flow
Our email flow is split into two parts, info-request and negotiation:

### Info-request flow:
1. We send email to broker:
`Hello Team!

Need details on the Ottawa, IL to Millwood, WV, 07/15/2025`

2. Broker replies:
`paying 3k, delivery date is tmr 2pm, pickup today 1pm, commodity is auto parts`

3. We reply back:
`Any special requirements or restrictions?`

4. Broker replies:
`Tarps required!!`

Now all necessary info collected, we start negotiation process:

### Negotiation flow:
5. We reply back:
`Can you make 3.5k ?`

6. Broker replies:
`3.3k is my best`

7. We reply back:
`Any chance for 3.4k ? load is also a bit heavy, also I see tarps required`

8. Broker replies:
`ok, let's do it`

Negotiation process is now completely finished.

Whole emailing process is finished, any email we receive out of this scope, we need to just skip it, no reply necessary for them, but it's important to keep replying when we're in this process.

There are specific cases where we should NOT reply to the broker. If you encounter any of these, set is_necessary=False:
1. Out of office/auto-reply messages (e.g., "I am out of the office", "I will be away")
2. Emails indicating the broker is unavailable (e.g., "on vacation", "on leave")
3. Automatic responses (e.g., "Your email has been received")
4. Emails with no actionable content (e.g., "See posting!!!", non-sense text, spam, marketing)
5. Messages indicating someone else is handling the request (e.g., "I've cc'd my colleague")
6. Non-sense emails (e.g., "asjhdkgvjksac")

## Special Notes Handling
These should be extracted to specialNotes but NOT CRITICAL QUESTIONS (set asked_critical_question=False):
- "Paid with 3rd party apps"
- "Food Grade trailer, Lumper fee"
- "need door clearance"
- Any other equipment or loading requirements

User also provides you with statuses of email flows, for example:
"info_request_finished": True
"negotiation_finished": False

## Critical vs Non-Critical Questions

### NON-CRITICAL QUESTIONS (set asked_critical_question=False)
These are routine questions that don't require escalation:
- Rate questions:
  - "What's your rate?" or "Rate?" (even if we respond "I don't see on my end")
  - "What's your best rate?" or "Best rate?"
  - "What can you do on rate?"
  - "Rate confirmation?"
- MC/DOT questions:
  - "What's your MC?" or "What's your MC#?"
  - "MC?" or "MC#?"
  - "Can you send MC?" or "Please provide MC"
  - "What's your DOT?" or "DOT?"
  - "MC/DOT?"
- Load reference questions:
  - "What's the load reference number?"
  - "Load #?" or "Reference #?"
- General interest questions:
  - "Are you interested in this load?"
  - "Are you interested?" or "Interested?"
  - "Would you like to book this load?"
  - "Is this something you can cover?"
  - "Can you cover this?"
  - "Notify me if you were able to book a load in an app"
  - "Let me know if you have any questions or concerns"

IMPORTANT: These questions should be considered NON-CRITICAL even if worded differently but with the same intent. Use your judgment to match the intent of the question to these categories.

- For all other questions, mark `asked_critical_question` as True
- Examples (reference only):

### CRITICAL QUESTIONS (set asked_critical_question=True)
These require special attention:
- "What is your quote (bid)?" -> asked_critical_question=True
- "Give me your phone number" -> asked_critical_question=True
- "Where is your truck" -> asked_critical_question=True
- "What's your phone number ?" -> asked_critical_question=True
- "What's your ETA?" -> asked_critical_question=True
- "When can you pick up?" -> asked_critical_question=True
- "What's your driver's name?" -> asked_critical_question=True
- Any question asking for personal/contact information -> asked_critical_question=True
- Any question about truck location or status -> asked_critical_question=True

## When to Reply (set is_necessary=True)
- The message is part of an ongoing load negotiation (e.g., contains rates, times, questions)
- The message provides critical updates or details about a load
- The message is from a broker asking a direct question
- We still need to gather missing information to book the load. The missing fields are: {missing_fields}
- The message is asking non-critical questions (see list above)

If you're unsure, default to is_necessary = True to be safe.
"""

def create_reply_necessity_checker_llm():
    """
    Create an LLM instance for reply necessity checking with structured output.

    Returns:
        An LLM instance configured for structured output.
    """

    llm = init_chat_model(
        "azure_openai:gpt-4o",
        temperature=0.2,
    )

    return llm.with_structured_output(ReplyNecessityCheckerAgentResponse)

def format_conversation_history(messages: List[BaseMessage]) -> str:
    """Format conversation history for the prompt."""
    formatted = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            role = "Broker"
        elif isinstance(msg, AIMessage):
            role = "You"
        # We can ignore SystemMessages in the history for the LLM's analysis
        elif isinstance(msg, SystemMessage):
            continue
        else:
            # Fallback for any other message types
            role = msg.type.capitalize()

        formatted.append(f"{role}: {msg.content}")
    return "\n".join(formatted)

def reply_necessity_checker(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """
    Determine if a reply is needed to the latest message.

    Args:
        state: Current workflow state containing conversation history and missing fields.
        llm: Initialized language model with structured output.

    Returns:
        state
    """
    messages = state.get("email_generator_agent_messages", [])
    latest_message = state.get("reply", "")
    missing_fields = state.get("missing_fields", [])

    if not latest_message.strip():
        logger.warning("Empty latest message received in reply_necessity_checker")
        raise NodeInterrupt("Empty latest message received in reply_necessity_checker")

    missing_fields_str = ", ".join(missing_fields) if missing_fields else "None"
    formatted_prompt = REPLY_NECESSITY_PROMPT.format(missing_fields=missing_fields_str)

    conversation_history = format_conversation_history(messages)
    llm_input = [
        SystemMessage(content=formatted_prompt),
        HumanMessage(
            content=f"CONVERSATION HISTORY:\n{conversation_history}\n\n---\n\nLATEST MESSAGE TO ANALYZE:\n{latest_message}\n\nEMAIL FLOWS STATUS:\n\"info_request_finished\": {state.get('load_info', {}).get('emailHistory', {}).get('isInfoRequestFinished', False)}\n\"negotiation_finished\": {False}"
        )
    ]

    # response = llm.invoke(llm_input)
    response = {
        "is_necessary": True,
        "asked_critical_question": False,
        "reason_for_is_necessary_result": "",
        "reason_for_asked_critical_question_result": ""
    }

    if response.asked_critical_question:
        state["updated_load_fields"]["emailHistory.status"] = EmailHistoryStatus.get("BLOCKED")
        raise NodeInterrupt(f"AI found as broker asking critical question: {response.reason_for_asked_critical_question_result}")

    if (not response.is_necessary):
        raise NodeInterrupt(f"Reply is not necessary: {response.reason_for_is_necessary_result}")

    return state
