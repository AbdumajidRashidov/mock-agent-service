"""Email-related models for freight negotiation"""

from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import Field, validator, ConfigDict
from datetime import datetime

from .base import BaseModel

class EmailType(str, Enum):
    """Types of emails in freight negotiation"""

    JUST_INFO = "just-info"
    JUST_QUESTION = "just-question"
    QUESTION_AND_INFO = "question-and-info"
    CANCELLATION_REPORT = "cancellation-report"
    BID = "bid"
    OTHER = "other"

class EmailAddress(BaseModel):
    """Email address with optional name - flexible for various formats"""

    model_config = ConfigDict(extra="allow")

    email: str  # Flexible string instead of strict EmailStr
    name: Optional[str] = None

    @validator('email', pre=True)
    def validate_email_format(cls, v):
        """Basic email validation - more flexible than EmailStr"""
        if isinstance(v, str) and '@' in v:
            return v.strip().lower()
        return str(v) if v else ""


class EmailContent(BaseModel):
    """Processed email content with AI-friendly formatting"""

    model_config = ConfigDict(extra="allow")

    subject: str
    body: str
    html_body: Optional[str] = None
    plain_text: str
    is_reply: bool = False
    reply_content: Optional[str] = None

    # Content analysis
    word_count: Optional[int] = None
    has_questions: Optional[bool] = None
    has_rates: Optional[bool] = None

    @validator('plain_text', pre=True, always=True)
    def set_plain_text(cls, v, values):
        """Ensure plain_text is set from body if not provided"""
        return v or values.get('body', '')

    @validator('word_count', pre=True, always=True)
    def calculate_word_count(cls, v, values):
        """Calculate word count if not provided"""
        if v is None:
            plain_text = values.get('plain_text', '')
            return len(plain_text.split()) if plain_text else 0
        return v


class EmailMessage(BaseModel):
    """Individual email message in the conversation thread"""

    model_config = ConfigDict(
        extra="allow",  # Allow extra fields for compatibility
        populate_by_name=True
    )

    # Core email fields
    id: Optional[str] = None
    subject: str = ""
    body: str = ""

    # Sender/recipient information
    from_: Union[List[EmailAddress], List[Dict[str, Any]]] = Field(alias="from", default_factory=list)
    to: Optional[Union[List[EmailAddress], List[Dict[str, Any]]]] = None
    cc: Optional[Union[List[EmailAddress], List[Dict[str, Any]]]] = None
    bcc: Optional[Union[List[EmailAddress], List[Dict[str, Any]]]] = None

    # Email metadata
    date: Optional[Union[datetime, str]] = None
    message_id: Optional[str] = Field(None, alias="messageId")
    in_reply_to: Optional[str] = Field(None, alias="inReplyTo")
    references: Optional[List[str]] = None

    # Processing fields
    content: Optional[EmailContent] = None
    email_type: Optional[EmailType] = None

    # Classification flags
    is_from_dispatcher: bool = False
    is_from_broker: bool = False

    # Additional metadata (allows any extra fields)
    priority: Optional[str] = None
    importance: Optional[str] = None
    thread_id: Optional[str] = Field(None, alias="threadId")
    conversation_id: Optional[str] = Field(None, alias="conversationId")

    @validator('from_', pre=True)
    def normalize_from_field(cls, v):
        """Normalize the from field to EmailAddress objects"""
        if not v:
            return []

        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, dict):
                    result.append(EmailAddress(**item))
                elif hasattr(item, 'email'):
                    result.append(item)
                else:
                    # Handle string format
                    result.append(EmailAddress(email=str(item)))
            return result

        return [EmailAddress(email=str(v))]

    @validator('to', 'cc', 'bcc', pre=True)
    def normalize_recipient_fields(cls, v):
        """Normalize recipient fields to EmailAddress objects"""
        if not v:
            return None

        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, dict):
                    result.append(EmailAddress(**item))
                elif hasattr(item, 'email'):
                    result.append(item)
                else:
                    result.append(EmailAddress(email=str(item)))
            return result

        return [EmailAddress(email=str(v))]

    @validator('date', pre=True)
    def normalize_date(cls, v):
        """Normalize date field to datetime"""
        if not v:
            return None

        if isinstance(v, datetime):
            return v

        if isinstance(v, str):
            # Try common date formats
            date_formats = [
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%d %H:%M:%S',
                '%m/%d/%Y %H:%M:%S',
                '%m/%d/%Y, %I:%M:%S %p'
            ]

            for fmt in date_formats:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue

            # If no format matches, return current time
            return datetime.now()

        return datetime.now()

    def get_sender_email(self) -> str:
        """Get the sender's email address"""
        if self.from_ and len(self.from_) > 0:
            sender = self.from_[0]
            if isinstance(sender, EmailAddress):
                return sender.email
            elif isinstance(sender, dict):
                return sender.get('email', '')
        return ""

    def get_sender_name(self) -> Optional[str]:
        """Get the sender's name"""
        if self.from_ and len(self.from_) > 0:
            sender = self.from_[0]
            if isinstance(sender, EmailAddress):
                return sender.name
            elif isinstance(sender, dict):
                return sender.get('name')
        return None

    def get_plain_content(self) -> str:
        """Get plain text content for AI processing"""
        if self.content and self.content.plain_text:
            return self.content.plain_text

        # Clean HTML if needed
        body = self.body
        if '<' in body and '>' in body:
            # Simple HTML tag removal
            import re
            body = re.sub(r'<[^>]+>', '', body)

        return body.strip()

    def is_reply(self) -> bool:
        """Check if this is a reply email"""
        return (
            self.subject.lower().startswith(('re:', 'fwd:', 'fw:')) or
            bool(self.in_reply_to) or
            bool(self.content and self.content.is_reply)
        )

    def has_attachments(self) -> bool:
        """Check if email has attachments (from extra fields)"""
        # This would be set from extra fields if attachment data is available
        attachments = getattr(self, 'attachments', None)
        return bool(attachments)


class EmailThread(BaseModel):
    """Email conversation thread with analysis capabilities"""

    model_config = ConfigDict(extra="allow")

    # Core thread data
    messages: List[EmailMessage] = Field(default_factory=list)
    subject_line: str = ""
    participants: List[EmailAddress] = Field(default_factory=list)
    our_emails: List[str] = Field(default_factory=list)

    # Thread analysis
    message_count: int = 0
    dispatcher_message_count: int = 0
    broker_message_count: int = 0

    # Thread metadata
    thread_id: Optional[str] = None
    started_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._analyze_thread()

    def _analyze_thread(self):
        """Analyze the thread and set classification flags"""
        if not self.messages:
            return

        self.message_count = len(self.messages)
        all_participants = set()

        # Get subject line from first message if not set
        if not self.subject_line and self.messages:
            self.subject_line = self.messages[0].subject

        # Analyze each message
        for msg in self.messages:
            sender_email = msg.get_sender_email()

            # Set dispatcher/broker flags
            if sender_email in self.our_emails:
                msg.is_from_dispatcher = True
                self.dispatcher_message_count += 1
            else:
                msg.is_from_broker = True
                self.broker_message_count += 1

            # Collect all participants
            all_participants.add(sender_email)

            # Update timestamps
            if msg.date:
                if not self.started_at or msg.date < self.started_at:
                    self.started_at = msg.date
                if not self.last_activity or msg.date > self.last_activity:
                    self.last_activity = msg.date

        # Update participants list
        self.participants = [EmailAddress(email=email) for email in all_participants if email]

    def get_latest_message(self) -> Optional[EmailMessage]:
        """Get the most recent message"""
        return self.messages[-1] if self.messages else None

    def get_latest_broker_message(self) -> Optional[EmailMessage]:
        """Get the most recent message from broker"""
        for msg in reversed(self.messages):
            if msg.is_from_broker:
                return msg
        return None

    def get_latest_dispatcher_message(self) -> Optional[EmailMessage]:
        """Get the most recent message from dispatcher"""
        for msg in reversed(self.messages):
            if msg.is_from_dispatcher:
                return msg
        return None

    def get_conversation_context(self) -> str:
        """Get formatted conversation context for AI processing"""
        if not self.messages:
            return ""

        context_parts = []
        for i, msg in enumerate(self.messages):
            sender_type = "Dispatcher" if msg.is_from_dispatcher else "Broker"
            context_parts.append(f"Message {i+1} ({sender_type}):")
            context_parts.append(f"Subject: {msg.subject}")
            context_parts.append(f"Body: {msg.get_plain_content()}")
            context_parts.append("")  # Empty line between messages

        return "\n".join(context_parts)

    def get_thread_summary(self) -> Dict[str, Any]:
        """Get summary of the thread for analysis"""
        return {
            "message_count": self.message_count,
            "dispatcher_messages": self.dispatcher_message_count,
            "broker_messages": self.broker_message_count,
            "participants": len(self.participants),
            "subject": self.subject_line,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "duration_hours": self._calculate_duration_hours()
        }

    def _calculate_duration_hours(self) -> Optional[float]:
        """Calculate thread duration in hours"""
        if self.started_at and self.last_activity:
            delta = self.last_activity - self.started_at
            return delta.total_seconds() / 3600
        return None


class QuestionAnswer(BaseModel):
    """Question asked by broker and our answer"""

    model_config = ConfigDict(extra="allow")

    question: str
    answer: Optional[str] = None
    could_not_answer: bool = False
    confidence_score: Optional[float] = Field(None, ge=0, le=1)

    # Question classification
    question_type: Optional[str] = None  # "company_info", "load_details", "capabilities", etc.
    requires_human_review: bool = False

    def is_answered(self) -> bool:
        """Check if question has been answered successfully"""
        return bool(self.answer and not self.could_not_answer)

    def is_critical(self) -> bool:
        """Check if this is a critical question that must be answered"""
        return self.could_not_answer or self.requires_human_review
