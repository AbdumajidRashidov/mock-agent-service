import logging
from typing import Optional
import json
from ...utils.azure import azure_openai_chat_service
from .const import EmailType, EMAIL_TYPES
from .prompt import REPLY_EMAIL_TYPE_CHECKER_SYSTEM_PROMPT
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reply_email_type_checker_plugin(reply_email: str, response_callback: callable) -> Optional[EmailType]:
    """Check the type of email received from broker.

    Args:
        reply_email (str): Content of the broker's reply email

    Returns:
        Optional[EmailType]: Type of the email or None if unable to determine
    """
    response = await azure_openai_chat_service.complete({
        'messages': [
            {
                'role': 'system',
                'content': REPLY_EMAIL_TYPE_CHECKER_SYSTEM_PROMPT
            },
            {
                'role': 'user',
                'content': reply_email
            }
        ],
        'tools': [
            {
                'type': 'function',
                'function': {
                    'name': 'setEmailType',
                    'description': 'Set the type of the email',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'emailType': {
                                'type': 'string',
                                'description': 'Type of the email',
                                'enum': [e.value for e in EMAIL_TYPES]
                            }
                        },
                        'required': ['emailType']
                    }
                }
            }
        ]
    })

    tool = response.get('choices', [{}])[0].get('message', {}).get('tool_calls', [None])[0]

    if not tool:
        logger.warning("WARNING::replyEmailTypeChecker:: No tool call found", json.dumps(response, indent=2))
        return None

    try:
        parsed_arguments = json.loads(tool['function']['arguments'])
    except (KeyError, json.JSONDecodeError):
        logger.warning("WARNING::replyEmailTypeChecker:: Failed to parse tool arguments")
        return None

    if not parsed_arguments.get('emailType'):
        logger.warning("WARNING::replyEmailTypeChecker:: No email type found", json.dumps(parsed_arguments, indent=2))
        return None

    email_type = EmailType(parsed_arguments['emailType'])

    # Create the plugin response
    plugin_response = {
        "plugin_name": "reply_email_type_checker",
        "response": response,
        "extracted_data": email_type.value,
    }

    await response_callback({
        "plugin_response": plugin_response,
        "metadata": {
            "timestamp": datetime.now().isoformat()
        }
    })

    return email_type
