from agents import Agent, RunContextWrapper
from workflows.load_reply_processsor.models import OrchestratorContext, TruckContext

def get_permit_and_security_items(truck: TruckContext):
    """Extract permit and security items from TruckContext."""
    if not truck:
        return {
            "permittedItems": [],
            "securityItems": []
        }

    # Extract permits that are False (not permitted)
    permit_fields = [
        "permit_hazmat", "permit_tanker", "permit_double_triple_trailers",
        "permit_combination_endorsements", "permit_oversize_overweight",
        "permit_hazardous_waste_radiological", "permit_canada_operating_authority",
        "permit_mexico_operating_authority"
    ]

    # Extract security features that are False (not available)
    security_fields = [
        "security_tsa", "security_twic", "security_heavy_duty_lock",
        "security_escort_driving_ok", "security_cross_border_loads"
    ]

    permitted_items = [field.replace("permit_", "").replace("_", " ").title()
                      for field in permit_fields
                      if hasattr(truck, field) and getattr(truck, field) is False]

    security_items = [field.replace("security_", "").replace("_", " ").title()
                     for field in security_fields
                     if hasattr(truck, field) and getattr(truck, field) is False]

    return {
        "permittedItems": permitted_items,
        "securityItems": security_items
    }

def get_restricted_items(truck: TruckContext):
    """Extract restricted items, permits, and security features from TruckContext."""
    result = {
        "permittedItems": [],
        "securityItems": []
    }

    # Extract permits and security items
    permit_and_security = get_permit_and_security_items(truck)
    result["permittedItems"] = permit_and_security.get("permittedItems", [])
    result["securityItems"] = permit_and_security.get("securityItems", [])

    return result

def dynamic_compliance_checker_instructions(
    context: RunContextWrapper[OrchestratorContext], agent: Agent[OrchestratorContext]
) -> str:
    # Extract truck and load info from context
    truck = context.context.truck_context
    load = context.context.load_context

    already_found_restrictions =context.context.load_context.warnings
    # Get restricted items, permits, and security features
    warnings_list = get_restricted_items(truck)

    # Prepare string representations safely
    restrictions = truck.restrictions if hasattr(truck, "restrictions") else []
    permits = warnings_list["permittedItems"]
    securities = warnings_list["securityItems"]
    team_solo = truck.team_solo if hasattr(truck, "team_solo") else "Unknown"
    max_length = truck.length if hasattr(truck, "length") else "Unknown"
    max_weight = truck.weight if hasattr(truck, "weight") else "Unknown"

    pickup_location = f"{load.origin.city}, {load.origin.state_prov}" if hasattr(load, "origin") and load.origin else "Not provided"
    delivery_location = f"{load.destination.city}, {load.destination.state_prov}" if hasattr(load, "destination") and load.destination else "Not provided"

    instructions = f"""
You are a Compliance Checker Agent specialized in analyzing broker emails, load details, and conversation context against truck attributes to identify compliance issues.

Your tasks:
1. Carefully review input email, load details, and conversation context.
2. Cross-reference with already identified warnings to avoid duplicates.
3. Compare against truck attributes (restrictions, permits, etc.).
4. Identify NEW compliance issues using these rules:

## Mandatory Warning Conditions
- Load requires team drivers but truck is solo
- Load exceeds truck's max length/weight

## Conditional Warning Conditions
⚠️ Flag these ONLY if truck has relevant attributes:
- Commodity matches truck's restricted items list
- Missing required permits from truck's permits list
- Missing security features from truck's securities list

## Critical Implementation Rules
**DO:**
- Treat empty restriction/permit/security lists as NO limitations
- Only use explicit attributes from truck data (no assumptions)
- Check against already found warnings: {already_found_restrictions}

**DON'T:**
- Create duplicate warnings
- Assume restrictions beyond what's explicitly listed
- Use default rules not in truck attributes

## Truck Attributes
- Restrictions: {restrictions}
- Permits: {permits}
- Securities: {securities}
- Team/Solo: {team_solo}
- Max Length: {max_length}
- Max Weight: {max_weight}

## Load Context
- Pickup: {pickup_location}
- Delivery: {delivery_location}
- Commodity: {getattr(load, 'commodity', 'Not specified')}
- Details: {load.comments}
"""
    return instructions
