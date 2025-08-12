import logging
from typing import Optional, Dict, Any, Callable
import json
from ...utils.azure import azure_openai_chat_service
from .prompt import INFO_EXTRACTOR_SYSTEM_PROMPT
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def info_extractor_plugin(email_content: str, response_callback: Optional[Callable] = None) -> Optional[Dict[str, Any]]:
    """Extract load information from a broker's email.

    Args:
        email_content (str): Content of the broker's reply email
        response_callback (Optional[Callable]): Optional callback function for streaming responses

    Returns:
        Optional[Dict[str, Any]]: Extracted load information or None if extraction fails
        Optional[LoadInfo]: Extracted load information or None if extraction fails
    """
    response = await azure_openai_chat_service.complete({
        'messages': [
            {
                'role': 'system',
                'content': INFO_EXTRACTOR_SYSTEM_PROMPT
            },
            {
                'role': 'user',
                'content': email_content
            }
        ],
        'tools': [
            {
                'type': 'function',
                'function': {
                    'name': 'setInfo',
                    'description': 'Set the information of the load',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'equipmentType': {
                                'type': 'string',
                                'description': 'Equipment type of the load'
                            },
                            'commodity': {
                                'type': 'string',
                                'description': 'Commodity of the load'
                            },
                            'weight': {
                                'type': 'string',
                                'description': 'Weight of the load'
                            },
                            'offeringRate': {
                                'type': 'number',
                                'description': 'Offering rate of the load'
                            },
                            'deliveryDate': {
                                'type': 'string',
                                'description': 'Delivery date of the load'
                            },
                            'additionalInfo': {
                                'type': 'string',
                                'description': 'Any additional information about the load'
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
        logger.warning("WARNING::infoExtractor:: No tool call found", json.dumps(response, indent=2))
        return None

    try:
        parsed_arguments = json.loads(tool['function']['arguments'])
    except (KeyError, json.JSONDecodeError):
        logger.warning("WARNING::infoExtractor:: Failed to parse tool arguments")
        return None

    # Create the plugin response
    plugin_response = {
        "plugin_name": "info_extractor",
        "response": response,
        "extracted_data": parsed_arguments,
    }

    await response_callback({
        "plugin_response": plugin_response,
        "metadata": {
            "timestamp": datetime.now().isoformat()
        }
    })

    return parsed_arguments or {}
