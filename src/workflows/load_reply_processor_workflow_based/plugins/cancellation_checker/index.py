import logging
from typing import Optional, Callable
import json
from ...utils.azure import azure_openai_chat_service
from .prompt import CANCELLATION_CHECKER_SYSTEM_PROMPT
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def cancellation_checker_plugin(email_content: str, response_callback: Optional[Callable] = None) -> Optional[bool]:
    """Check if a broker's email indicates load cancellation.

    Args:
        email_content (str): The content of the broker's reply email
        response_callback (Optional[Callable]): Callback function to handle streaming responses

    Returns:
        Optional[bool]: True if load is cancelled, False if not, None if unable to determine
    """
    response = await azure_openai_chat_service.complete({
        'messages': [
            {
                'role': 'system',
                'content': CANCELLATION_CHECKER_SYSTEM_PROMPT
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
                    'name': 'setCancelledStatus',
                    'description': 'Set the cancelled status of the load',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'cancelled': {
                                'type': 'boolean',
                                'description': 'Cancelled status of the load'
                            }
                        },
                        'required': ['cancelled']
                    }
                }
            }
        ]
    })

    tool = response.get('choices', [{}])[0].get('message', {}).get('tool_calls', [None])[0]

    if not tool:
        logger.warning("WARNING::cancellationChecker:: No tool call found", json.dumps(response, indent=2))
        return None

    try:
        parsed_arguments = json.loads(tool['function']['arguments'])
    except (KeyError, json.JSONDecodeError):
        logger.warn("WARNING::cancellationChecker:: Failed to parse tool arguments")
        return None

    is_cancelled = bool(parsed_arguments.get('isCancelled', False))

    # Create the plugin response
    plugin_response = {
        "plugin_name": "cancellation_checker",
        "response": response,
        "extracted_data": is_cancelled,
    }

    await response_callback({
        "plugin_response": plugin_response,
        "metadata": {
            "timestamp": datetime.now().isoformat()
        }
    })

    return is_cancelled
