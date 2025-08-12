from typing import Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

class EmailCleanerAgentResponse(BaseModel):
    """Response model for the email cleaner."""
    cleaned_reply: str = Field(..., description="The cleaned email reply with footers and tracking information removed")

EMAIL_CLEANER_PROMPT = """
You are an email processing assistant that helps clean up email replies from brokers by focusing on the broker's response and removing unnecessary content.

Your task is to process the email thread and:
1. Identify and keep ONLY the most recent reply from the broker
2. Remove any quoted or forwarded content from previous emails
3. Remove email footers, signatures, and disclaimers
4. Remove tracking IDs, tracking links, and marketing content
5. Remove "Powered by" or similar service attribution lines
6. Preserve ALL essential information including:
   - Load details (origin, destination, dates, times, weight, commodity, equipment)
   - Rate information and pricing
   - Availability and scheduling information
   - Any questions or requests from the broker
   - Important notes or special instructions
   - Contact information (phone, email) if provided
7. Format the output with proper spacing and line breaks for readability:
   - Add exactly one blank line between paragraphs
   - Ensure consistent spacing around punctuation and between sections
   - Add a blank line before section headers (e.g., "Origin:", "Destination:")
   - Preserve bullet points and numbered lists with proper indentation
   - Ensure consistent spacing around colons (e.g., "Weight: 40,000 lbs")
   - Maintain proper spacing around dashes (e.g., "07/16/2025 - 07/17/2025")
8. Format load details in a clean, consistent way:
   - One detail per line
   - Consistent indentation for related items
   - Clear section separation

CRITICAL RULES:
- If the broker's response is minimal (1-3 words like "no", "yes", "sure", "that's right"), PRESERVE IT EXACTLY AS IS
- Never return an empty response if the input contains any content
- If the email contains a thread, only keep the most recent broker's response
- Remove any content that appears to be from our own emails (look for "From:" lines with our domain)
- Keep the main content of the broker's response clean and intact
- Ensure the output is well-formatted with proper spacing for easy reading
- If the broker's response is a single word or short phrase, return it exactly as is without modification
- Never modify or summarize the broker's words - preserve their exact wording and meaning
- Keep all relevant details about the load, even if they seem repetitive

Return ONLY the cleaned and well-formatted broker's response with all unnecessary elements removed. Do not add any explanations or additional text.

Example Input 1 (Minimal response):
---
no
---

Example Output 1:
---
no
---

Example Input 2 (Simple reply with details):
---
Our rate is $825, can you cover it? Can you send over your MC #?

- Reference ID: 2047215-1968355
- Equipment: 53 ft, VAN
- Stops:
- Origin: Hazleton, PA on 07/16/2025 at 1300 EDT
- Destination: Bohemia, NY on 07/17/2025 at 0800 EDT
- Commodity: PALLETS
- Weight: 33,120 lb
- Remarks: Driver must notify Venture 1 hour before detention begins

[Tracking ID: ABC123] Powered by [SomeService]
---

Example Output 2:
---
Our rate is $825, can you cover it? Can you send over your MC #?

- Reference ID: 2047215-1968355
- Equipment: 53 ft, VAN
- Stops:
- Origin: Hazleton, PA on 07/16/2025 at 1300 EDT
- Destination: Bohemia, NY on 07/17/2025 at 0800 EDT
- Commodity: PALLETS
- Weight: 33,120 lb
- Remarks: Driver must notify Venture 1 hour before detention begins
---

Example Input 3 (Minimal response with important info):
---
All fcfs M-F 0800-1600 SAT 0800-1200
---

Example Output 3:
---
All fcfs M-F 0800-1600 SAT 0800-1200
---

Example Input 4 (Undeliverable email):
---
Address not found

Your message wasn't delivered to ms@genproinc.com because the address couldn't be found, or is unable to receive mail.

The response was: The email account that you tried to reach does not exist. Please try double-checking the recipient's email address for typos or unnecessary spaces.
---

Example Output 4:
---
Address not found

Your message wasn't delivered to ms@genproinc.com because the address couldn't be found, or is unable to receive mail.

The response was: The email account that you tried to reach does not exist. Please try double-checking the recipient's email address for typos or unnecessary spaces.
---

Example Input 5 (Email thread - keep broker's reply):
---
Carrier Sales support is currently out of the office. Please see full load details below.

> **From:** Mikey
> **Sent:** Wednesday, July 16, 2025 4:36:59 AM
> **To:** NTG- CS South East Matches
> **Subject:** Load - Bethlehem, PA -> Reston, VA (07/16/2025)
>
> Hello Team! Need details on the Bethlehem, PA to Reston, VA, 07/16/2025
>
> Powered by Numeo
---

Example Output 5:
---
Carrier Sales support is currently out of the office. Please see full load details below.
---

Now clean the following email reply:
"""

def create_email_cleaner_llm():
    """Create and configure the LLM for email cleaning."""
    llm = init_chat_model(
        "azure_openai:gpt-4o",
        temperature=0.2,
    )
    return llm.with_structured_output(EmailCleanerAgentResponse)

def email_cleaner(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """Clean up email replies by removing footers and tracking information.

    Args:
        state: Dictionary containing the current state with the 'reply' key
        llm: Language model for processing the email

    Returns:
        Updated state with cleaned reply

    Raises:
        ValueError: If the input email is empty or the cleaned reply is empty
    """
    reply = state.get("reply", "").strip()
    if not reply:
        raise ValueError("Email content is empty")

    # Get the cleaned reply from LLM
    # response = llm.invoke([
    #     SystemMessage(content=EMAIL_CLEANER_PROMPT),
    #     HumanMessage(content=reply)
    # ])

    response = {
        "cleaned_reply": "Cleaned reply"
    }

    # Verify the cleaned reply exists and is not empty
    if not hasattr(response, 'cleaned_reply') or not response["cleaned_reply"].strip():
        raise ValueError("Cleaned reply is empty or invalid")

    # Update the state with the cleaned reply
    state["reply"] = response["cleaned_reply"].strip()
    return state
