from typing import List, Optional, TypedDict
from ..answer_generator.types import QuestionAnswer

class Email(TypedDict):
    subject: str
    body: str
    from_: str  # Using from_ since 'from' is a Python keyword

class EmailGeneratorParams(TypedDict):
    questions_and_answers: Optional[List[QuestionAnswer]]
    emails: List[Email]
    our_emails: List[str]
    missing_info: Optional[List[str]]
    offering_rate: Optional[float]
