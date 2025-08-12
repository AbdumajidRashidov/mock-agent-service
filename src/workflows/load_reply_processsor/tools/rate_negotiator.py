import logging
import os
from typing import Any

from src.workflows.load_reply_processsor.setup import azure_client

from agents import Agent, OpenAIChatCompletionsModel, FunctionTool
from src.workflows.load_reply_processsor.utils.draft_sender import send_draft
from src.workflows.load_reply_processsor.models import AgentsReq
from src.workflows.load_reply_processsor.instructions.rate_negotiator import get_rate_negotiator_instructions

logger = logging.getLogger(__name__)
openai_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")



rate_negotiator = Agent[Any](
        name="rate_negotiator",
        instructions=get_rate_negotiator_instructions,
        model=OpenAIChatCompletionsModel(model=openai_deployment_name, openai_client=azure_client),
        tools=[
            FunctionTool(
                name="create_draft",
                on_invoke_tool=send_draft,
                description="This tool will negotiate the rate with the broker.",
                params_json_schema=AgentsReq.model_json_schema()
            )
        ]
    )


