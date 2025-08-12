import logging
from typing import Dict, List, Any, Optional
import json
from ...utils.azure import azure_openai_chat_service
from .prompt import ANSWER_GENERATOR_SYSTEM_PROMPT
from .types import QuestionAnswer
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def answer_generator_plugin(
    questions: List[str],
    company_details: Dict[str, Any],
    load_reference_id: Optional[str] = None,
    response_callback: callable = None,
) -> List[QuestionAnswer]:
    """Generate answers for broker questions using company details.

    Args:
        questions (List[str]): List of questions asked by the broker
        company_details (Dict[str, Any]): Company details to use for answers
        load_reference_id (Optional[str]): Reference ID for the load if available

    Returns:
        List[QuestionAnswer]: List of questions and their answers
    """
    user_content = f"""Questions: {chr(10).join(questions)}

Information to use to answer questions:
{f"Company name: {company_details.get('name', '')}" if company_details.get('name') else ""}
{f"Company address: {company_details.get('address', '')}" if company_details.get('address') else ""}
{f"Company phone: {company_details.get('phone', '')}" if company_details.get('phone') else ""}
{f"Company MC number: {company_details.get('mcNumber', '')}" if company_details.get('mcNumber') else ""}
{f"Company additional information: {company_details.get('details', '')}" if company_details.get('details') else ""}
Load ID: {load_reference_id or "(if broker explicity asks load id, answer: I see the load doesn't have any id, BECAUSE SOME LOADS MIGHT NOT HAVE LOAD ID)"}
"""

    response = await azure_openai_chat_service.complete({
        'messages': [
            {
                'role': 'system',
                'content': ANSWER_GENERATOR_SYSTEM_PROMPT
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
                    'name': 'setAnswers',
                    'description': 'Set the answer to the asked questions',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'questions_and_answers': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'question': {
                                            'type': 'string',
                                            'description': 'Question asked by broker'
                                        },
                                        'answer': {
                                            'type': 'string',
                                            'description': 'Answer to the question'
                                        },
                                        'couldNotAnswer': {
                                            'type': 'boolean',
                                            'description': 'Set to true if you cannot answer the question'
                                        }
                                    },
                                    'required': ['question']
                                },
                                'description': 'Questions asked in the email and generated answers'
                            }
                        },
                        'required': ['questions_and_answers']
                    }
                }
            }
        ]
    })

    tool = response.get('choices', [{}])[0].get('message', {}).get('tool_calls', [None])[0]

    if not tool:
        logger.warning("WARNING::answerGenerator:: No tool call found", json.dumps(response, indent=2))
        return []

    try:
        parsed_arguments = json.loads(tool['function']['arguments'])
    except (KeyError, json.JSONDecodeError):
        logger.warning("WARNING::answerGenerator:: Failed to parse tool arguments")
        return []

    if not parsed_arguments.get('questions_and_answers'):
        logger.warning("INFO::answerGenerator:: No questions and answers found", json.dumps(parsed_arguments, indent=2))
        return []

    qa_pairs = parsed_arguments['questions_and_answers']

    # Create the plugin response
    plugin_response = {
        "plugin_name": "answer_generator",
        "response": response,
        "extracted_data": qa_pairs,
    }

    await response_callback({
        "plugin_response": plugin_response,
        "metadata": {
            "timestamp": datetime.now().isoformat()
        }
    })

    return qa_pairs
