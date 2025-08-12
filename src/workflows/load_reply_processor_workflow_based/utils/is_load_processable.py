from typing import Any
from enum import IntEnum

class NegotiationStep(IntEnum):
    MAX_BID = 0
    FIRST_BID = 1
    SECOND_BID = 2
    MIN_BID = 3
    FAILED = 4
    SUCCEEDED = 5

def is_load_processable(load: Any) -> bool:
    """Check if a load is processable based on its status and conditions.

    Args:
        load (Any): The load object to check

    Returns:
        bool: True if the load is processable, False otherwise
    """
    return (
        load.get('status') != "cancelled"
        and not load.get('warnings', [])
        and not load.get('emailHistory', {}).get('criticalQuestions', [])
        and load.get('emailHistory', {}).get('negotitationStep') not in [NegotiationStep.FAILED, NegotiationStep.SUCCEEDED]
    )
