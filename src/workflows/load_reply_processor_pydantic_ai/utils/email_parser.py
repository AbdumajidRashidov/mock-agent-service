"""Email parsing utilities for freight processing"""

from typing import List, Dict, Any
from datetime import datetime

from ..models.email import EmailThread, EmailMessage, EmailAddress, EmailContent
from ..tools.utils import clean_email_content


def parse_email_messages(emails: List[Dict[str, Any]], our_emails: List[str]) -> EmailThread:
    """
    Parse raw email dictionaries into EmailThread with EmailMessage objects.

    Args:
        emails: List of raw email dictionaries
        our_emails: List of dispatcher email addresses

    Returns:
        EmailThread object with parsed messages
    """
    parsed_messages = []

    for email_dict in emails:
        message = convert_email_dict_to_message(email_dict)
        parsed_messages.append(message)

    # Create thread
    thread = EmailThread(
        messages=parsed_messages,
        subject_line=parsed_messages[0].subject if parsed_messages else "",
        our_emails=our_emails
    )

    return thread


def convert_email_dict_to_message(email_dict: Dict[str, Any]) -> EmailMessage:
    """
    Convert a raw email dictionary to EmailMessage object.

    Args:
        email_dict: Raw email dictionary

    Returns:
        EmailMessage object
    """
    # Parse sender addresses
    from_addresses = []
    if 'from' in email_dict and email_dict['from']:
        for sender in email_dict['from']:
            if isinstance(sender, dict):
                from_addresses.append(EmailAddress(
                    email=sender.get('email', ''),
                    name=sender.get('name')
                ))
            elif isinstance(sender, str):
                from_addresses.append(EmailAddress(email=sender))

    # Parse recipient addresses
    to_addresses = []
    if 'to' in email_dict and email_dict['to']:
        for recipient in email_dict['to']:
            if isinstance(recipient, dict):
                to_addresses.append(EmailAddress(
                    email=recipient.get('email', ''),
                    name=recipient.get('name')
                ))
            elif isinstance(recipient, str):
                to_addresses.append(EmailAddress(email=recipient))

    # Parse CC addresses
    cc_addresses = []
    if 'cc' in email_dict and email_dict['cc']:
        for cc_recipient in email_dict['cc']:
            if isinstance(cc_recipient, dict):
                cc_addresses.append(EmailAddress(
                    email=cc_recipient.get('email', ''),
                    name=cc_recipient.get('name')
                ))
            elif isinstance(cc_recipient, str):
                cc_addresses.append(EmailAddress(email=cc_recipient))

    # Process email content
    raw_body = email_dict.get('body', '')
    clean_body = clean_email_content(raw_body)

    email_content = EmailContent(
        subject=email_dict.get('subject', ''),
        body=raw_body,
        html_body=raw_body if '<' in raw_body else None,
        plain_text=clean_body,
        is_reply=is_reply_email(email_dict.get('subject', '')),
        reply_content=extract_reply_portion(clean_body) if is_reply_email(email_dict.get('subject', '')) else None
    )

    # Parse date
    email_date = None
    if 'date' in email_dict and email_dict['date']:
        email_date = parse_email_date(email_dict['date'])

    # Create EmailMessage
    message = EmailMessage(
        id=email_dict.get('id'),
        subject=email_dict.get('subject', ''),
        body=raw_body,
        **{'from': from_addresses},  # Use from_ in the model
        to=to_addresses if to_addresses else None,
        cc=cc_addresses if cc_addresses else None,
        date=email_date,
        message_id=email_dict.get('messageId'),
        in_reply_to=email_dict.get('inReplyTo'),
        references=email_dict.get('references', []),
        content=email_content
    )

    return message


def is_reply_email(subject: str) -> bool:
    """
    Check if an email is a reply based on subject line.

    Args:
        subject: Email subject line

    Returns:
        True if this appears to be a reply email
    """
    if not subject:
        return False

    reply_indicators = ['re:', 'fwd:', 'fw:', 'reply:', 'response:']
    subject_lower = subject.lower().strip()

    return any(subject_lower.startswith(indicator) for indicator in reply_indicators)


def extract_reply_portion(email_body: str) -> str:
    """
    Extract just the reply portion from an email body.

    Args:
        email_body: Full email body

    Returns:
        Just the new reply content
    """
    if not email_body:
        return ""

    # Common reply separators
    reply_separators = [
        '-----Original Message-----',
        '--- Original Message ---',
        'On .* wrote:',
        'From:.*To:.*Subject:',
        '________________________________',
        '> ',  # Quoted lines
        '<div class="gmail_quote',
        'Begin forwarded message:',
        '---------- Forwarded message'
    ]

    # Find the first separator
    lines = email_body.split('\n')
    reply_end = len(lines)

    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # Check for common separators
        for separator in reply_separators:
            if separator in line_stripped:
                reply_end = i
                break

        # Break if we found a separator
        if reply_end < len(lines):
            break

    # Return content before the separator
    reply_lines = lines[:reply_end]
    return '\n'.join(reply_lines).strip()


def parse_email_date(date_str: Any) -> datetime:
    """
    Parse email date from various formats.

    Args:
        date_str: Date string or datetime object

    Returns:
        Parsed datetime object
    """
    if isinstance(date_str, datetime):
        return date_str

    if not date_str:
        return datetime.now()

    # Try common email date formats
    date_formats = [
        '%a, %d %b %Y %H:%M:%S %z',  # RFC 2822
        '%d %b %Y %H:%M:%S %z',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%SZ',
        '%m/%d/%Y %H:%M:%S',
        '%m/%d/%Y, %I:%M:%S %p'
    ]

    date_str = str(date_str).strip()

    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    # If all parsing fails, return current time
    return datetime.now()

