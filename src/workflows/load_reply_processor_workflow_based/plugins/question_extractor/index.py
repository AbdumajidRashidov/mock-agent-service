import logging
from typing import List
import json
from ...utils.azure import azure_openai_chat_service
from .prompt import QUESTIONS_EXTRACTOR_SYSTEM_PROMPT
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def questions_extractor_plugin(reply_email: str, response_callback: callable) -> List[str]:
    """Extract questions from a broker's email.

    Args:
        reply_email (str): Content of the broker's reply email

    Returns:
        List[str]: List of extracted questions, empty list if none found
    """
    response = await azure_openai_chat_service.complete({
        'messages': [
            {
                'role': 'system',
                'content': QUESTIONS_EXTRACTOR_SYSTEM_PROMPT
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
                    'name': 'setQuestions',
                    'description': 'Set the asked questions in email',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'questions': {
                                'type': 'array',
                                'items': {
                                    'type': 'string'
                                },
                                'description': 'Questions asked in the email'
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
        logger.warning("WARNING::questionExtractor:: No tool call found", json.dumps(response, indent=2))
        return []

    try:
        parsed_arguments = json.loads(tool['function']['arguments'])
    except (KeyError, json.JSONDecodeError):
        logger.warning("WARNING::questionExtractor:: Failed to parse tool arguments")
        return []

    questions = parsed_arguments.get('questions', [])

    # Create the plugin response
    plugin_response = {
        "plugin_name": "questions_extractor",
        "response": response,
        "extracted_data": questions,
    }

    await response_callback({
        "plugin_response": plugin_response,
        "metadata": {
            "timestamp": datetime.now().isoformat()
        }
    })

    return questions
