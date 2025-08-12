"""
Models for load reply processor workflow.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional
import re
from pydantic import BaseModel


from typing import List, Optional
from pydantic import BaseModel, Field

class UpdateDetailsPayload(BaseModel):
    commodity:      Optional[str]  = Field(None, description="Cargo description")
    equipment:      Optional[str]  = Field(None, description="Equipment type code, e.g. V, R, F")
    delivery_date:  Optional[str]  = Field(None, description="YYYY-MM-DD")
    weight:         Optional[float] = Field(None, description="Weight in pounds")
    offering_rate:  Optional[float] = Field(None, description="Rate the broker is offering (USD)")


class AgentsReq(BaseModel):
    query: str

class EmailSendingClass(BaseModel):
    body: str


class WarningsReq(BaseModel):
    warnings: List[str]


# class WarningItems(BaseModel):
#     restrictedItems: List[str]
#     permits: List[str]
#     security: List[str]
#     excludedStates: List[str]

class RateNegotiation(BaseModel):
    first_bid_threshold: float
    second_bid_threshold: float
    rounding: float

class CompanyInfo(BaseModel):
    name: str
    mc_number: str
    details: str
    rate_negotiation: Optional[RateNegotiation] = None


from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone_number: Optional[str] = None


class CreditInfo(BaseModel):
    as_of: str = ""
    credit_score: int = 0
    days_to_pay: int = 0


class PosterInfo(BaseModel):
    contact: ContactInfo = ContactInfo()
    carrier_home_state: str = ""
    city: str = ""
    company_name: str = ""
    preferred_contact_method: str = ""
    mc_number: str = ""
    credit: CreditInfo = CreditInfo()


class RateInfo(BaseModel):
    basis: str = ""
    rate_usd: float = 0
    minimum_rate: Optional[float] = None
    maximum_rate: Optional[float] = None


class ShipmentDetails(BaseModel):
    type: str = ""
    full_partial: str = ""
    maximum_length_feet: Optional[int] = 0
    maximum_weight_pounds: Optional[int] = 0


class LocationInfo(BaseModel):
    type: str = "Point"
    coordinates: List[float] = []
    city: str = ""
    state_prov: str = ""
    postal_code: Optional[str] = None
    country: Optional[str] = None
    label: Optional[str] = None
    state_code: Optional[str] = None


class Revenue(BaseModel):
    charge_amount: float = 0
    profit_margin: float = 0


class LoadContext(BaseModel):
    # Basic load identifiers
    load_id: str
    load_search_id: Optional[str] = None
    external_id: Optional[str] = None
    posters_reference_id: Optional[str] = None
    route_id: Optional[str] = None
    booking_url: Optional[str] = None

    # Load details
    commodity: Optional[str] = None
    weight: Optional[float] = None
    equipment_type: Optional[str] = None

    # Dates and timing
    earliest_availability: Optional[str] = None
    latest_availability: Optional[str] = None
    posted_at: Optional[str] = None
    duration: Optional[int] = None

    # Locations
    origin: Optional[LocationInfo] = None  # Changed from flat structure to nested
    destination: Optional[LocationInfo] = None  # Changed from flat structure to nested

    # Trip details
    trip_length: Optional[int] = None  # In miles
    length: Optional[int] = None  # In feet (for the load)
    polyline: Optional[str] = None  # Encoded route polyline

    # Shipment details
    shipment_details: ShipmentDetails = ShipmentDetails()

    # Rate and financial information
    rate_info: RateInfo = RateInfo()
    revenue: Revenue = Revenue()

    # Poster information
    poster_info: PosterInfo = PosterInfo()

    # Status information
    status: Optional[str] = None  # cancelled or active
    is_factorable: bool = False
    is_info_request_sent: bool = False
    is_bid_request_sent: bool = False

    # Requirements
    permits_required: List[str] = []
    certifications_required: List[str] = []

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Comments
    comments: Optional[str] = None

    # Session information
    session_start: Optional[datetime] = None

    # Warnings
    warnings: Optional[List[str]] = None

    class Config:
        populate_by_name = True

    def model_post_init(self, __context):
        if self.session_start is None:
            self.session_start = datetime.now()

        # For backward compatibility - if origin/destination aren't set but flat fields are
        if self.origin is None and hasattr(self, 'origin_city'):
            self.origin = LocationInfo(
                city=self.origin_city or "",
                state_prov=self.origin_state or "",
                postal_code=self.origin_postal_code,
                country=self.origin_country,
                coordinates=self.origin_coordinates or []
            )

        if self.destination is None and hasattr(self, 'destination_city'):
            self.destination = LocationInfo(
                city=self.destination_city or "",
                state_prov=self.destination_state or "",
                postal_code=self.destination_postal_code,
                country=self.destination_country,
                coordinates=self.destination_coordinates or []
            )


class TruckContext(BaseModel):
    # Main truck identifiers
    id: str
    truck_id: Optional[str] = None
    load_id: Optional[str] = None
    tteld_vin: Optional[str] = None
    samsara_id: Optional[str] = None
    main_info: Optional[str] = None

    # Driver information (simplified, could be expanded to match proto Driver message)
    first_driver_name: Optional[str] = None
    first_driver_phone: Optional[str] = None
    first_driver_is_us_citizen: Optional[bool] = None
    second_driver_name: Optional[str] = None

    # Equipment information
    equipment_type: Optional[str] = None
    equipment_values: List[str] = []
    length: Optional[int] = None
    weight: Optional[int] = None

    # Restrictions and requirements
    restrictions: List[str] = []
    excluded_states: List[str] = []

    # Permits (matching proto Permits message)
    permit_hazmat: Optional[bool] = False
    permit_tanker: Optional[bool] = False
    permit_double_triple_trailers: Optional[bool] = False
    permit_combination_endorsements: Optional[bool] = False
    permit_canada_operating_authority: Optional[bool] = False
    permit_mexico_operating_authority: Optional[bool] = False
    permit_oversize_overweight: Optional[bool] = False
    permit_hazardous_waste_radiological: Optional[bool] = False

    # Security (matching proto Security message)
    security_tsa: Optional[bool] = False
    security_twic: Optional[bool] = False
    security_heavy_duty_lock: Optional[bool] = False
    security_escort_driving_ok: Optional[bool] = False
    security_cross_border_loads: Optional[bool] = False

    # Travel preferences
    deadhead_origin: Optional[str] = None
    deadhead_destination: Optional[str] = None
    team_solo: str = "SOLO"
    weekly_gross_target: Optional[int] = None
    max_travel_distance: Optional[int] = None
    min_travel_distance: Optional[int] = None
    max_travel_hours_per_day: Optional[str] = None
    full_partial: str = "BOTH"
    avoid_winter_roads: bool = False

    # Integration flags
    eld_integration: Optional[bool] = False

    # Timestamps
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Legacy fields for backward compatibility
    permits_required: List[str] = []
    certifications_required: List[str] = []
    security_required: List[str] = []
    equipment_required: Optional[str] = None

    class Config:
        populate_by_name = True


class NegotiatorOutput(BaseModel):
    rate: float
    reasoning: str


class AnalyzerAgentOutput(BaseModel):
    extracted_details: UpdateDetailsPayload
    missing_details: list[str]
    warnings: list[str]
    cancelled: bool
    negotiation_rate: Optional[NegotiatorOutput] = None

@dataclass
class OrchestratorContext:
    load_context: LoadContext
    truck_context: TruckContext
    company_info: CompanyInfo
    load_id: str
    thread_id: str
    application_name: str
    email_id: str
    subject: str
    conversation_history: List[Dict[str, str]]
    missing_information: Optional[List[str]] = None

@dataclass
class CommunicatorContext(BaseModel):
    load_context: LoadContext
    truck_context: TruckContext
    company_info: CompanyInfo
    load_id: str
    thread_id: str
    application_name: str
    email_id: str
    subject: str
    conversation_history: List[Dict[str, str]]
    missing_information: Optional[List[str]] = None
    result: AnalyzerAgentOutput

