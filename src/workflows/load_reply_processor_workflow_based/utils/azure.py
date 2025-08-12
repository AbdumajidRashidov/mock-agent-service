import os
from typing import Dict, List, Optional, Union, TypedDict, Literal
import aiohttp
import json

OPENAI_API_URL = 'https://numeo-oai-rtv1.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview'

class ToolParameter(TypedDict):
    type: str
    description: str
    enum: Optional[List[str]]

class ToolFunction(TypedDict):
    name: str
    description: str
    parameters: Dict[str, ToolParameter]

class Tool(TypedDict):
    type: Literal['function']
    function: ToolFunction

class ToolCallFunction(TypedDict):
    name: str
    arguments: str  # JSON string of arguments

class ToolCall(TypedDict):
    id: str
    type: Literal['function']
    function: ToolCallFunction

class ChatMessage(TypedDict):
    role: Literal['system', 'user', 'assistant', 'tool']
    content: Optional[str]
    name: Optional[str]
    tool_calls: Optional[List[ToolCall]]
    tool_call_id: Optional[str]

class ToolChoice(TypedDict):
    type: Literal['function']
    function: Dict[str, str]

class ChatCompletionRequest(TypedDict):
    messages: List[ChatMessage]
    tools: Optional[List[Tool]]
    tool_choice: Optional[Union[Literal['auto', 'none'], ToolChoice]]
    temperature: Optional[float]
    max_tokens: Optional[int]
    model: Optional[str]
    stream: Optional[bool]
    n: Optional[int]
    presence_penalty: Optional[float]
    frequency_penalty: Optional[float]
    logit_bias: Optional[Dict[str, float]]
    user: Optional[str]
    stop: Optional[Union[str, List[str]]]

class LogProbContent(TypedDict):
    token: str
    logprob: float
    top_logprobs: List[Dict[str, float]]

class ChatChoice(TypedDict):
    index: int
    message: ChatMessage
    logprobs: Optional[Dict[str, List[LogProbContent]]]
    finish_reason: Literal['stop', 'length', 'tool_calls', 'content_filter']

class CompletionTokensDetails(TypedDict):
    reasoning_tokens: int
    accepted_prediction_tokens: int
    rejected_prediction_tokens: int

class Usage(TypedDict):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    completion_tokens_details: Optional[CompletionTokensDetails]

class ChatCompletionResponse(TypedDict):
    id: str
    object: Literal['chat.completion']
    created: int
    model: str
    system_fingerprint: Optional[str]
    choices: List[ChatChoice]
    usage: Usage

class AzureOpenAiChatService:
    async def complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OPENAI_API_URL,
                headers={
                    'Content-Type': 'application/json',
                    'api-key': os.environ['AZURE_OPENAI_API_KEY'],
                },
                json={
                    'messages': request['messages'],
                    'tools': request.get('tools'),
                    'tool_choice': request.get('tool_choice'),
                    'temperature': request.get('temperature', 0.9),
                    'max_tokens': request.get('max_tokens'),
                }
            ) as response:
                if not response.ok:
                    try:
                        error = await response.json()
                    except:
                        error = {}

                    raise ValueError(error.get('message') or f"HTTP error! status: {response.status}")

                return await response.json()

azure_openai_chat_service = AzureOpenAiChatService()
