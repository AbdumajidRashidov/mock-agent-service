"""Rate calculation logic for freight negotiation"""

from typing import Optional, Dict, Any
from ..models.negotiation import NegotiationSettings
from .constants import NegotiationStep
from .exceptions import RateCalculationError

def calculate_strategic_rate(
    min_rate: float,
    max_rate: float,
    negotiation_step: int,
    first_bid_threshold: float = 75.0,
    second_bid_threshold: float = 50.0,
    rounding: int = 25
) -> Optional[float]:
    """
    NEW: Strategic rate calculation with better logic
    """
    if min_rate >= max_rate or min_rate <= 0:
        return None

    rate_range = max_rate - min_rate

    if negotiation_step == NegotiationStep.MAX_BID:
        offering_rate = max_rate
    elif negotiation_step == NegotiationStep.FIRST_BID:
        threshold = first_bid_threshold / 100.0
        offering_rate = min_rate + (rate_range * threshold)
    elif negotiation_step == NegotiationStep.SECOND_BID:
        threshold = second_bid_threshold / 100.0
        offering_rate = min_rate + (rate_range * threshold)
    elif negotiation_step == NegotiationStep.MIN_BID:
        offering_rate = min_rate
    else:
        return None

    # Apply rounding
    if rounding > 1:
        offering_rate = round(offering_rate / rounding) * rounding

    return max(min_rate, min(max_rate, offering_rate))

def evaluate_broker_offer(
    broker_rate: float,
    our_target_rate: float,
    min_rate: float,
    max_rate: float,
    current_step: int,
    rate_context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    NEW: Smart broker offer evaluation with context awareness
    """
    context = rate_context or {}

    decision = {
        "action": "wait",
        "reason": "",
        "should_book": False,
        "next_rate": None,
        "next_step": current_step,
        "confidence": 0.5
    }

    # DECISION MATRIX for your test case
    if broker_rate >= our_target_rate:
        # Broker meets/exceeds target - ACCEPT
        decision.update({
            "action": "accept",
            "reason": f"Broker ${broker_rate:,.0f} meets target ${our_target_rate:,.0f}",
            "should_book": True,
            "next_step": NegotiationStep.SUCCEEDED,
            "confidence": 0.95
        })

    elif context.get("is_final_offer") and broker_rate >= min_rate * 1.05:
        # Final offer above minimum with buffer - ACCEPT
        decision.update({
            "action": "accept",
            "reason": f"Accepting final offer ${broker_rate:,.0f}",
            "should_book": True,
            "next_step": NegotiationStep.SUCCEEDED,
            "confidence": 0.85
        })

    elif broker_rate >= min_rate and current_step < NegotiationStep.MIN_BID.value:
        # Above minimum, continue negotiating
        next_step = min(current_step + 1, NegotiationStep.MIN_BID.value)
        next_rate = calculate_strategic_rate(
            min_rate, max_rate, next_step,
            first_bid_threshold=75, second_bid_threshold=50, rounding=25
        )

        if next_rate and next_rate > broker_rate:
            decision.update({
                "action": "counter",
                "reason": f"Broker ${broker_rate:,.0f} below target, counter ${next_rate:,.0f}",
                "next_rate": next_rate,
                "next_step": next_step,
                "confidence": 0.7
            })
        else:
            # Our next rate would be lower - accept broker's
            decision.update({
                "action": "accept",
                "reason": f"Broker ${broker_rate:,.0f} better than our next offer",
                "should_book": True,
                "next_step": NegotiationStep.SUCCEEDED,
                "confidence": 0.8
            })

    elif broker_rate >= min_rate:
        # At minimum step - accept if reasonable
        decision.update({
            "action": "accept",
            "reason": f"At minimum step, accepting ${broker_rate:,.0f}",
            "should_book": True,
            "next_step": NegotiationStep.SUCCEEDED,
            "confidence": 0.8
        })

    else:
        # Below minimum - reject
        decision.update({
            "action": "reject",
            "reason": f"Rate ${broker_rate:,.0f} below minimum ${min_rate:,.0f}",
            "confidence": 0.9
        })

    return decision

def validate_rate_range(min_rate: float, max_rate: float) -> bool:
    """
    Validate that min and max rates form a valid range.

    Args:
        min_rate: Minimum rate
        max_rate: Maximum rate

    Returns:
        True if valid range
    """
    try:
        min_rate = float(min_rate)
        max_rate = float(max_rate)

        return (
            min_rate > 0 and
            max_rate > 0 and
            min_rate < max_rate and
            min_rate >= 100 and  # Reasonable minimum
            max_rate <= 50000    # Reasonable maximum
        )
    except (ValueError, TypeError):
        return False


def estimate_profit_margin(
    offering_rate: float,
    estimated_costs: Dict[str, float]
) -> Dict[str, float]:
    """
    Estimate profit margin for a given offering rate.

    Args:
        offering_rate: Rate being offered
        estimated_costs: Dictionary of cost components

    Returns:
        Dictionary with profit analysis
    """
    total_costs = sum(estimated_costs.values())

    if total_costs >= offering_rate:
        profit = 0.0
        margin_percentage = 0.0
    else:
        profit = offering_rate - total_costs
        margin_percentage = (profit / offering_rate) * 100

    return {
        'total_costs': total_costs,
        'gross_profit': profit,
        'margin_percentage': margin_percentage,
        'offering_rate': offering_rate,
        'cost_breakdown': estimated_costs.copy()
    }
