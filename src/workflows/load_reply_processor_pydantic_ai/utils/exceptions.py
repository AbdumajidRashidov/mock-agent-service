"""Custom exceptions for freight processing"""

from typing import Optional, Dict, Any

class FreightProcessingError(Exception):
    """Base exception for freight processing errors"""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code or "PROCESSING_ERROR"
        self.details = details or {}

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

class RateCalculationError(FreightProcessingError):
    """Exception for rate calculation errors"""

    def __init__(
        self,
        message: str,
        min_rate: Optional[float] = None,
        max_rate: Optional[float] = None
    ):
        super().__init__(message, "RATE_CALCULATION_ERROR")
        self.min_rate = min_rate
        self.max_rate = max_rate

        if min_rate is not None:
            self.details["min_rate"] = min_rate
        if max_rate is not None:
            self.details["max_rate"] = max_rate
