import logging
from workflows.load_reply_processsor.setup import azure_client

# Message type constants matching the TypeScript frontend
CHAT_MESSAGE_TYPE = {
    "USER": "user",
    "AGENT_THINKING": "agent-thinking",
    "AGENT_TOOL_CALL": "agent-tool-call",
    "AGENT_TOOL_RESULT": "agent-tool-result",
    "AGENT_RESPONSE": "agent-response",
    "SYSTEM": "system"
}

# Setup logging
logger = logging.getLogger(__name__)

# Dispatcher assistant definition
DISPATCHER_INSTRUCTIONS = """
You are an AI Dispatcher for a logistics company specializing in freight transport and negotiation.
Your role is to interact with brokers to negotiate rates and terms for transporting loads.

Key responsibilities:
1. Greet brokers professionally and gather essential load details (origin, destination, weight, equipment type, etc.)
2. Negotiate rates professionally, starting slightly higher than your minimum acceptable rate
3. Be firm but reasonable in negotiations
4. Build relationships with brokers through professional communication
5. Communicate clearly about expectations, timing, and requirements

When greeting a broker for the first time:
- Introduce yourself as the dispatcher for Numeo Logistics
- Ask for complete load details if not provided
- Explain that you'll work to secure the best rate possible
- Aim for a 10-20% markup from your minimum target, leaving room for negotiation

NEVER agree to rates below your minimum threshold without further authorization.
Prioritize clarity and professionalism in all communications.

Your goal is to secure profitable loads while maintaining good broker relationships.
"""

from agents import Agent, OpenAIChatCompletionsModel, Runner

# Optionally cache agents by negotiation_id if you want unique state/instructions per negotiation
agents_cache = {}

def get_or_create_dispatcher_agent(negotiation_id):
    if negotiation_id in agents_cache:
        return agents_cache[negotiation_id]
    agent = Agent(
        model=OpenAIChatCompletionsModel(
            model='gpt-4o-mini',
            openai_client=azure_client
        ),
        name=f"Dispatcher-{negotiation_id}",
        instructions=DISPATCHER_INSTRUCTIONS
    )
    agents_cache[negotiation_id] = agent
    return agent

async def test_agent(initiation_data: dict):
    """
    Handle negotiation requests using OpenAI Agents SDK (not Assistants API)
    Args:
        initiation_data: Dictionary containing context about the negotiation
            - negotiation_id: Unique identifier for this negotiation session
            - application_name: Name of the calling application
            - load_id: ID of the load being negotiated (if available)
            - user_id: ID of the user/broker
            - content: Message content (for message actions)
    """
    negotiation_id = initiation_data.get('negotiation_id', 'unknown')
    content = initiation_data.get('content', '')
    load_id = initiation_data.get('load_id', 'unknown')
    application_name = initiation_data.get('application_name', '')
    user_id = initiation_data.get('user_id', '')

    agent = get_or_create_dispatcher_agent(negotiation_id)

    if not content:
        prompt = (
            f"You are a Dispatcher. Initiate a negotiation session.\n"
            f"Negotiation ID: {negotiation_id} | "
            f"Application: {application_name} | "
            f"Load ID: {load_id} | "
            f"User ID: {user_id}\n"
            "Greet the broker, ask for load details if not provided, and explain you will try to get the best rate."
        )
    else:
        prompt = content

    # Collect structured events for streaming
    events = []
    # Only emit canonical message types as per agentic-communication.ts
    events.append({
        "type": CHAT_MESSAGE_TYPE["AGENT_THINKING"],
        "content": "Thinking...",
        "timestamp": "2025-04-28T03:12:41.156Z"
    })
    result = await Runner.run(agent, input=prompt)
    events.append({
        "type": CHAT_MESSAGE_TYPE["AGENT_RESPONSE"],
        "content": result.final_output,
        "timestamp": "2025-04-28T03:12:41.160Z"
    })
    return events


# Code within the code,
# Functions calling themselves,
# Infinite loop's dance.
