# This file is a copy of orchestrator_v2.py

from ast import arguments
import os
from agents import (
    Agent,
    FunctionTool,
    GuardrailFunctionOutput,
    OpenAIChatCompletionsModel,
    Runner,
    TResponseInputItem,
    input_guardrail,
    set_tracing_disabled,
    RunContextWrapper,
)
import logfire
from typing import Optional
from workflows.load_reply_processsor.models import (
    AnalyzerAgentOutput,
    CommunicatorContext,
    EmailSendingClass,
    OrchestratorContext,
    UpdateDetailsPayload,
)
from workflows.load_reply_processsor.utils.load_warnings import upsert_load_warnings
from workflows.load_reply_processsor.utils.load_reply_status import (
    update_load_reply_status,
)
from workflows.load_reply_processsor.tools.cancell_load import cancel_load
from workflows.load_reply_processsor.tools.reply_to_broker import send_reply
from workflows.load_reply_processsor.setup import azure_client
from workflows.load_reply_processsor.models import WarningsReq, AgentsReq
from workflows.load_reply_processsor.utils.split_email import split_email
from workflows.load_reply_processsor.instructions.version2.instructions import (
    dynamic_question_answering_agent_instructions,
)
from workflows.load_reply_processsor.instructions.rate_negotiator import (
    dynamic_negotiation_agent_instructions,
)
from db.utils import save_message, format_conversation_for_llm, get_conversation_history


from workflows.load_reply_processsor.instructions.guardian import (
    dynamic_compliance_checker_instructions,
)
from workflows.load_reply_processsor.instructions.extractor import (
    extractor_dynamic_instructions,
)
from workflows.load_reply_processsor.instructions.manager import MANAGER_INSTRUCTIONS
from workflows.load_reply_processsor.instructions.communicator import (
    communicator_instructions,
)

logfire.configure()
logfire.instrument_openai()
logfire.instrument_openai_agents()

set_tracing_disabled(True)


# Models
from pydantic import BaseModel, Field


class MessagePayload(BaseModel):
    message: str


# Agents
warnings_analyzer = Agent[OrchestratorContext](
    name="Warnings Analyzer Agent",
    instructions=dynamic_compliance_checker_instructions,
    model=OpenAIChatCompletionsModel(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        openai_client=azure_client,
    ),
    tools=[
        FunctionTool(
            name="update_warnings",
            on_invoke_tool=upsert_load_warnings,
            description="This tool will send the load warnings to the external load processing service",
            params_json_schema=WarningsReq.model_json_schema(),
        ),
    ],
    output_type=list[str],
)

# Extractor Agent
extractor = Agent[OrchestratorContext](
    name="Extractor Agent",
    instructions=extractor_dynamic_instructions,
    model=OpenAIChatCompletionsModel(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        openai_client=azure_client,
    ),
    tools=[
        FunctionTool(
            name="update_details",
            on_invoke_tool=update_load_reply_status,
            description="This tool will send ALL load details to the external load processing service. Call this tool only ONCE with all the details combined.",
            params_json_schema=UpdateDetailsPayload.model_json_schema(),
        ),
    ],
    output_type=UpdateDetailsPayload,
)

# Question Answer Agent
question_answer = Agent[OrchestratorContext](
    name="Question Answer Agent",
    instructions=dynamic_question_answering_agent_instructions,
    model=OpenAIChatCompletionsModel(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        openai_client=azure_client,
    ),
)


@input_guardrail
async def negotiator_guardrail(
    ctx: RunContextWrapper[OrchestratorContext],
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    context = ctx.context
    load_context = context.load_context
    rate_info = load_context.rate_info

    print("Rate info:", rate_info)

    # Precondition checks
    has_offered_rate = rate_info and rate_info.rate_usd is not None
    has_min_max = (
        rate_info
        and rate_info.minimum_rate is not None
        and rate_info.maximum_rate is not None
    )
    no_warnings = not load_context.warnings or len(load_context.warnings) == 0

    can_negotiate = all(
        [
            has_offered_rate,
            has_min_max,
            no_warnings,
        ]
    )

    print("Negotiation guardrail evaluation...AFK 10 min")

    logfire.debug(
        "Negotiation guardrail evaluation",
        evaluation_result={
            "broker_rate_provided": has_offered_rate,
            "rate_bounds_defined": has_min_max,
            "warnings_present": not no_warnings,
            "final_decision": can_negotiate,
        },
    )

    return GuardrailFunctionOutput(
        output_info=can_negotiate,
        tripwire_triggered=not can_negotiate,
    )


rate_negotiator = Agent[OrchestratorContext](
    name="Rate Negotiator Agent",
    instructions=dynamic_negotiation_agent_instructions,
    model=OpenAIChatCompletionsModel(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"), openai_client=azure_client
    ),
    input_guardrails=[negotiator_guardrail],
)

# Define the agents
# should orchestrator between agents
analyzer = Agent[OrchestratorContext](
    name="Manager Agent",
    instructions=MANAGER_INSTRUCTIONS,
    model=OpenAIChatCompletionsModel(model="gpt-4o", openai_client=azure_client),
    tools=[
        extractor.as_tool(
            tool_name="extract_details",
            tool_description="Extract all load details from the conversation history, identify missing critical information, and structure the data for analysis.",
        ),
        warnings_analyzer.as_tool(
            tool_name="analyze_warnings",
            tool_description="This tool will analyze the load warnings",
        ),
        question_answer.as_tool(
            tool_name="answer_question",
            tool_description="This tool will find the answer to the user's question using the provided load details and company information",
        ),
        rate_negotiator.as_tool(
            tool_name="negotiate_rate",
            tool_description="This tool will get the rate",
        ),
        FunctionTool(
            name="cancel_load",
            on_invoke_tool=cancel_load,
            description="This tool will cancel the load",
            params_json_schema=AgentsReq.model_json_schema(),
        ),
    ],
    output_type=AnalyzerAgentOutput,
)


communicator = Agent[OrchestratorContext](
    name="Communicator Agent",
    instructions=communicator_instructions,
    model=OpenAIChatCompletionsModel(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        openai_client=azure_client,
    ),
    tools=[
        FunctionTool(
            name="send_email",
            on_invoke_tool=send_reply,
            description="This tool will send the email to the broker",
            params_json_schema=EmailSendingClass.model_json_schema(),
        ),
        FunctionTool(
            name="cancel_load",
            on_invoke_tool=cancel_load,
            description="This tool will cancel the load",
            params_json_schema=AgentsReq.model_json_schema(),
        ),
    ],
    output_type=EmailSendingClass,
)


# Map conversation roles to standard roles for the agent system
def map_conversation_roles(conversation):
    role_mapping = {"system": "system", "user": "user", "assistant": "assistant"}

    mapped_conversation = []
    for message in conversation:
        if "role" in message and "content" in message:
            role = message["role"]
            # Map to standard role or default to 'user'
            standard_role = role_mapping.get(role, "user")
            mapped_conversation.append(
                {"role": standard_role, "content": message["content"]}
            )

    return mapped_conversation


# Define main function to process broker emails
async def process_broker_email(request) -> str:
    # Log the incoming request

    # Email content related fields
    reply_email = getattr(request, "reply_email", None)
    email_content = getattr(reply_email, "body", "") if reply_email else ""
    subject = getattr(reply_email, "subject", "") if reply_email else ""

    # Thread and email identification
    thread_id = getattr(request, "thread_id", None)
    email_id = getattr(request, "email_id", None)

    # Load related fields
    load = getattr(request, "load", None)
    load_id = getattr(request, "load_id", None)

    # Truck related fields
    truck = getattr(request, "truck", None)

    # Company and application details
    company_info = getattr(request, "company_details", None)
    application_name = getattr(request, "application_name", None)

    # Split the email content into reply and original parts
    email_parts = split_email(email_content)
    reply_content = email_parts["reply"]
    origin_content = email_parts["original"]

    logfire.info(
        "Received load reply request",
        **{
            "reply_content": reply_content,
            "origin_content": origin_content,
            "thread_id": thread_id,
            "email_id": email_id,
            "load_id": load_id,
            "subject": subject,
            "company_info": company_info,
            "application_name": application_name,
            "truck": truck,
            "load": load,
        },
    )

    # Get conversation history from the database
    conversation_history = []
    try:
        # Get the load ID from the load details if available
        load_id = load_id or (getattr(load, "id", None) if load else None)

        # Set a default limit for conversation history
        limit = 100

        # Retrieve conversation history from the database
        messages_from_db = get_conversation_history(
            load_id=load_id, thread_id=thread_id, limit=limit
        )

        conversation_history = format_conversation_for_llm(messages_from_db)

        # Log the number of messages retrieved
        logfire.info(
            f"Retrieved {len(conversation_history)} messages from conversation history"
        )
    except Exception as e:
        # Log the error and return an empty list if there's an issue
        logfire.error(f"Error retrieving conversation history: {e}")
        conversation_history = []

    if len(conversation_history) == 0:
        save_message(
            load_id=load_id,
            thread_id=thread_id,
            role="assistant",
            content=origin_content,
        )

        conversation_history.append({"role": "assistant", "content": origin_content})

    save_message(
        load_id=load_id, thread_id=thread_id, role="user", content=reply_content
    )

    conversation_history.append({"role": "user", "content": reply_content})

    # Map conversation roles before using them
    mapped_conversation = map_conversation_roles(conversation_history)

    context = OrchestratorContext(
        # Core entities
        load_context=load,
        company_info=company_info,
        truck_context=truck,
        # Identifiers
        thread_id=thread_id,
        email_id=email_id,
        load_id=load_id,
        subject=subject,
        # Metadata
        application_name=application_name,
        # Conversation state
        conversation_history=conversation_history,  # Use the retrieved conversation history
    )

    result = await Runner.run(
        starting_agent=analyzer,
        input=mapped_conversation,
        context=context,
        max_turns=20,
    )

    print("Result:", result.final_output)

    return result.final_output
