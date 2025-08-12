from langchain_core.messages import SystemMessage, HumanMessage
from langchain.chat_models import init_chat_model
from typing import Dict, Any
from pydantic import BaseModel

class EmailGeneratorAgentResponse(BaseModel):
    email_variation_1: str
    email_variation_2: str
    email_variation_3: str

def round_rate(rate: float) -> int:
    """Round rate to nearest $50"""
    return int(round(rate / 50) * 50)

NEGOTIATION_EMAIL_GENERATOR_PROMPT = """You are a freight dispatcher negotiating rates with brokers. Your goal is to generate 3 casual, human-like email variations to offer a new rate.

# Context
- Current Broker Rate: {current_rate}
- Our Proposed Rate: {proposed_rate}
- Our MC#: {company_mc_number}

# Instructions
1.  **Generate 3 Variations**: Create three distinct, casual email options.
2.  **Be Human-like**: Write like a real dispatcher. Short sentences, casual language, and minor grammatical imperfections are good.
3.  **Use Our Rate**: All variations must include our proposed rate: {proposed_rate}.
4.  **Stay Focused**: No market analysis or long explanations. Just the offer.
5.  **MC# Handling**: ONLY include our MC# if the broker explicitly asks for it. Never include it otherwise.

# Few-Shot Examples
Here are examples of how dispatchers talk. Use this style.

---
**Example 1: Simple Offer**
- Broker Rate: $1250
- Our Offer: $1500
- Generated Email: "Any chance for 1500$ ?"

**Example 2: Direct Offer**
- Broker Rate: $900
- Our Offer: $1100
- Generated Email: "Can you do 1100$ ?"

**Example 3: Offer with Context**
- Broker Rate: $1453
- Our Offer: $1500
- Generated Email: "Can you send it for 1500$? Driver is empty now in Statesville, NC"

**Example 4: Very Casual Offer**
- Broker Rate: $2400
- Our Offer: $2600
- Generated Email: "Any chance for 2600$ ? and can we go there now and get loaded?"

**Example 5: Short & Sweet**
- Broker Rate: $3000
- Our Offer: $3800
- Generated Email: "3800$"

**Example 6: With MC# (only if asked)**
- Broker Question: "What's your MC#?"
- Our Offer: $2000
- Generated Email: "Can you do 2000$? MC# 123456"
---

Now, generate exactly 3 email variations based on the context provided.
"""

def create_negotiation_email_generator_llm():
    """Create an LLM instance for email generation with tool calling and structured output."""
    llm = init_chat_model("azure_openai:gpt-4o", temperature=0.3)

    return llm.with_structured_output(EmailGeneratorAgentResponse)

def negotiation_email_generator(state: Dict[str, Any], llm):
    """Generate three distinct email variations for broker negotiation."""

    # Get load details from state with safe defaults
    load_info = state.get("load_info", {})

    # Get and validate the current rate
    current_rate = 0

    if state.get("updated_load_fields", {}).get("rateInfo.rateUsd", 0):
        current_rate = int(state["updated_load_fields"]["rateInfo.rateUsd"])
    elif load_info.get("rateInfo", {}).get("rate", 0):
        current_rate = int(load_info["rateInfo"]["rate"])
    else:
        raise ValueError("Current rate is required for negotiation email generation")

    # Calculate the proposed rate based on brackets
    if current_rate >= 3000:
        proposed_rate = current_rate + 500
    elif current_rate < 3000 and current_rate >= 2000:
        proposed_rate = current_rate + 400
    elif current_rate < 2000 and current_rate >= 1000:
        proposed_rate = current_rate + 300
    else:
        proposed_rate = current_rate + 200

    # Round to nearest 50 for cleaner numbers
    proposed_rate = round_rate(proposed_rate)

    company_dot_number = state.get("company_info", {}).get("dotNumber", "")

    if company_dot_number:
        company_dot_number = f"Our company DOT number is {company_dot_number}"
    else:
        company_dot_number = "We don't have a DOT number"

    load_reference_number = state.get("load_info", {}).get("postersReferenceId", "")

    if load_reference_number:
        load_reference_number = f"Load reference number is {load_reference_number}"
    else:
        load_reference_number = "Say something like 'There isn't any in my dashboard' or 'I don't see any on my end'"

    # Format the prompt with all context
    prompt = NEGOTIATION_EMAIL_GENERATOR_PROMPT.format(
        current_rate=f"${current_rate:,}",
        proposed_rate=f"${proposed_rate:,}",
        company_mc_number=state.get("company_info", {}).get("mcNumber", ""),
        company_dot_number=company_dot_number,
        load_reference_number=load_reference_number,
    )

    messages = [
        SystemMessage(content=prompt),
        *state["email_generator_agent_messages"],
        HumanMessage(content=state["reply"])
    ]

    # response = llm.invoke(messages)

    response = {
        "email_variation_1": "Any chance for 1500$ ?",
        "email_variation_2": "Can you do 1100$ ?",
        "email_variation_3": "Can you send it for 1500$? Driver is empty now in Statesville, NC"
    }

    state["updated_load_fields"]["emailHistory.suggestedEmails"] = [
        response["email_variation_1"],
        response["email_variation_2"],
        response["email_variation_3"]
    ]
    return state
