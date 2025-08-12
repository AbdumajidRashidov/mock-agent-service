"""Company and truck models for freight operations"""

from typing import Optional, List, Dict, Any
from pydantic import Field, validator, ConfigDict

from .base import BaseModel

class PermitInfo(BaseModel):
    """Truck permit information"""

    oversize: bool = False
    overweight: bool = False
    hazmat: bool = False
    refrigerated: bool = False
    specialized: bool = False

    def get_active_permits(self) -> List[str]:
        """Get list of active permits"""
        permits = []
        if self.oversize:
            permits.append("oversize")
        if self.overweight:
            permits.append("overweight")
        if self.hazmat:
            permits.append("hazmat")
        if self.refrigerated:
            permits.append("refrigerated")
        if self.specialized:
            permits.append("specialized")
        return permits

class SecurityInfo(BaseModel):
    """Truck security information"""

    gps_tracking: bool = Field(False, alias="gpsTracking")
    cargo_insurance: bool = Field(False, alias="cargoInsurance")
    security_seal: bool = Field(False, alias="securitySeal")
    driver_background_check: bool = Field(False, alias="driverBackgroundCheck")

    def get_active_security_features(self) -> List[str]:
        """Get list of active security features"""
        features = []
        if self.gps_tracking:
            features.append("GPS tracking")
        if self.cargo_insurance:
            features.append("cargo insurance")
        if self.security_seal:
            features.append("security seal")
        if self.driver_background_check:
            features.append("driver background check")

class TruckInfo(BaseModel):
    """Truck capabilities and restrictions"""

    model_config = ConfigDict(extra="allow")  # Allow extra fields

    # Capacity limits
    max_weight: Optional[float] = Field(None, alias="maxWeight")
    max_length: Optional[float] = Field(None, alias="maxLength")
    max_width: Optional[float] = None
    max_height: Optional[float] = None

    # Restrictions (loads we cannot take)
    restrictions: List[str] = Field(default_factory=list)

    # Capabilities
    is_permitted: PermitInfo = Field(default_factory=PermitInfo, alias="isPermitted")
    security: SecurityInfo = Field(default_factory=SecurityInfo)

    # Equipment details
    equipment_type: Optional[str] = Field(None, alias="equipmentType")
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None

    @validator('max_weight', 'max_length', 'max_width', 'max_height', pre=True)
    def validate_positive_values(cls, v):
        """Ensure capacity values are positive"""
        if v is not None and v <= 0:
            raise ValueError("Capacity values must be positive")
        return v

    def can_handle_weight(self, weight: float) -> bool:
        """Check if truck can handle given weight"""
        return self.max_weight is None or weight <= self.max_weight

    def can_handle_length(self, length: float) -> bool:
        """Check if truck can handle given length"""
        return self.max_length is None or length <= self.max_length

    def has_restriction(self, commodity: str) -> bool:
        """Check if truck has restriction for given commodity"""
        return any(restriction.lower() in commodity.lower() for restriction in self.restrictions)

    def get_capabilities_summary(self) -> str:
        """Get human-readable capabilities summary"""
        parts = []

        if self.max_weight:
            parts.append(f"Max weight: {self.max_weight:,} lbs")

        if self.max_length:
            parts.append(f"Max length: {self.max_length} ft")

        permits = self.is_permitted.get_active_permits()
        if permits:
            parts.append(f"Permits: {', '.join(permits)}")

        security = self.security.get_active_security_features()
        if security:
            parts.append(f"Security: {', '.join(security)}")

        if self.restrictions:
            parts.append(f"Restrictions: {', '.join(self.restrictions)}")

        return "; ".join(parts)

class CompanyDetails(BaseModel):
    """Company information and settings"""

    model_config = ConfigDict(extra="allow")  # Allow extra fields

    # Basic company info
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    mc_number: Optional[str] = Field(None, alias="mcNumber")
    details: Optional[str] = None

    # Negotiation settings - allow dict for flexibility
    rate_negotiation: Optional[Dict[str, Any]] = Field(None, alias="rateNegotiation")

    # Business rules
    auto_book_threshold: Optional[float] = Field(None, alias="autoBookThreshold")
    minimum_profit_margin: Optional[float] = Field(None, alias="minimumProfitMargin")
    preferred_lanes: List[str] = Field(default_factory=list, alias="preferredLanes")
    blacklisted_brokers: List[str] = Field(default_factory=list, alias="blacklistedBrokers")

    @validator('mc_number', pre=True)
    def format_mc_number(cls, v):
        """Format MC number consistently"""
        if v and isinstance(v, (str, int)):
            return str(v).replace("MC", "").replace("#", "").strip()
        return v

    def has_negotiation_settings(self) -> bool:
        """Check if company has rate negotiation settings configured"""
        return (
            self.rate_negotiation is not None
            and isinstance(self.rate_negotiation, dict)
            and 'firstBidThreshold' in self.rate_negotiation
            and 'secondBidThreshold' in self.rate_negotiation
            and 'rounding' in self.rate_negotiation
        )

    def get_company_signature(self) -> str:
        """Get company signature for emails"""
        parts = []

        if self.name:
            parts.append(f"Best Regards\n{self.name}")
        else:
            parts.append("Best Regards")

        if self.mc_number:
            parts.append(f"MC #{self.mc_number}")

        parts.append("Powered by Numeo")

        return "\n\n".join(parts)

    def is_broker_blacklisted(self, broker_email: str) -> bool:
        """Check if a broker is blacklisted"""
        return any(
            blacklisted.lower() in broker_email.lower()
            for blacklisted in self.blacklisted_brokers
        )
