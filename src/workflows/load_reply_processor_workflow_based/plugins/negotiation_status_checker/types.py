from typing import List, TypedDict

class Email(TypedDict):
    subject: str
    body: str
    from_: str  # Using from_ since 'from' is a Python keyword
