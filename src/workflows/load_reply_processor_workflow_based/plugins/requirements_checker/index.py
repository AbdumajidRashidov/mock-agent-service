import logging
from typing import List, Dict, Any
import json
from ...utils.azure import azure_openai_chat_service
from .prompt import REQUIREMENTS_CHECKER_SYSTEM_PROMPT
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def requirements_checker_plugin(load: Dict[str, Any], truck: Dict[str, Any], response_callback: callable) -> List[str]:
    """Check if load details meet truck requirements.

    Args:
        load (Dict[str, Any]): Load details including origin, destination, and email history
        truck (Dict[str, Any]): Truck details including restrictions, permits, and security

    Returns:
        List[str]: List of abused requirements, empty list if none found
    """
    truck_permits = ", ".join(key for key, value in truck.get('isPermitted', {}).items() if value)
    truck_securities = ", ".join(key for key, value in truck.get('security', {}).items() if value)

    user_content = f"""Truck details (requirements & permits):
{f"- Restrictions (we do not allow these loads): {', '.join(truck['restrictions'])}" if truck.get('restrictions') else ""}
{f"- Permits (Our Permits details): {truck_permits}" if truck_permits else ""}
{f"- Securities (Our Security details): {truck_securities}" if truck_securities else ""}
{f"- Max Length (this is max length truck allow): {truck['maxLength']}" if truck.get('maxLength') else ""}
{f"- Max Weight (this is max weight truck allow): {truck['maxWeight']}" if truck.get('maxWeight') else ""}


Load details:
- Pickup: {load['origin']['city']}, {load['origin']['stateProv']}
- Delivery: {load['destination']['city']}, {load['destination']['stateProv']}
- Commodity: {load['emailHistory']['details'].get('commodity', '')}
{f"- Weight: {load['emailHistory']['details']['weight']}" if load['emailHistory']['details'].get('weight') else ""}
{f"- Special Notes: {load['emailHistory']['details']['specialNotes']}" if load['emailHistory']['details'].get('specialNotes') else ""}"""

    response = await azure_openai_chat_service.complete({
        'messages': [
            {
                'role': 'system',
                'content': REQUIREMENTS_CHECKER_SYSTEM_PROMPT
            },
            {
                'role': 'user',
                'content': user_content
            }
        ],
        'tools': [
            {
                'type': 'function',
                'function': {
                    'name': 'setAbusedRequirements',
                    'description': 'Set the abused requirements',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'abusedRequirements': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'abusedRequirement': {
                                            'type': 'string',
                                            'description': 'Abused requirement'
                                        },
                                        'reason': {
                                            'type': 'string',
                                            'description': "EXACT sentance(s) from load info and truck info which caused the abuse, IF THERE'S NO EXACT REASONS IN BOTH LOAD AND TRUCK INFO, DO NOT MARK AS ABUSED!!!"
                                        }
                                    },
                                    'required': ['abusedRequirement', 'reason']
                                },
                                'description': 'Abused requirements'
                            }
                        },
                        'required': []
                    }
                }
            }
        ]
    })

    tool = response.get('choices', [{}])[0].get('message', {}).get('tool_calls', [None])[0]

    if not tool:
        logger.warning("WARNING::requirementsChecker:: No tool call found", json.dumps(response, indent=2))
        return []

    try:
        parsed_arguments = json.loads(tool['function']['arguments'])
    except (KeyError, json.JSONDecodeError):
        logger.warning("WARNING::requirementsChecker:: Failed to parse tool arguments")
        return []

    abused_requirements = parsed_arguments.get('abusedRequirements', [])

    # Create the plugin response
    plugin_response = {
        "plugin_name": "requirements_checker",
        "response": response,
        "extracted_data": abused_requirements,
    }

    await response_callback({
        "plugin_response": plugin_response,
        "metadata": {
            "timestamp": datetime.now().isoformat()
        }
    })

    if not abused_requirements:
        logger.info("INFO::requirementsChecker:: No abused requirements found", json.dumps(parsed_arguments, indent=2))
        return []

    if abused_requirements:
        logger.info("INFO::requirementsChecker:: Abused requirements found", json.dumps(parsed_arguments, indent=2))

    return [r['abusedRequirement'] for r in abused_requirements]
