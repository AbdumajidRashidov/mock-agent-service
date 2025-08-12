import json
import logging
from typing import Optional
import html2md
from ...utils.azure import azure_openai_chat_service
from ...utils.extract_reply_content import extract_reply_content
from .prompt import INFO_REQUEST_EMAIL_GENERATOR_SYSTEM_PROMPT, NEGOTIATION_EMAIL_GENERATOR_SYSTEM_PROMPT
from .types import EmailGeneratorParams
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def email_generator_plugin(params: EmailGeneratorParams, response_callback: callable) -> Optional[str]:
    """Generate a reply email based on conversation history and parameters.

    Args:
        params (EmailGeneratorParams): Parameters for email generation including conversation history

    Returns:
        Optional[str]: Generated email body or None if generation fails
    """
    user_content = json.dumps({
        **({"missing_info": params["missing_info"]} if params.get("missing_info") else {}),
        **({"questions_asked_by_broker_in_received_email_and_answers_to_include_generating_email": params["questions_and_answers"]}
           if params.get("questions_and_answers") else {}),
        "emails": [{
            "subject": email["subject"],
            "body": html2md.convert(extract_reply_content(email["body"])),
            "from": "user (dispatcher)" if email["from"][0]["email"] in params["our_emails"] else "broker"
        } for email in params["emails"]],
        **({"rate_we_ask_if_broker_can_offer": params["offering_rate"]} if params.get("offering_rate") else {})
    })

    response_callback({
        "message": "Generating reply email...",
        "metadata": {"timestamp": datetime.now().isoformat(), "messages": [
            {
                'role': 'system',
                'content': NEGOTIATION_EMAIL_GENERATOR_SYSTEM_PROMPT if params.get("offering_rate") else INFO_REQUEST_EMAIL_GENERATOR_SYSTEM_PROMPT
            },
            {
                'role': 'user',
                'content': user_content
            }
        ]}
    })

    response = await azure_openai_chat_service.complete({
        'messages': [
            {
                'role': 'system',
                'content': NEGOTIATION_EMAIL_GENERATOR_SYSTEM_PROMPT if params.get("offering_rate") else INFO_REQUEST_EMAIL_GENERATOR_SYSTEM_PROMPT
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
                    'name': 'generateEmail',
                    'description': 'Generate a reply email',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'emailBody': {
                                'type': 'string',
                                'description': 'Generated email body'
                            }
                        },
                        'required': ['emailBody']
                    }
                }
            }
        ]
    })

    tool = response.get('choices', [{}])[0].get('message', {}).get('tool_calls', [None])[0]

    if not tool:
        logger.warning("WARNING::emailGenerator:: No tool call found", json.dumps(response, indent=2))
        return None

    try:
        parsed_arguments = json.loads(tool['function']['arguments'])
    except (KeyError, json.JSONDecodeError):
        logger.warning("WARNING::emailGenerator:: Failed to parse tool arguments")
        return None

    if not parsed_arguments.get('emailBody'):
        logger.warning("WARNING::emailGenerator:: No email body found", json.dumps(parsed_arguments, indent=2))
        return None

    email_body = parsed_arguments['emailBody']

    # Create the plugin response
    plugin_response = {
        "plugin_name": "email_generator",
        "response": response,
        "extracted_data": email_body,
    }

    await response_callback({
        "plugin_response": plugin_response,
        "metadata": {
            "timestamp": datetime.now().isoformat()
        }
    })

    return email_body
