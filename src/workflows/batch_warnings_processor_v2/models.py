# models.py
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class FilterSeverity(Enum):
    """Severity levels for filter results."""
    WARNING = "warning"
    INFO = "info"


@dataclass
class FilterResult:
    """Result from a single filter check."""
    warnings: List[str]        # ONLY contains actual issues
    filter_type: str
    severity: FilterSeverity
    details: Optional[Dict[str, Any]] = None

    def has_issues(self) -> bool:
        """Returns True if the severity is WARNING."""
        return self.severity == FilterSeverity.WARNING


@dataclass
class LoadAnalysisResult:
    """Complete analysis result for a single load."""
    load_id: str
    truck_id: str
    warning_issues: List[str]     # All warning messages
    filter_results: List[FilterResult]

    def has_issues(self) -> bool:
        """Returns True if there are any issues to report."""
        return len(self.warning_issues) > 0

    def to_warning_item(self, agents_service_pb2):
        """Convert to protobuf WarningItem ONLY if there are issues."""
        if not self.has_issues():
            return None  # Clean loads don't get WarningItems

        return agents_service_pb2.WarningItem(
            truck_id=self.truck_id,
            load_id=self.load_id,
            warnings=self.warning_issues
        )


@dataclass
class TruckCapabilities:
    """Simplified truck capabilities for analysis."""
    id: str
    excluded_states: List[str]
    restrictions: List[str]
    permitted_items: List[str]
    security_items: List[str]
    team_solo: str
    max_length: Optional[int] = None
    max_weight: Optional[int] = None


@dataclass
class LoadInfo:
    """Simplified load information for analysis."""
    id: str
    origin_state: str
    destination_state: str
    origin_city: str
    destination_city: str
    equipment_type: str
    comments: str
    maximum_weight_pounds: Optional[int] = None
    maximum_length_feet: Optional[int] = None
    commodity: Optional[str] = None
    special_notes: Optional[str] = None
    driver_should_load: Optional[bool] = None
    driver_should_unload: Optional[bool] = None
    is_team_driver: Optional[bool] = None
