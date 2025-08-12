"""System constants and enums for freight processing"""

from enum import IntEnum, Enum
from typing import List, Set


class NegotiationStep(IntEnum):
    """Steps in the negotiation process"""

    MAX_BID = 0
    FIRST_BID = 1
    SECOND_BID = 2
    MIN_BID = 3
    FAILED = 4
    SUCCEEDED = 5


class RateOfferer(str, Enum):
    """Who offered the rate"""

    BROKER = "broker"
    DISPATCHER = "dispatcher"


class EmailType(str, Enum):
    """Types of emails in freight negotiation"""

    JUST_INFO = "just-info"
    JUST_QUESTION = "just-question"
    QUESTION_AND_INFO = "question-and-info"
    CANCELLATION_REPORT = "cancellation-report"
    BID = "bid"
    OTHER = "other"

class EquipmentType(str, Enum):
    """Types of equipment for freight loads"""

    VAN = "v"
    FLATBED = "f"
    REEFER = "r"
    STEP_DECK = "sd"
    LOWBOY = "lb"
    TANKER = "t"
    CONTAINER = "c"
    OTHER = "other"
