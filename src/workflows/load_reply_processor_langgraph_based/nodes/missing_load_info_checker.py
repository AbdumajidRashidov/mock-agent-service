from typing import Dict, Any, List

def get_load_missing_fields(load: Dict[str, Any]) -> List[str]:
    missing_fields = []
    if not load.get("shipmentDetails", {}).get("maximumWeightPounds") and not load.get("emailHistory", {}).get("details", {}).get("weight"):
        missing_fields.append("weight")

    if not load.get("shipmentDetails", {}).get("maximumLengthFeet") and not load.get("emailHistory", {}).get("details", {}).get("length"):
        missing_fields.append("length")

    if not load.get("emailHistory", {}).get("details", {}).get("commodity"):
        missing_fields.append("commodity")

    if not load.get("earliestAvailability") and not load.get("latestAvailability") and not load.get("emailHistory", {}).get("details", {}).get("pickupDateTime"):
        missing_fields.append("pickupDateTime")

    if not load.get("emailHistory", {}).get("details", {}).get("deliveryDateTime"):
        missing_fields.append("deliveryDateTime")

    if not load.get("rateInfo", {}).get("rate"):
        missing_fields.append("offeringRate")

    if not load.get("emailHistory", {}).get("details", {}).get("specialNotes"):
        missing_fields.append("specialNotes")

    return missing_fields
