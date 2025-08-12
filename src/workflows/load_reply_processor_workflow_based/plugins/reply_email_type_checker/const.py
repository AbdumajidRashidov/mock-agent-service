from enum import Enum
from typing import List

class EmailType(str, Enum):
    JUST_INFO = 'just-info'
    JUST_QUESTION = 'just-question'
    QUESTION_AND_INFO = 'question-and-info'
    CANCELLATION_REPORT = 'cancellation-report'
    BID = 'bid'
    OTHER = 'other'

EMAIL_TYPES: List[EmailType] = [
    EmailType.JUST_INFO,
    EmailType.JUST_QUESTION,
    EmailType.QUESTION_AND_INFO,
    EmailType.CANCELLATION_REPORT,
    EmailType.BID,
    EmailType.OTHER
]

PROCESSABLE_EMAIL_TYPES: List[EmailType] = [
    EmailType.JUST_INFO,
    EmailType.JUST_QUESTION,
    EmailType.QUESTION_AND_INFO,
    EmailType.CANCELLATION_REPORT,
    EmailType.BID
]
