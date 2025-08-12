"""Negotiation-specific models for rate management"""

from enum import Enum, IntEnum
from pydantic import Field, validator

from .base import BaseModel

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

class NegotiationSettings(BaseModel):
    """Settings for rate negotiation strategy"""

    first_bid_threshold: float = Field(alias="firstBidThreshold")
    second_bid_threshold: float = Field(alias="secondBidThreshold")
    rounding: int = Field(default=25, ge=1)

    @validator('first_bid_threshold', 'second_bid_threshold')
    def validate_thresholds(cls, v):
        """Ensure thresholds are between 0 and 100"""
        if not 0 <= v <= 100:
            raise ValueError("Thresholds must be between 0 and 100")
        return v
