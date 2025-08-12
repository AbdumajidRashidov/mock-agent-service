from enum import IntEnum
from typing import Dict, Optional, TypedDict, Any

class NegotiationStep(IntEnum):
    MAX_BID = 0
    FIRST_BID = 1
    SECOND_BID = 2
    MIN_BID = 3
    FAILED = 4
    SUCCEEDED = 5

class RateInfo(TypedDict):
    minimumRate: float
    maximumRate: float

class EmailHistory(TypedDict):
    negotiationStep: NegotiationStep

class Load(TypedDict):
    rateInfo: RateInfo
    emailHistory: EmailHistory

def get_current_offering_rate(load: Load, company_details: Dict[str, Any]) -> Optional[float]:
    """Get the current offering rate based on the negotiation step.

    Args:
        load (Load): The load information containing rate info and email history
        company_details (Dict[str, Any]): Company details containing rate negotiation settings

    Returns:
        Optional[float]: The calculated offering rate or None if not applicable
    """
    offering_rate = None

    # Get negotiation step with a default of None
    negotiation_step = load.get('emailHistory', {}).get('negotitationStep')
    if negotiation_step is None:
        return None

    match negotiation_step:
        case NegotiationStep.MAX_BID:
            offering_rate = load['rateInfo']['maximumRate']

        case NegotiationStep.FIRST_BID:
            rate_range = load['rateInfo']['maximumRate'] - load['rateInfo']['minimumRate']
            threshold = company_details.get('rateNegotiation', {}).get('firstBidThreshold', 0) / 100
            rounding = company_details.get('rateNegotiation', {}).get('rounding', 1)

            offering_rate = round(
                (load['rateInfo']['minimumRate'] + (rate_range * threshold)) / rounding
            ) * rounding

        case NegotiationStep.SECOND_BID:
            rate_range = load['rateInfo']['maximumRate'] - load['rateInfo']['minimumRate']
            threshold = company_details.get('rateNegotiation', {}).get('secondBidThreshold', 0) / 100
            rounding = company_details.get('rateNegotiation', {}).get('rounding', 1)

            offering_rate = round(
                (load['rateInfo']['minimumRate'] + (rate_range * threshold)) / rounding
            ) * rounding

        case NegotiationStep.MIN_BID:
            offering_rate = load['rateInfo']['minimumRate']

    return offering_rate
