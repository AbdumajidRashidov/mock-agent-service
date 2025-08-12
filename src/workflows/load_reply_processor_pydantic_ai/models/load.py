"""Load and freight models for the negotiation system"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import Field, ConfigDict
from .base import BaseModel, Location

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

class LoadDetails(BaseModel):
    """Detailed information about the load"""

    model_config = ConfigDict(extra="allow")  # Allow extra fields

    commodity: Optional[str] = None
    weight: Optional[str] = None
    delivery_date_time: Optional[str] = Field(None, alias="deliveryDateTime")
    special_notes: Optional[str] = Field(None, alias="specialNotes")

    # Additional details that might be extracted
    dimensions: Optional[str] = None
    temperature_requirements: Optional[str] = None
    loading_instructions: Optional[str] = None
    delivery_instructions: Optional[str] = None

class RouteInfo(BaseModel):
    """Route information for the load"""

    model_config = ConfigDict(extra="allow")

    origin: Location
    destination: Location
    distance_miles: Optional[float] = None
    estimated_drive_time: Optional[str] = None

    def get_route_description(self) -> str:
        """Get human-readable route description"""
        return f"{self.origin} to {self.destination}"

class LoadHistory(BaseModel):
    """Historical information about load processing"""

    model_config = ConfigDict(extra="allow")  # Allow extra fields

    details: LoadDetails = Field(default_factory=LoadDetails)
    negotiation_step: Optional[int] = Field(None, alias="negotitationStep")  # Note: keeping original typo for compatibility
    offered_rates: List[Dict[str, Any]] = Field(default_factory=list, alias="offeredRates")

class LoadInfo(BaseModel):
    """Complete load information - flexible to handle existing data"""

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True
    )

    id: Optional[str] = None
    posters_reference_id: Optional[str] = Field(None, alias="postersReferenceId")

    # Basic info
    status: Optional[str] = "active"
    equipment_type: Optional[str] = Field(None, alias="equipmentType")

    # Route information - make optional for power-only loads
    origin: Optional[Location] = None
    destination: Optional[Location] = None
    route: Optional[RouteInfo] = None

    # Rate information
    rate_info: Optional[Dict[str, Any]] = Field(None, alias="rateInfo")

    # Load details
    email_history: LoadHistory = Field(default_factory=LoadHistory, alias="emailHistory")

    # Flags and warnings
    warnings: List[str] = Field(default_factory=list)
    is_bid_request_sent: bool = Field(False, alias="isBidRequestSent")

    def __init__(self, **data):
        # Handle missing origin/destination by creating dummy ones
        if not data.get('origin') and not data.get('destination'):
            # For power-only or missing location data, create placeholder
            data['origin'] = {'city': 'TBD', 'stateProv': 'TBD'}
            data['destination'] = {'city': 'TBD', 'stateProv': 'TBD'}

        super().__init__(**data)

        # Create route info from origin/destination if not provided
        if not self.route and self.origin and self.destination:
            self.route = RouteInfo(
                origin=self.origin,
                destination=self.destination
            )
