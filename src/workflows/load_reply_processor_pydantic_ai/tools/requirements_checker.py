"""Requirements validation tool for freight loads"""

from typing import List
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider

from ..models.load import LoadInfo
from ..models.company import TruckInfo
from ..models.responses import PluginResponse, AbusedRequirement
from ..config.prompts import REQUIREMENTS_CHECKER_SYSTEM_PROMPT
from ..config.settings import get_model_config

class RequirementViolation(BaseModel):
    """Individual requirement violation"""

    abused_requirement: str = Field(alias="abusedRequirement")
    reason: str
    severity: str = "warning"

class RequirementsCheckResult(BaseModel):
    """Result of requirements validation"""

    abused_requirements: List[RequirementViolation] = Field(default_factory=list, alias="abusedRequirements")

def get_azure_openai_model():
    """Get configured Azure OpenAI model"""
    config = get_model_config()

    model = OpenAIModel(
        config['model'],
        provider=AzureProvider(
            azure_endpoint=config['endpoint'],
            api_version='2024-06-01',
            api_key=config['api_key'],
        ),
    )

    return model

# Initialize requirements checker agent
requirements_checker_agent = Agent(
    model=get_azure_openai_model(),
    system_prompt=REQUIREMENTS_CHECKER_SYSTEM_PROMPT,
    result_type=RequirementsCheckResult,
)

async def check_requirements(load_info: LoadInfo, truck_info: TruckInfo) -> PluginResponse:
    """
    Check if load requirements match truck capabilities.
    FIXED VERSION - Much more conservative approach.
    """
    try:
        # First do rule-based checking for obvious violations
        rule_based_violations = []

        # Weight check
        if load_info.email_history.details.weight and truck_info.max_weight:
            weight_violations = validate_weight_requirements(
                load_info.email_history.details.weight,
                truck_info.max_weight
            )
            rule_based_violations.extend(weight_violations)

        # Permit requirements
        permit_violations = validate_permit_requirements(load_info, truck_info)
        rule_based_violations.extend(permit_violations)

        # If we found obvious violations, return them without AI check
        if rule_based_violations:
            return PluginResponse(
                plugin_name="requirements_checker",
                success=True,
                extracted_data=rule_based_violations,
                response={"violations_count": len(rule_based_violations), "method": "rule_based"}
            )

        # Only use AI for edge cases where rule-based didn't find clear violations
        # Build context for requirements checking
        context = _build_requirements_context(load_info, truck_info)

        # Run the AI requirements check (more conservative now)
        result = await requirements_checker_agent.run(context)

        # Convert to AbusedRequirement objects
        abused_requirements = []
        for violation in result.data.abused_requirements:
            abused_requirements.append(AbusedRequirement(
                abused_requirement=violation.abused_requirement,
                reason=violation.reason,
                severity=violation.severity
            ))

        return PluginResponse(
            plugin_name="requirements_checker",
            success=True,
            extracted_data=abused_requirements,
            response={"violations_count": len(abused_requirements), "method": "ai_assisted"}
        )

    except Exception as e:
        return PluginResponse(
            plugin_name="requirements_checker",
            success=False,
            error_message=str(e),
            extracted_data=[]
        )

def _build_requirements_context(load_info: LoadInfo, truck_info: TruckInfo) -> str:
    """Build context string for requirements checking - ENHANCED VERSION"""

    context_parts = ["TRUCK CAPABILITIES AND RESTRICTIONS:"]

    # Add truck restrictions (what we CAN'T haul)
    if truck_info.restrictions:
        context_parts.append(f"- RESTRICTIONS (We DO NOT haul these): {', '.join(truck_info.restrictions)}")

    # Add truck permits (what we CAN haul)
    permits = truck_info.is_permitted.get_active_permits()
    if permits:
        context_parts.append(f"- PERMITS (We ARE certified for): {', '.join(permits)}")
    else:
        context_parts.append(f"- PERMITS: No special permits (standard dry van only)")

    # Add capacity limits
    if truck_info.max_weight:
        context_parts.append(f"- MAX WEIGHT: {truck_info.max_weight:,} lbs")

    if truck_info.max_length:
        context_parts.append(f"- MAX LENGTH: {truck_info.max_length} ft")

    # Add load details
    context_parts.append("\nLOAD REQUIREMENTS:")
    context_parts.append(f"- Route: {load_info.origin} → {load_info.destination}")

    if load_info.email_history.details.commodity:
        context_parts.append(f"- COMMODITY: {load_info.email_history.details.commodity}")

    if load_info.email_history.details.weight:
        context_parts.append(f"- WEIGHT: {load_info.email_history.details.weight}")

    if load_info.equipment_type:
        context_parts.append(f"- EQUIPMENT: {load_info.equipment_type}")

    # Add any special notes or requirements mentioned
    if load_info.email_history.details.special_notes:
        context_parts.append(f"- SPECIAL REQUIREMENTS: {load_info.email_history.details.special_notes}")

    context_parts.append(f"\nDETECT VIOLATIONS: Compare load requirements against truck capabilities.")
    context_parts.append(f"Look for mismatches like hazmat loads vs non-hazmat trucks, weight overages, etc.")

    return "\n".join(context_parts)

def validate_permit_requirements(load_info: LoadInfo, truck_info: TruckInfo) -> List[AbusedRequirement]:
    """
    Validate permit requirements for the load.
    FIXED VERSION - Much more conservative, only flag ACTUAL violations.
    """
    violations = []

    # Get commodity and any special requirements
    commodity = load_info.email_history.details.commodity or ""
    special_notes = load_info.email_history.details.special_notes or ""

    # Combine all text that might indicate requirements
    combined_text = f"{commodity} {special_notes}".lower()

    # MUCH MORE CONSERVATIVE hazmat detection - only flag obvious hazmat
    explicit_hazmat_indicators = [
        'hazmat required', 'hazmat certification', 'dangerous goods required',
        'un number', 'dot classification', 'hazmat endorsement needed'
    ]

    # Only flag as hazmat if explicitly stated OR obvious chemicals
    explicit_hazmat = any(indicator in combined_text for indicator in explicit_hazmat_indicators)

    # Or if it's clearly industrial chemicals with hazmat context
    chemical_hazmat = (
        'industrial chemicals' in combined_text and
        ('hazmat' in combined_text or 'dangerous' in combined_text)
    )

    needs_hazmat = explicit_hazmat or chemical_hazmat

    # DO NOT flag these as hazmat (common false positives):
    safe_commodities = [
        'electronics', 'auto parts', 'furniture', 'retail goods',
        'clothing', 'food', 'produce', 'steel parts', 'machinery'
    ]

    if any(safe_commodity in combined_text for safe_commodity in safe_commodities):
        needs_hazmat = False

    if needs_hazmat and not truck_info.is_permitted.hazmat:
        violations.append(AbusedRequirement(
            abused_requirement="Hazmat certification required",
            reason=f"Load explicitly requires hazmat certification but truck is not hazmat certified",
            severity="error"
        ))

    # CONSERVATIVE oversize detection - only flag if explicitly mentioned
    explicit_oversize = any(keyword in combined_text for keyword in [
        'oversize required', 'oversize permit needed', 'wide load permit',
        'over-dimensional', 'special permits required'
    ])

    if explicit_oversize and not truck_info.is_permitted.oversize:
        violations.append(AbusedRequirement(
            abused_requirement="Oversize permit required",
            reason="Load explicitly requires oversize permit but truck does not have oversize permits",
            severity="warning"
        ))

    # CONSERVATIVE temperature requirements - only flag if equipment mismatch
    reefer_required = any(keyword in combined_text for keyword in [
        'reefer', 'refrigerated', 'frozen', 'temperature controlled', 'temp controlled'
    ])

    # Check equipment type from load
    load_equipment = getattr(load_info, 'equipment_type', None)
    if hasattr(load_equipment, 'value'):
        load_equipment = load_equipment.value

    # Only flag if load specifically requires reefer but truck can't do it
    if (reefer_required or load_equipment == 'r') and not truck_info.is_permitted.refrigerated:
        violations.append(AbusedRequirement(
            abused_requirement="Refrigerated equipment required",
            reason="Load requires temperature control but truck is not refrigerated",
            severity="error"
        ))

    return violations

def validate_weight_requirements(load_weight: str, truck_max_weight: float) -> List[AbusedRequirement]:
    """
    Validate weight requirements against truck capacity.
    FIXED VERSION - More accurate weight parsing.
    """
    violations = []

    if not load_weight or not truck_max_weight:
        return violations

    try:
        # Extract numeric weight - handle various formats
        weight_str = str(load_weight).replace(',', '').replace('lbs', '').replace('lb', '').strip()

        # Handle "42k" format
        if weight_str.endswith('k'):
            weight_num = float(weight_str[:-1]) * 1000
        else:
            weight_num = float(weight_str)

        # Only flag if significantly over capacity (allow small buffer)
        if weight_num > (truck_max_weight + 1000):  # 1000 lb buffer for minor discrepancies
            violations.append(AbusedRequirement(
                abused_requirement="Weight exceeds truck capacity",
                reason=f"Load weight {weight_num:,.0f} lbs exceeds truck maximum {truck_max_weight:,.0f} lbs",
                severity="error"
            ))

    except (ValueError, AttributeError):
        # If we can't parse the weight, don't flag as violation
        pass

    return violations

def validate_permit_requirements(load_info: LoadInfo, truck_info: TruckInfo) -> List[AbusedRequirement]:
    """
    Validate permit requirements for the load.

    Args:
        load_info: Load information
        truck_info: Truck permit information

    Returns:
        List of permit-related violations
    """
    violations = []

    # Check for hazmat requirements
    commodity = load_info.email_history.details.commodity or ""
    special_notes = load_info.email_history.details.special_notes or ""

    combined_text = f"{commodity} {special_notes}".lower()

    # Hazmat keywords
    hazmat_keywords = ['hazmat', 'dangerous', 'chemical', 'flammable', 'toxic', 'corrosive']
    needs_hazmat = any(keyword in combined_text for keyword in hazmat_keywords)

    if needs_hazmat and not truck_info.is_permitted.hazmat:
        violations.append(AbusedRequirement(
            abused_requirement="Hazmat permit required",
            reason="Load appears to require hazmat permit but truck is not hazmat certified",
            severity="error"
        ))

    # Check for oversize/overweight keywords
    oversize_keywords = ['oversize', 'over size', 'wide load', 'oversized']
    needs_oversize = any(keyword in combined_text for keyword in oversize_keywords)

    if needs_oversize and not truck_info.is_permitted.oversize:
        violations.append(AbusedRequirement(
            abused_requirement="Oversize permit required",
            reason="Load appears to require oversize permit but truck does not have oversize permits",
            severity="warning"
        ))

    # Check for temperature requirements
    temp_keywords = ['refrigerated', 'frozen', 'temp controlled', 'temperature', 'cold', 'freeze']
    needs_refrigerated = any(keyword in combined_text for keyword in temp_keywords)

    if needs_refrigerated and not truck_info.is_permitted.refrigerated:
        violations.append(AbusedRequirement(
            abused_requirement="Refrigerated equipment required",
            reason="Load appears to require temperature control but truck is not refrigerated",
            severity="error"
        ))

    return violations
