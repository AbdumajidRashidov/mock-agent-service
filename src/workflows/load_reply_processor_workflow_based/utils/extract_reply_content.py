def extract_reply_content(reply: str) -> str:
    """Extract the reply content by removing the gmail quote container if present.

    Args:
        reply (str): The email reply content

    Returns:
        str: The formatted reply with gmail quote removed if present
    """
    formatted_reply = reply
    start_tag1 = '<div class="gmail_quote gmail_quote_container">'
    start_index1 = formatted_reply.find(start_tag1)

    if start_index1 != -1:
        formatted_reply = formatted_reply[:start_index1]

    start_tag2 = '<div class="gmail_quote">'
    start_index2 = formatted_reply.find(start_tag2)

    if start_index2 != -1:
        formatted_reply = formatted_reply[:start_index2]

    return formatted_reply
