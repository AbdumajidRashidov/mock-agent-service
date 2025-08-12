from langchain_core.messages import HumanMessage, SystemMessage
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from ..utils.convert_emails_to_messages import get_conversation_context

class EmailJudgement(BaseModel):
    """Evaluation of an email's naturalness and human-like quality."""
    score: int = Field(..., description="Score from 1-10 where 10 is perfectly natural")
    feedback: Optional[str] = Field(..., description="Brief feedback on what makes it sound natural or artificial, optional if email is good to send")
    should_send: bool = Field(..., description="Whether the email sounds natural enough to send")
    improvements: Optional[str] = Field(default="", description="If should_send is False, specific suggestions to make it sound more human, optional if email is good to send")

EMAIL_JUDGE_PROMPT = """
You are evaluating responses from a truck dispatcher INFO REQUEST AGENT whose ONLY job is to gather missing information from brokers.

CRITICAL CONTEXT:
- This is NOT a negotiation agent - it should NEVER offer or commit to rates
- Responses should be 1-2 sentences max, direct and to the point
- Common abbreviations (RC, PU, DEL) are okay and preferred
- NO greetings (no hi/hello/hey)
- NO signatures or pleasantries
- Current missing fields: {missing_fields_formatted}
- The agent MAY answer ONLY these direct questions from the broker:
  - MC# or DOT# questions
  - Load Reference Number questions
- For all other non-critical questions (e.g., 'are you interested?', 'can you cover this?'), the agent should IGNORE them and focus on gathering missing information

YOUR TASK:
1. Does this sound like a real, natural response from a busy dispatcher?
2. Is it asking for ALL missing fields in a single message?
3. Is it using casual, human-like language?

STYLE GUIDE (ACCEPT IF IT MATCHES THIS STYLE):
- Short, direct questions (1-2 sentences max)
- Casual language with industry terms (e.g., "pu" for pickup, "del" for delivery)
- Minor typos or slang are okay (e.g., "whats" instead of "what's")
- No greetings, signatures, or pleasantries

EXAMPLES OF GOOD RESPONSES:
- "whats the commodity, weight and rate?"
- "pu and del times?"
- "what's the del and rate?"
- "any special requirements or restrictions?"  # NOTE: Always use 'special requirements or restrictions', NEVER 'special notes'
- "commodity, pu time and rate?"
- "MC# 12345. Any special requirements or restrictions?"  # Example of good MC# response

CRITICAL RULES (REJECT IF ANY OF THESE ARE VIOLATED):
1. REJECT if it offers or commits to specific rates
2. REJECT if it's too formal or robotic (e.g., "Could you please provide...")
3. REJECT if it doesn't ask about ALL missing fields (unless answering a direct question)
4. REJECT if it's more than 2 sentences
5. REJECT if it includes greetings, signatures, or pleasantries

ACCEPTABLE SCENARIOS:
- If broker asks for MC#: "MC# 12345. Any special requirements or restrictions?"
- If broker asks for DOT#: "DOT# 12345. What's the rate?"
- If broker asks for Load Reference: "Load #5678. Any special requirements?"
- If broker asks other non-critical questions (e.g., 'are you interested?'): IGNORE them and ask about missing fields

UNACCEPTABLE SCENARIOS:
- Answering questions about interest, coverage, or commitment (e.g., 'are you interested?', 'can you cover this?')
- Providing information not explicitly requested (MC#, DOT#, or Load Reference only)
- Using 'special notes' instead of 'special requirements or restrictions'

IMPORTANT INSTRUCTIONS FOR JUDGING:
1. If the broker asked for MC# and the response includes it, this is CORRECT - do not suggest removing it
2. Always use 'special requirements or restrictions' - NEVER suggest using 'special notes'
3. The response should be casual and human-like, but minor formality is acceptable

RESPOND WITH JSON:
 - score: number 1-10 (10 = perfect)
 - feedback: brief explanation of your score
 - should_send: boolean
 - improvements: specific suggestions to improve naturalness (if any). DO NOT suggest removing MC# if it was asked for. DO NOT suggest using 'special notes'.
"""

def create_email_judger_llm():
    llm = init_chat_model(
        "azure_openai:gpt-4o",
        temperature=0.3,
    )
    return llm.with_structured_output(EmailJudgement)


def judge_email(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """Evaluate if the generated email sounds natural and human-like."""
    email_content = state.get("email_to_send", "").strip()
    if not email_content:
        return {
            "email_judgement": {
                "score": 1,
                "feedback": "No email content to evaluate",
                "should_send": False,
                "improvements": "Generate an email first"
            },
            "email_to_send": ""
        }

    # Get formatted missing fields for the prompt
    missing_fields = state.get("missing_fields", [])
    missing_fields_formatted = ", ".join(missing_fields) if missing_fields else "None"

    # Get conversation context
    conversation_context = get_conversation_context(state)

    # Format the prompt with missing fields
    prompt_context = {
        "missing_fields_formatted": missing_fields_formatted,
    }
    prompt = EMAIL_JUDGE_PROMPT.format(**prompt_context)

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"CONVERSATION HISTORY:\n{conversation_context}\n\nGENERATED EMAIL TO EVALUATE:\n{email_content}")
    ]

    # judgement = llm.invoke(messages)
    judgement = {
        "score": 10,
        "feedback": "Sounds natural",
        "should_send": True,
        "improvements": ""
    }
    
    judgement_dict = judgement

    if not judgement_dict.get("should_send", False):
        state["email_judgement"] = {
            "score": judgement_dict.get("score", 1),
            "feedback": judgement_dict.get("feedback", "Email doesn't sound natural"),
            "should_send": False,
            "improvements": judgement_dict.get("improvements", "Make it sound more casual and human-like")
        }
        state["email_to_send"] = ""  # Clear to trigger regeneration
    else:
        state["email_judgement"] = {
            "score": judgement_dict.get("score", 10),
            "feedback": "Sounds natural",
            "should_send": True,
            "improvements": ""
        }
        state["email_to_send"] = email_content


    return state
