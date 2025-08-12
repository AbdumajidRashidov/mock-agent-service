import logging
import re

# Get tracer
logger = logging.getLogger(__name__)


def split_email(email_content):
    """
    Split an email into the reply part and the original part.

    Args:
        email_content: The full email content to split

    Returns:
        Dict with 'reply' and 'original' parts of the email
    """

    if not email_content:
        logger.debug("Empty email content received")
        return {"reply": "", "original": ""}

    # Split the email content into lines
    lines = email_content.split("\n")

    # Regular expressions to detect the start of quoted content
    outlook_pattern = re.compile(r"^-----Original Message-----", re.IGNORECASE)
    gmail_pattern = re.compile(r"^On .* (at|wrote).*$", re.IGNORECASE)
    forward_pattern = re.compile(r"^-+\s*Forwarded message\s*-+", re.IGNORECASE)
    reply_pattern = re.compile(r"^>.*", re.IGNORECASE)  # Lines starting with >
    date_pattern = re.compile(
        r"^(From|Sent|To|Date|Subject):", re.IGNORECASE
    )  # Email headers

    # Find the index where the original message starts
    original_start_index = None

    for i, line in enumerate(lines):
        # Check for patterns indicating quoted content
        if (
            outlook_pattern.match(line.strip())
            or gmail_pattern.match(line.strip())
            or forward_pattern.match(line.strip())
        ):
            original_start_index = i
            break

    # If we found a divider, split the content
    if original_start_index is not None:
        reply_lines = lines[:original_start_index]
        original_lines = lines[original_start_index + 1 :]  # Skip the divider line

        # For Gmail-style quotes, we need to extract the actual message
        # without the "On ... wrote:" line
        if gmail_pattern.match(lines[original_start_index].strip()):
            # Check if there's content after the "On ... wrote:" line
            if len(original_lines) > 0:
                # Skip any headers like From:, To:, etc. that often follow
                while original_lines and date_pattern.match(original_lines[0].strip()):
                    original_lines.pop(0)

        reply = "\n".join(reply_lines).strip()
        original = "\n".join(original_lines).strip()
    else:
        # If no divider is found, assume it's all reply
        reply = email_content.strip()
        original = ""

    logger.debug(
        f"Email split completed successfully. Reply : {reply}, Original: {original}"
    )
    return {"reply": reply, "original": original}
