import logging
from typing import List, Optional, Any
import json
import html2md
from ...utils.azure import azure_openai_chat_service
from ...utils.extract_reply_content import extract_reply_content
from .prompt import NEGOTIATION_STATUS_CHECKER_SYSTEM_PROMPT
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def negotiation_status_checker_plugin(emails: List[dict], our_emails: List[str], response_callback: callable) -> Optional[bool]:
    """Check if the broker approved our rate in the latest email.

    Args:
        emails (List[Dict]): List of email objects containing conversation history
        our_emails (List[str]): List of our email addresses to identify sender

    Returns:
        Optional[bool]: True if rate is approved, False if not, None if unable to determine
    """
    formatted_emails = [{
        "subject": email["subject"],
        "body": html2md.convert(extract_reply_content(email["body"])),
        "from": "user (dispatcher)" if email["from"][0]["email"] in our_emails else "broker"
    } for email in emails]

    response = await azure_openai_chat_service.complete({
        'messages': [
            {
                'role': 'system',
                'content': NEGOTIATION_STATUS_CHECKER_SYSTEM_PROMPT
            },
            {
                'role': 'user',
                'content': f'Emails: {json.dumps(formatted_emails)}'
            }
        ],
        'tools': [
            {
                'type': 'function',
                'function': {
                    'name': 'setIsApproved',
                    'description': 'Set the negotiation status of the load',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'isApproved': {
                                'type': 'boolean',
                                'description': 'Is the broker approved the rate we asked?'
                            }
                        },
                        'required': ['isApproved']
                    }
                }
            }
        ]
    })

    tool = response.get('choices', [{}])[0].get('message', {}).get('tool_calls', [None])[0]

    if not tool:
        logger.warning("WARNING::negotiationStatusChecker:: No tool call found", json.dumps(response, indent=2))
        return None

    try:
        parsed_arguments = json.loads(tool['function']['arguments'])
    except (KeyError, json.JSONDecodeError):
        logger.warning("WARNING::negotiationStatusChecker:: Failed to parse tool arguments")
        return None

    is_approved = bool(parsed_arguments.get('isApproved', False))

    # Create the plugin response
    plugin_response = {
        "plugin_name": "negotiation_status_checker",
        "response": response,
        "extracted_data": is_approved,
    }

    await response_callback({
        "plugin_response": plugin_response,
        "metadata": {
            "timestamp": datetime.now().isoformat()
        }
    })

    return is_approved
