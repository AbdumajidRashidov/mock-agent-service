"""Enhanced agent response models and processing results with metadata tracking"""

from typing import Optional, List, Dict, Any
from pydantic import Field
from datetime import datetime

from .base import BaseModel, ProcessingMetadata
from .email import QuestionAnswer

class AbusedRequirement(BaseModel):
    """Requirement that was violated"""

    abused_requirement: str = Field(alias="abusedRequirement")
    reason: str
    severity: str = "warning"  # warning, error, critical

    def __str__(self) -> str:
        return f"{self.abused_requirement}: {self.reason}"

class PluginResponse(BaseModel):
    """Enhanced response from an AI plugin/tool with metadata tracking"""

    plugin_name: str
    success: bool = True
    response: Optional[Dict[str, Any]] = None
    extracted_data: Optional[Any] = None

    # Enhanced metadata fields
    tokens_spent: Optional[int] = None
    processing_time_ms: Optional[int] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    error_message: Optional[str] = None

    # Additional tracking fields
    model_used: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    retry_count: Optional[int] = 0

    def is_successful(self) -> bool:
        """Check if plugin execution was successful"""
        return self.success and self.error_message is None

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this plugin execution"""
        return {
            "plugin_name": self.plugin_name,
            "success": self.success,
            "tokens_spent": self.tokens_spent,
            "processing_time_ms": self.processing_time_ms,
            "confidence_score": self.confidence_score,
            "timestamp": self.timestamp.isoformat(),
            "retry_count": self.retry_count
        }

class ProcessingResult(BaseModel):
    """Enhanced complete result of freight email processing with metadata tracking"""

    # Main outputs
    email_to_send: Optional[str] = None
    field_updates: Dict[str, Any] = Field(default_factory=dict)
    message: str

    # Enhanced processing metadata - NEVER None
    metadata: ProcessingMetadata = Field(default_factory=lambda: ProcessingMetadata(
        timestamp=datetime.now(),
        processor_version="pydantic_ai_v3.0_modular",
        model_used="gpt-4o-mini",
        tokens_used=0,
        processing_time_ms=0,
        confidence_score=0.75
    ))

    # Detailed results
    plugin_responses: List[PluginResponse] = Field(default_factory=list)
    questions_and_answers: List[QuestionAnswer] = Field(default_factory=list)
    abused_requirements: List[AbusedRequirement] = Field(default_factory=list)

    # Processing flags
    is_load_cancelled: bool = False
    is_load_booked: bool = False
    requires_human_review: bool = False
    has_critical_questions: bool = False

    # Rate information
    detected_broker_rate: Optional[float] = None
    calculated_offering_rate: Optional[float] = None
    negotiation_completed: bool = False

    def add_field_update(self, field_path: str, new_value: Any, operation: str = "set"):
        """Add a field update to the result"""
        if operation == "push":
            if field_path not in self.field_updates:
                self.field_updates[field_path] = []
            if isinstance(self.field_updates[field_path], list):
                self.field_updates[field_path].append(new_value)
            else:
                # Convert to list if not already
                self.field_updates[field_path] = [self.field_updates[field_path], new_value]
        else:
            self.field_updates[field_path] = new_value

    def add_plugin_response(self, plugin_response: PluginResponse):
        """Add a plugin response to the results with metadata aggregation"""
        self.plugin_responses.append(plugin_response)

        # Aggregate metadata from plugin responses
        if plugin_response.tokens_spent:
            current_tokens = self.metadata.tokens_used or 0
            self.metadata.tokens_used = current_tokens + plugin_response.tokens_spent

        if plugin_response.processing_time_ms:
            current_time = self.metadata.processing_time_ms or 0
            self.metadata.processing_time_ms = current_time + plugin_response.processing_time_ms

    def add_question_answer(self, qa: QuestionAnswer):
        """Add a question-answer pair"""
        self.questions_and_answers.append(qa)
        if qa.could_not_answer:
            self.has_critical_questions = True

    def add_abused_requirement(self, requirement: AbusedRequirement):
        """Add an abused requirement"""
        self.abused_requirements.append(requirement)
        if requirement.severity in ["error", "critical"]:
            self.requires_human_review = True

    def mark_load_cancelled(self, reason: str = "Broker cancelled the load"):
        """Mark the load as cancelled"""
        self.is_load_cancelled = True
        self.message = reason
        self.add_field_update("status", "cancelled")

    def mark_load_booked(self, rate: float, reason: str = "Load successfully booked"):
        """Mark the load as booked"""
        self.is_load_booked = True
        self.negotiation_completed = True
        self.calculated_offering_rate = rate
        self.message = reason
        # self.add_field_update("status", "booked")
        self.add_field_update("emailHistory.negotitationStep", 5)  # SUCCEEDED

    def mark_negotiation_failed(self, reason: str = "Negotiation failed"):
        """Mark the negotiation as failed"""
        self.requires_human_review = True
        self.message = reason
        self.add_field_update("emailHistory.negotitationStep", 4)  # FAILED

    def update_metadata(self, **kwargs):
        """Update metadata fields dynamically"""
        for key, value in kwargs.items():
            if hasattr(self.metadata, key) and value is not None:
                setattr(self.metadata, key, value)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        plugin_metrics = [pr.get_performance_metrics() for pr in self.plugin_responses]

        total_plugin_tokens = sum(pr.tokens_spent or 0 for pr in self.plugin_responses)
        total_plugin_time = sum(pr.processing_time_ms or 0 for pr in self.plugin_responses)

        successful_plugins = sum(1 for pr in self.plugin_responses if pr.success)

        avg_confidence = None
        confidence_scores = [pr.confidence_score for pr in self.plugin_responses if pr.confidence_score is not None]
        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)

        return {
            "overall": {
                "total_tokens": self.metadata.tokens_used,
                "total_time_ms": self.metadata.processing_time_ms,
                "model_used": self.metadata.model_used,
                "processor_version": self.metadata.processor_version,
                "confidence_score": self.metadata.confidence_score
            },
            "plugins": {
                "total_plugins": len(self.plugin_responses),
                "successful_plugins": successful_plugins,
                "plugin_tokens": total_plugin_tokens,
                "plugin_time_ms": total_plugin_time,
                "avg_plugin_confidence": avg_confidence,
                "plugin_details": plugin_metrics
            },
            "outputs": {
                "has_email": bool(self.email_to_send),
                "field_updates_count": len(self.field_updates),
                "questions_answered": len([qa for qa in self.questions_and_answers if qa.is_answered()]),
                "questions_failed": len([qa for qa in self.questions_and_answers if qa.could_not_answer]),
                "requirements_violations": len(self.abused_requirements),
                "is_load_booked": self.is_load_booked,
                "is_load_cancelled": self.is_load_cancelled,
                "requires_human_review": self.requires_human_review
            },
            "business_outcomes": {
                "detected_broker_rate": self.detected_broker_rate,
                "calculated_offering_rate": self.calculated_offering_rate,
                "negotiation_completed": self.negotiation_completed,
                "final_message": self.message
            }
        }

    def get_summary(self) -> str:
        """Get a human-readable summary of the processing result"""
        summary_parts = [f"Status: {self.message}"]

        if self.email_to_send:
            summary_parts.append("✅ Email generated")

        if self.field_updates:
            summary_parts.append(f"📝 {len(self.field_updates)} field updates")

        if self.questions_and_answers:
            answered = sum(1 for qa in self.questions_and_answers if qa.is_answered())
            summary_parts.append(f"❓ {answered}/{len(self.questions_and_answers)} questions answered")

        if self.detected_broker_rate:
            summary_parts.append(f"💰 Broker rate: ${self.detected_broker_rate}")

        if self.calculated_offering_rate:
            summary_parts.append(f"💵 Our rate: ${self.calculated_offering_rate}")

        if self.abused_requirements:
            summary_parts.append(f"⚠️ {len(self.abused_requirements)} requirement violations")

        if self.requires_human_review:
            summary_parts.append("👥 Requires human review")

        # Add performance metrics
        if self.metadata.tokens_used:
            summary_parts.append(f"📊 {self.metadata.tokens_used} tokens")

        if self.metadata.processing_time_ms:
            time_seconds = self.metadata.processing_time_ms / 1000
            summary_parts.append(f"⏱️ {time_seconds:.1f}s")

        return " | ".join(summary_parts)

    def to_legacy_format(self) -> Dict[str, Any]:
        """Convert to legacy format for compatibility - WITH GUARANTEED METADATA"""

        # Ensure metadata is complete and never None
        if not self.metadata:
            self.metadata = ProcessingMetadata(
                timestamp=datetime.now(),
                processor_version="pydantic_ai_v3.0_modular",
                model_used="gpt-4o-mini",
                tokens_used=0,
                processing_time_ms=0,
                confidence_score=0.75
            )

        # Double-check all metadata fields are set
        if self.metadata.timestamp is None:
            self.metadata.timestamp = datetime.now()
        if self.metadata.processor_version is None:
            self.metadata.processor_version = "pydantic_ai_v3.0_modular"
        if self.metadata.model_used is None:
            self.metadata.model_used = "gpt-4o-mini"
        if self.metadata.tokens_used is None:
            self.metadata.tokens_used = 0
        if self.metadata.processing_time_ms is None:
            self.metadata.processing_time_ms = 0
        if self.metadata.confidence_score is None:
            self.metadata.confidence_score = 0.75

        result = {
            "message": self.message,
            "metadata": {
                "timestamp": self.metadata.timestamp.isoformat(),
                "processor_version": self.metadata.processor_version,
                "model_used": self.metadata.model_used,
                "tokens_used": self.metadata.tokens_used,
                "processing_time_ms": self.metadata.processing_time_ms,
                "confidence_score": self.metadata.confidence_score
            }
        }

        if self.email_to_send:
            result["email_to_send"] = self.email_to_send

        if self.field_updates:
            result["field_updates"] = self.field_updates

        # Add performance summary for debugging
        result["performance_summary"] = self.get_performance_summary()

        return result

    def validate_completeness(self) -> List[str]:
        """Validate that all required fields are properly set"""
        issues = []

        if not self.metadata:
            issues.append("metadata is None")
        else:
            if self.metadata.timestamp is None:
                issues.append("metadata.timestamp is None")
            if self.metadata.processor_version is None:
                issues.append("metadata.processor_version is None")
            if self.metadata.model_used is None:
                issues.append("metadata.model_used is None")
            if self.metadata.tokens_used is None:
                issues.append("metadata.tokens_used is None")
            if self.metadata.processing_time_ms is None:
                issues.append("metadata.processing_time_ms is None")
            if self.metadata.confidence_score is None:
                issues.append("metadata.confidence_score is None")

        if not self.message:
            issues.append("message is empty")

        return issues
