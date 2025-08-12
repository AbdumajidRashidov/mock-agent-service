from typing import Optional, TypedDict

class LoadInfo(TypedDict, total=False):
    equipmentType: Optional[str]
    commodity: Optional[str]
    weight: Optional[str]
    offeringRate: Optional[float]
    deliveryDate: Optional[str]
    additionalInfo: Optional[str]
