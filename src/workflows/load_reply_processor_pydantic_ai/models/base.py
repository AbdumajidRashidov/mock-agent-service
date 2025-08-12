"""Enhanced base models and shared types for freight negotiation system"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel as PydanticBaseModel, Field, ConfigDict, validator


class BaseModel(PydanticBaseModel):
    """Base model with flexible configuration for compatibility"""

    model_config = ConfigDict(
        extra="allow",  # Allow extra fields for compatibility
        validate_assignment=True,
        str_strip_whitespace=True,
        populate_by_name=True
    )

class ValidationResult(BaseModel):
    """Result of input validation"""

    is_valid: bool
    error: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class Location(BaseModel):
    """Geographic location"""

    city: str
    state_prov: str = Field(alias="stateProv")
    country: Optional[str] = "US"

    def __str__(self) -> str:
        return f"{self.city}, {self.state_prov}"

class ProcessingMetadata(BaseModel):
    """Enhanced metadata for processing operations - GUARANTEED NO None VALUES"""

    timestamp: datetime = Field(default_factory=datetime.now)
    processor_version: str = Field(default="pydantic_ai_v3.0_modular")
    model_used: str = Field(default="gpt-4o-mini")
    tokens_used: int = Field(default=0, ge=0)
    processing_time_ms: int = Field(default=0, ge=0)
    confidence_score: float = Field(default=0.75, ge=0, le=1)

    # Additional optional metadata
    api_version: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # Performance tracking
    memory_used_mb: Optional[float] = None
    cpu_time_ms: Optional[int] = None
    cache_hits: Optional[int] = None
    cache_misses: Optional[int] = None

    # Quality metrics
    retry_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)

    @validator('processor_version', pre=True, always=True)
    def ensure_processor_version(cls, v):
        """Ensure processor version is never None"""
        return v or "pydantic_ai_v3.0_modular"

    @validator('model_used', pre=True, always=True)
    def ensure_model_used(cls, v):
        """Ensure model_used is never None"""
        return v or "gpt-4o-mini"

    @validator('tokens_used', pre=True, always=True)
    def ensure_tokens_used(cls, v):
        """Ensure tokens_used is never None"""
        return v if v is not None else 0

    @validator('processing_time_ms', pre=True, always=True)
    def ensure_processing_time(cls, v):
        """Ensure processing_time_ms is never None"""
        return v if v is not None else 0

    @validator('confidence_score', pre=True, always=True)
    def ensure_confidence_score(cls, v):
        """Ensure confidence_score is never None"""
        return v if v is not None else 0.75

    class Config:
        extra = "allow"  # Allow additional metadata fields
        validate_assignment = True  # Validate on assignment too

    def update_timing(self, additional_time_ms: int):
        """Update processing time by adding additional time"""
        self.processing_time_ms += max(0, additional_time_ms)

    def update_tokens(self, additional_tokens: int):
        """Update token count by adding additional tokens"""
        self.tokens_used += max(0, additional_tokens)

    def update_confidence(self, new_confidence: float):
        """Update confidence score with validation"""
        if 0 <= new_confidence <= 1:
            self.confidence_score = new_confidence

    def increment_retry(self):
        """Increment retry count"""
        self.retry_count += 1

    def increment_error(self):
        """Increment error count"""
        self.error_count += 1

    def increment_warning(self):
        """Increment warning count"""
        self.warning_count += 1

    def get_processing_rate(self) -> Optional[float]:
        """Calculate tokens per second processing rate"""
        if self.processing_time_ms > 0 and self.tokens_used > 0:
            return (self.tokens_used * 1000) / self.processing_time_ms
        return None

    def get_efficiency_score(self) -> float:
        """Calculate processing efficiency score (0-1)"""
        base_score = self.confidence_score

        # Adjust for retry rate
        if self.retry_count > 0:
            retry_penalty = min(0.2, self.retry_count * 0.05)
            base_score -= retry_penalty

        # Adjust for error rate
        if self.error_count > 0:
            error_penalty = min(0.3, self.error_count * 0.1)
            base_score -= error_penalty

        return max(0.0, min(1.0, base_score))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with guaranteed no None values"""
        result = {
            "timestamp": self.timestamp.isoformat(),
            "processor_version": self.processor_version,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
            "processing_time_ms": self.processing_time_ms,
            "confidence_score": self.confidence_score,
            "retry_count": self.retry_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count
        }

        # Add optional fields if they exist
        optional_fields = [
            "api_version", "request_id", "user_id", "session_id",
            "memory_used_mb", "cpu_time_ms", "cache_hits", "cache_misses"
        ]

        for field in optional_fields:
            value = getattr(self, field, None)
            if value is not None:
                result[field] = value

        # Add computed metrics
        processing_rate = self.get_processing_rate()
        if processing_rate is not None:
            result["tokens_per_second"] = round(processing_rate, 2)

        result["efficiency_score"] = round(self.get_efficiency_score(), 3)

        return result

    def get_summary_string(self) -> str:
        """Get human-readable summary"""
        time_seconds = self.processing_time_ms / 1000

        parts = [
            f"{self.processor_version}",
            f"{self.model_used}",
            f"{self.tokens_used} tokens",
            f"{time_seconds:.1f}s",
            f"{self.confidence_score:.1%} confidence"
        ]

        if self.retry_count > 0:
            parts.append(f"{self.retry_count} retries")

        if self.error_count > 0:
            parts.append(f"{self.error_count} errors")

        return " | ".join(parts)

    @classmethod
    def create_default(cls, **overrides) -> 'ProcessingMetadata':
        """Create ProcessingMetadata with defaults and optional overrides"""
        defaults = {
            "timestamp": datetime.now(),
            "processor_version": "pydantic_ai_v3.0_modular",
            "model_used": "gpt-4o-mini",
            "tokens_used": 0,
            "processing_time_ms": 0,
            "confidence_score": 0.75
        }
        defaults.update(overrides)
        return cls(**defaults)

    @classmethod
    def from_legacy_dict(cls, legacy_dict: Dict[str, Any]) -> 'ProcessingMetadata':
        """Create ProcessingMetadata from legacy dictionary format"""

        # Handle legacy timestamp formats
        timestamp = legacy_dict.get('timestamp')
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.now()
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.now()

        return cls.create_default(
            timestamp=timestamp,
            processor_version=legacy_dict.get('processor_version') or "unknown",
            model_used=legacy_dict.get('model_used') or "unknown",
            tokens_used=legacy_dict.get('tokens_used') or 0,
            processing_time_ms=legacy_dict.get('processing_time_ms') or 0,
            confidence_score=legacy_dict.get('confidence_score') or 0.75
        )
