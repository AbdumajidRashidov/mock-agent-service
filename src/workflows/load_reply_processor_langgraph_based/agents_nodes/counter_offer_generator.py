from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage

def round_rate(rate: float) -> int:
    """Round rate to nearest $50"""
    return int(round(rate / 50) * 50)

NEGOTIATION_EMAIL_GENERATOR_WITH_DATAPOINTS = """You are a freight dispatcher making a counter-offer. Your first offer was rejected. Now, generate 3 casual, human-like email variations for a new offer.

# Context
- Broker's Last Rate: {current_rate}
- Our New Counter-Offer: {proposed_rate}
- Our MC#: {company_mc_number}

# Instructions
1.  **Generate 3 Variations**: Create three distinct, casual email options for the counter-offer.
2.  **Be Human-like**: Write like a real dispatcher making a follow-up offer. It should be very concise.
3.  **Use Our Rate**: All variations must include our new proposed rate: {proposed_rate}.
4.  **Consider Load Details**: You can subtly mention a load detail to justify the rate, but keep it brief. (e.g., "it's a bit heavy", "driver is empty nearby").
    - Weight: {weight}
    - Team Drivers: {is_team}
    - Driver Load/Unload: {driver_load}/{driver_unload}
5.  **Answer Direct Questions**: If the broker asks a direct question for our MC#, you MUST include the answer in ALL 3 variations.

# Few-Shot Examples
Here are examples of how dispatchers make counter-offers. Use this style.

---
**Example 1: Simple Counter**
- Broker's Rate: $1250
- Our Counter: $1400
- Generated Email: "1400 lets do it"

**Example 2: Casual Counter**
- Broker's Rate: $947
- Our Counter: $1000
- Generated Email: "1000 lets do it man"

**Example 3: Counter with Context**
- Broker's Rate: $1300
- Our Counter: $1350
- Generated Email: "1350 lets do it. empty now in Columbia SC"

**Example 4: Final Offer Feel**
- Broker's Rate: $2500
- Our Counter: $2600
- Generated Email: "Alright, can we lock it for 2600"
---

Now, generate exactly 3 email variations for the counter-offer based on the context provided.
"""

def generate_counter_offer(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """Generate second round counter-offer emails with data points."""
    current_rate = int(state.get("load_info", {}).get("rateInfo", {}).get("rate", "0"))
    if not current_rate:
        raise ValueError("Current rate is required for negotiation email generation")

    # Calculate the proposed rate based on brackets
    if current_rate >= 3000:
        proposed_rate = current_rate + 250
    elif current_rate < 3000 and current_rate >= 2000:
        proposed_rate = current_rate + 200
    elif current_rate < 2000 and current_rate >= 1000:
        proposed_rate = current_rate + 150
    else:
        proposed_rate = current_rate + 100

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

    messages = [
        SystemMessage(content=NEGOTIATION_EMAIL_GENERATOR_WITH_DATAPOINTS.format(
            weight= state.get("updated_load_fields", {}).get("emailHistory.details.weight", "") or state.get("load_info", {}).get("emailHistory", {}).get("details", {}).get("weight") or state.get("load_info", {}).get("shipment_details", {}).get("maximum_weight_pounds"),
            is_team=state.get("load_info", {}).get("emailHistory", {}).get("details", {}).get("isTeamDriver") or state.get("updated_load_fields", {}).get("emailHistory.details.isTeamDriver", False),
            driver_load=state.get("load_info", {}).get("emailHistory", {}).get("details", {}).get("driverShouldLoad") or state.get("updated_load_fields", {}).get("emailHistory.details.driverShouldLoad", False),
            driver_unload=state.get("load_info", {}).get("emailHistory", {}).get("details", {}).get("driverShouldUnload") or state.get("updated_load_fields", {}).get("emailHistory.details.driverShouldUnload", False),
            special_notes=state.get("load_info", {}).get("emailHistory", {}).get("details", {}).get("specialNotes") or state.get("updated_load_fields", {}).get("emailHistory.details.specialNotes", ""),
            current_rate=current_rate,
            proposed_rate=proposed_rate,
            company_mc_number=state.get("company_info", {}).get("mcNumber", ""),
            company_dot_number=company_dot_number,
            load_reference_number=load_reference_number,
        )),
        *state["email_generator_agent_messages"],
        HumanMessage(content=state["reply"])
    ]

    # response = llm.invoke(messages)
    response = {
        "email_variation_1": "Variation 1",
        "email_variation_2": "Variation 2",
        "email_variation_3": "Variation 3"
    }

    # Store in suggestedEmails
    state["updated_load_fields"]["emailHistory.suggestedEmails"] = [
        response["email_variation_1"],
        response["email_variation_2"],
        response["email_variation_3"]
    ]

    return state
