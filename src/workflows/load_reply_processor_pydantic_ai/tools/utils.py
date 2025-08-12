"""Shared tool utilities for freight processing"""

import re
import html2md
from typing import Optional , Dict, Any
from ..models.email import EmailMessage

def clean_email_content(email_body: str) -> str:
    """Clean and normalize email content for AI processing"""
    # Remove Gmail quote containers
    start_tag = '<div class="gmail_quote gmail_quote_container">'
    start_index = email_body.find(start_tag)

    if start_index != -1:
        email_body = email_body[:start_index]

    # Convert HTML to markdown for better AI processing
    if '<' in email_body and '>' in email_body:
        email_body = html2md.convert(email_body)

    # Remove excessive whitespace
    email_body = re.sub(r'\n\s*\n\s*\n', '\n\n', email_body)
    email_body = email_body.strip()

    return email_body

def format_email_for_ai(email: EmailMessage, include_headers: bool = True) -> str:
    """Format email message for AI processing"""
    parts = []

    if include_headers:
        parts.append(f"Subject: {email.subject}")
        if email.from_:
            sender = email.from_[0]
            sender_str = f"{sender.name} <{sender.email}>" if sender.name else sender.email
            parts.append(f"From: {sender_str}")
        parts.append("")  # Empty line after headers

    # Get clean email content
    if email.content and email.content.plain_text:
        body = email.content.plain_text
    else:
        body = clean_email_content(email.body)

    parts.append(body)

    return "\n".join(parts)

def parse_rate_from_text(text: str) -> Optional[float]:
    """
    REBUILT: Enhanced rate detection for all broker communication patterns
    """
    if not text:
        return None

    # Comprehensive rate patterns covering all broker language
    rate_patterns = [
        # Explicit monetary formats
        (r'\$([0-9,]+(?:\.[0-9]{2})?)', 1.0),                    # $2,500.00
        (r'([0-9,]+)\s*(?:dollars?|bucks?|usd|USD)', 1.0),       # 2500 dollars

        # Broker negotiation language - CRITICAL for your test case
        (r'my\s+best\s+is\s*\$?([0-9,]+)', 1.0),               # my best is 2500 ✅
        (r'([0-9,]+)\s*no\s+less', 1.0),                        # 2500 no less ✅
        (r'final\s+offer\s*\$?([0-9,]+)', 1.0),                # final offer 2500
        (r'I\s+can\s+do\s*\$?([0-9,]+)', 1.0),                 # I can do 2500 ✅
        (r'how\s+about\s*\$?([0-9,]+)', 1.0),                  # how about 2500
        (r'will\s+pay\s*\$?([0-9,]+)', 1.0),                   # will pay 2500
        (r'offering\s*\$?([0-9,]+)', 1.0),                     # offering 2500

        # Counter offers and responses
        (r'counter\s*(?:with|at)?\s*\$?([0-9,]+)', 1.0),       # counter with 2500
        (r'meet\s+(?:at|in\s+the\s+middle\s+at)\s*\$?([0-9,]+)', 1.0), # meet at 2500
        (r'too\s+high.*?([0-9,]+)', 1.0),                      # too high, try 2200
        (r'can\'?t\s+do.*?([0-9,]+)', 1.0),                    # can't do that, try 2300

        # Short forms
        (r'([0-9,]+)k\b', 1000.0),                             # 3k = 3000
        (r'([0-9,]+)\s*grand', 1000.0),                        # 3 grand = 3000
        (r'([0-9]+(?:\.[0-9]+)?)\s*k', 1000.0),                # 2.5k = 2500

        # Existing patterns (keep compatibility)
        (r'([0-9,]+(?:\.[0-9]+)?)', 1.0),                      # Plain numbers (last resort)
    ]

    text_clean = text.lower().strip()

    for pattern, multiplier in rate_patterns:
        matches = re.findall(pattern, text_clean, re.IGNORECASE)
        if matches:
            try:
                rate_str = matches[0].replace(',', '')
                rate = float(rate_str) * multiplier

                # Freight rate sanity check (same as existing)
                if 100 <= rate <= 50000:
                    return rate

            except (ValueError, IndexError):
                continue

    return None

def extract_rate_context(text: str) -> Dict[str, Any]:
    """
    NEW: Extract negotiation context from broker messages
    """
    text_lower = text.lower()

    context = {
        "is_final_offer": False,
        "is_counter_offer": False,
        "is_acceptance": False,
        "is_rejection": False,
        "urgency": "normal",
        "confidence": 0.5
    }

    # Final offer indicators - CRITICAL for "my best is 2500 no less"
    final_indicators = ['final offer', 'best price', 'no less', 'that\'s it', 'take it or leave', 'my best']
    if any(indicator in text_lower for indicator in final_indicators):
        context["is_final_offer"] = True
        context["confidence"] = 0.9

    # Counter offer indicators
    counter_indicators = ['how about', 'counter with', 'meet at', 'try this', 'can you do']
    if any(indicator in text_lower for indicator in counter_indicators):
        context["is_counter_offer"] = True
        context["confidence"] = 0.8

    # Acceptance indicators
    accept_indicators = ['that works', 'deal', 'agreed', 'book it', 'send it', 'perfect', 'sounds good']
    if any(indicator in text_lower for indicator in accept_indicators):
        context["is_acceptance"] = True
        context["confidence"] = 0.95

    # Rejection indicators
    reject_indicators = ['too high', 'too low', 'can\'t do', 'no way', 'impossible', 'sorry']
    if any(indicator in text_lower for indicator in reject_indicators):
        context["is_rejection"] = True
        context["confidence"] = 0.85

    return context
