"""Load information extraction tool"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider

from ..models.email import EmailMessage
from ..models.responses import PluginResponse
from ..config.prompts import INFO_EXTRACTOR_SYSTEM_PROMPT
from ..config.settings import get_model_config
from .utils import format_email_for_ai

class ExtractedLoadInfo(BaseModel):
    """Structured load information extracted from emails"""

    equipment_type: Optional[str] = Field(None, description="Type of equipment (v=van, f=flatbed, r=reefer, etc.)")
    commodity: Optional[str] = Field(None, description="Type of commodity being shipped")
    weight: Optional[str] = Field(None, description="Weight of the load")
    offering_rate: Optional[float] = Field(None, description="Rate offered by broker")
    delivery_date: Optional[str] = Field(None, description="Delivery date for the load")
    additional_info: Optional[str] = Field(None, description="Any additional relevant information")

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

# Initialize the info extractor agent
info_extractor_agent = Agent(
    model=get_azure_openai_model(),
    system_prompt=INFO_EXTRACTOR_SYSTEM_PROMPT,
    result_type=ExtractedLoadInfo,
)

async def extract_load_info(email: EmailMessage) -> PluginResponse:
    """
    Extract load information from a broker's email.

    Args:
        email: Email message to extract information from

    Returns:
        PluginResponse containing extracted information
    """
    try:
        # Format email for AI processing
        email_content = format_email_for_ai(email, include_headers=False)

        # Run the extraction
        result = await info_extractor_agent.run(email_content)

        # Convert to dict for compatibility
        extracted_data = {}

        if result.data.equipment_type:
            extracted_data["equipmentType"] = result.data.equipment_type

        if result.data.commodity:
            extracted_data["commodity"] = result.data.commodity

        if result.data.weight:
            extracted_data["weight"] = result.data.weight

        if result.data.offering_rate:
            extracted_data["offeringRate"] = result.data.offering_rate

        if result.data.delivery_date:
            extracted_data["deliveryDate"] = result.data.delivery_date

        if result.data.additional_info:
            extracted_data["additionalInfo"] = result.data.additional_info

        return PluginResponse(
            plugin_name="info_extractor",
            success=True,
            extracted_data=extracted_data,
            response={"raw_result": result.data.dict()}
        )

    except Exception as e:
        return PluginResponse(
            plugin_name="info_extractor",
            success=False,
            error_message=str(e),
            extracted_data={}
        )

def validate_extracted_info(info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize extracted load information.

    Args:
        info: Raw extracted information dictionary

    Returns:
        Validated and normalized information
    """
    validated_info = {}

    # Validate equipment type
    if "equipmentType" in info and info["equipmentType"]:
        equipment_type = str(info["equipmentType"]).lower().strip()

        # Normalize equipment type codes
        equipment_map = {
            'van': 'v', 'vans': 'v', 'dry van': 'v',
            'flatbed': 'f', 'flatbeds': 'f', 'flat bed': 'f',
            'reefer': 'r', 'reefers': 'r', 'refrigerated': 'r',
            'step deck': 'sd', 'stepdeck': 'sd',
            'lowboy': 'lb', 'low boy': 'lb',
            'tanker': 't', 'tank': 't',
            'container': 'c', 'containers': 'c'
        }

        validated_info["equipmentType"] = equipment_map.get(equipment_type, equipment_type)

    # Validate weight - ensure it's a reasonable number
    if "weight" in info and info["weight"]:
        weight_str = str(info["weight"]).replace(',', '').replace('lbs', '').replace('lb', '').strip()
        try:
            weight_num = float(weight_str)
            if 100 <= weight_num <= 80000:  # Reasonable freight weight range
                validated_info["weight"] = weight_str
        except ValueError:
            pass  # Skip invalid weights

    # Validate offering rate
    if "offeringRate" in info and info["offeringRate"]:
        try:
            rate = float(info["offeringRate"])
            if 100 <= rate <= 50000:  # Reasonable freight rate range
                validated_info["offeringRate"] = rate
        except (ValueError, TypeError):
            pass  # Skip invalid rates

    # Copy other fields as-is if they exist
    for field in ["commodity", "deliveryDate", "additionalInfo"]:
        if field in info and info[field]:
            validated_info[field] = str(info[field]).strip()

    return validated_info

def merge_extracted_info_with_load(extracted_info: Dict[str, Any], load_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge extracted information with existing load data.

    Args:
        extracted_info: Newly extracted information
        load_data: Existing load data

    Returns:
        Updated load data with merged information
    """
    # Validate the extracted info first
    validated_info = validate_extracted_info(extracted_info)

    # Prepare field updates for the database
    field_updates = {}

    # Update equipment type at top level
    if "equipmentType" in validated_info:
        field_updates["equipmentType"] = validated_info["equipmentType"]

    # Update details in email history
    email_history_updates = {}

    if "commodity" in validated_info:
        email_history_updates["emailHistory.details.commodity"] = validated_info["commodity"]

    if "weight" in validated_info:
        email_history_updates["emailHistory.details.weight"] = validated_info["weight"]

    if "deliveryDate" in validated_info:
        email_history_updates["emailHistory.details.deliveryDateTime"] = validated_info["deliveryDate"]

    # Update rate information
    if "offeringRate" in validated_info:
        field_updates["rateInfo.rateUsd"] = validated_info["offeringRate"]
        field_updates["rateInfo.isAIIdentified"] = True

    # Merge all updates
    field_updates.update(email_history_updates)

    return field_updates
