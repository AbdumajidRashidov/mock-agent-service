from typing import Dict, Any, List, Union
from langchain_core.messages import AIMessage, HumanMessage

def map_email_to_message(email: Dict[str, Any], our_emails: List[str]) -> Union[AIMessage, HumanMessage]:
    """
    Convert an email dictionary to either an AIMessage or HumanMessage based on the sender.

    Args:
        email: Dictionary containing email data with 'from' field
        our_emails: List of email addresses that belong to us

    Returns:
        AIMessage if the email is from us, HumanMessage otherwise
    """
    from_field = email.get('from', [])
    if isinstance(from_field, list) and from_field:
        sender_data = from_field[0] if isinstance(from_field[0], dict) else {}
        sender_email = sender_data.get('email', '').lower()
    else:
        sender_email = ''

    content = email.get('body', '')
    
    # Remove 'Powered by Numeo' signature if present
    content = content.replace('Powered by Numeo', '')

    if sender_email in [e.lower() for e in our_emails]:
        return AIMessage(content=content)
    return HumanMessage(content=content)


def get_conversation_context(state: Dict[str, Any]) -> str:
    """Extract the conversation context from state."""
    context = []
    messages = state.get("email_generator_agent_messages", [])

    # Add last 4 messages for context (2 exchanges)
    for msg in messages[-4:]:
        role = "BROKER" if isinstance(msg, HumanMessage) else "DISPATCHER"
        # Remove 'Powered by Numeo' text from message content
        content = msg.content.replace('Powered by [Numeo](https://www.numeo.ai/)', '').strip()
        context.append(f"{role}: {content}")

    # Add the latest received message
    latest_message = state.get("reply", "")
    if latest_message:
        latest_message = latest_message.replace('Powered by [Numeo](https://www.numeo.ai/)', '').strip()
        context.append(f"BROKER: {latest_message}")

    return "\n\n".join(context) if context else "No recent conversation"
