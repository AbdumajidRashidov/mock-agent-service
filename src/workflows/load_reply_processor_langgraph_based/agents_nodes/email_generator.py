from langchain_core.messages import SystemMessage, HumanMessage
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.errors import NodeInterrupt
from typing import Dict, Any
from pydantic import BaseModel

class EmailGeneratorAgentResponse(BaseModel):
    email_to_send: str

EMAIL_GENERATOR_PROMPT = """You are a truck dispatcher for {company_name}. Your only job is to gather missing information about a load by asking simple, casual questions.

# Instructions
1.  **Answer First, Then Ask**: If the broker asks a direct question, you MUST answer it. In the same message, you can then ask for any missing information.
2.  **Combine Everything**: Your entire response (answer + questions) must be in ONE single message, keeping it 1-2 sentences max.
3.  **Be Human-like**: Write like a real dispatcher texting a broker. Keep it short, casual, and to the point. Minor typos or slang are okay.

# CRITICAL RULES
1. NEVER provide or discuss:
   - ETAs or delivery times
   - Driver information (name, cell, etc.)
   - Truck or trailer numbers
   - MC# or DOT# unless explicitly asked
   - Any information that would commit to a load
   - Rates or price discussions (only ask rate if 'offeringRate' is in the missing fields list, otherwise never mention rates)

2. If asked about equipment, respond ONLY with "Dry van"

3. If asked for MC#, respond with: "MC# {company_mc_number}" (only if available)

4. If asked for load ID:
   - If we have a real load ID: Respond with "Load ID: {posters_reference_id}"
   - If NO load ID is available and the user explicitly asked for a load ID: Respond with "I don't see load ID"
   - If the user didn't ask for a load ID, don't mention it at all

# RESPONSE FORMAT
- **Request Information:** Ask for ALL missing information in ONE message. If 'specialNotes' is missing, ask 'special requirements or restrictions?' (not 'special notes?').
- **Brevity & Style:** Keep it 1-2 sentences max. Be direct, casual, and to the point. Common abbreviations (RC, PU, DEL) are okay.

# STYLE GUIDE
- NO greetings (no hi/hello/hey)
- NO signatures (no names, regards, best wishes)
- NO thanks or pleasantries
- NO commitments or confirmations
- NEVER confirm rates (e.g., NEVER say "Rate $X?")

# Missing Fields to Ask About
- {missing_fields_formatted}

# Few-Shot Examples
Here are examples of how dispatchers ask for information. Use this style.

---
# NOTE: Only the following fields can be missing and should be referenced in examples:
# commodity, weight, pickupDateTime, deliveryDateTime, offeringRate, specialNotes

**Example 1: Basic Info Request**
- Missing Fields: commodity, weight, specialNotes
- Generated Email: "whats the commodity, weight and any special requirements?"

**Example 2: Very Casual**
- Missing Fields: pickupDateTime, deliveryDateTime
- Generated Email: "pu and del times?"

**Example 3: More Detailed Request**
- Missing Fields: deliveryDateTime, offeringRate
- Generated Email: "what's the del and rate?"

**Example 4: Simple & Direct**
- Missing Fields: specialNotes
- Generated Email: "any special requirements or restrictions?"

**Example 5: Multiple Fields**
- Missing Fields: commodity, pickupDateTime, specialNotes
- Generated Email: "commodity, pu time and any special requirements?"
---

# Email Context
This is the email you are replying to:
{reply}

{feedback}

IMPORTANT:
1. Only ask about missing fields listed above.
2. Never include MC# or DOT# unless explicitly asked
3. Only ask about rate if 'offeringRate' is in the missing fields
4. Ignore any requests for rates or quotes from the broker

Now, write your response below. Keep it to 1-2 sentences and do not include greetings or signatures.
"""

@tool
def get_answer_from_human():
    """
    Escalates the current conversation to a human dispatcher for handling.
    Use this when asked for information you're not allowed to provide (ETAs, driver info, etc.)
    or when the request requires human judgment.
    """
    raise NodeInterrupt("Escalating to human dispatcher for handling")

def create_email_generator_llm():
    """Create an LLM instance for email generation with tool calling and structured output."""
    llm = init_chat_model(
        "azure_openai:gpt-4o",
        temperature=0.3,
    )

    return llm.with_structured_output(EmailGeneratorAgentResponse)

def email_generator(state: Dict[str, Any], llm):
    """Generate a response email to the broker."""
    feedback = ""
    if "email_judgement" in state and not state.get("email_judgement", {}).get("should_send", True):
        judgement = state["email_judgement"]
        feedback = f"Feedbacks (score: {judgement.get('score', 0)}/10): {judgement.get('feedback', 'No feedback')}. {judgement.get('improvements', '')}"

    missing_fields = state.get("missing_fields", [])
    # Format missing fields, with special handling for specialNotes
    def format_field(field):
        if field == "specialNotes":
            return "- any special requirements or restrictions ?"
        if field == "pickupDateTime":
            return "- pickup date and time"
        if field == "deliveryDateTime":
            return "- delivery date and time"
        if field == "offeringRate":
            return "- offering rate"
        return f"- {field}"

    missing_fields_formatted = "\n".join(format_field(field) for field in missing_fields) if missing_fields else "No missing fields"

    # Get load info and handle load ID
    load_info = state.get("load_info", {})
    posters_reference_id = load_info.get("postersReferenceId")

    # Set load_id to None if postersReferenceId is not available
    load_id = str(posters_reference_id) if posters_reference_id is not None else None

    # Prepare the prompt context with all possible template variables
    prompt_context = {
        # Standard fields
        "company_name": state.get("company_info", {}).get("name", ""),
        "company_mc_number": state.get("company_info", {}).get("mcNumber", ""),
        "reply": state.get("reply", ""),
        "feedback": feedback,
        "missing_fields_formatted": missing_fields_formatted,
        "posters_reference_id": load_id if load_id is not None else ""
    }

    # Format the prompt with standard string formatting
    prompt = EMAIL_GENERATOR_PROMPT.format(**prompt_context)

    # Prepare the messages for the LLM
    messages = [
        SystemMessage(content=prompt),
        *state["email_generator_agent_messages"],
        HumanMessage(content=state["reply"])
    ]

    # response = llm.invoke(messages)
    response = {
        "email_to_send": "Email content"
    }

    email_content = response["email_to_send"]  

    return {"email_to_send": email_content, "generate_email_attempts": state.get("generate_email_attempts", 0) + 1}
