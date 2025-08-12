from typing import List, Optional, TypedDict

class QuestionAnswer(TypedDict):
    question: str
    answer: Optional[str]
    couldNotAnswer: Optional[bool]

class AnswerGeneratorResponse(TypedDict):
    questions_and_answers: List[QuestionAnswer]
