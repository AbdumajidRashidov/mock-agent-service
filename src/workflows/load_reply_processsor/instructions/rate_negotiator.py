from agents import Agent, RunContextWrapper
from workflows.load_reply_processsor.models import OrchestratorContext

def dynamic_negotiation_agent_instructions(
    context: RunContextWrapper[OrchestratorContext], agent: Agent[OrchestratorContext]
) -> str:

    load_context = context.context.load_context
    company_info = context.context.company_info

    # Get min/max acceptable rates from context
    MIN_ACCEPTABLE_RATE = load_context.rate_info.minimum_rate
    MAX_ACCEPTABLE_RATE = load_context.rate_info.maximum_rate

    # Get negotiation thresholds from company info
    first_bid_rate_threshold = company_info.rate_negotiation.first_bid_threshold / 100
    second_bid_rate_threshold = company_info.rate_negotiation.second_bid_threshold / 100
    rounding_value = company_info.rate_negotiation.rounding


    # First bid is between min and max, closer to max based on threshold
    first_bid_rate = MIN_ACCEPTABLE_RATE + (MAX_ACCEPTABLE_RATE - MIN_ACCEPTABLE_RATE) * first_bid_rate_threshold
    # Second bid is between min and max, closer to min based on threshold
    second_bid_rate = MIN_ACCEPTABLE_RATE + (MAX_ACCEPTABLE_RATE - MIN_ACCEPTABLE_RATE) * second_bid_rate_threshold

    # Round the bid rates to the nearest user-defined rounding value (e.g., $50 or $100)
    if rounding_value > 0:
        first_bid_rate = round(first_bid_rate / rounding_value) * rounding_value
        second_bid_rate = round(second_bid_rate / rounding_value) * rounding_value


    # Origin/destination formatting
    origin = f"{load_context.origin.city}, {load_context.origin.state_prov}"
    destination = f"{load_context.destination.city}, {load_context.destination.state_prov}"
    # Other load details
    weight = load_context.weight


    instructions = f"""
    ### Role ###
    You are an experienced logistics dispatcher negotiating freight rates with a broker.
    Your responsibility is to negotiate the rate of the load based on the provided details and negotiation strategy.

    ### Your negotiation parameters ###
    - Maximum acceptable rate: ${MAX_ACCEPTABLE_RATE}
    - Minimum acceptable rate: ${MIN_ACCEPTABLE_RATE} (never go below this)
    - First bid rate: {first_bid_rate} (fraction of difference for first counteroffer)
    - Second bid rate: {second_bid_rate} (fraction of difference for second counteroffer)

    ### Load details to support your negotiation ###
    - Route: {origin} to {destination}
    - Weight: {weight}
    - Equipment: {load_context.equipment_type}
"""


    instructions += f"""

        Negotiation strategy:
        1. Start by offering the max rate (${MAX_ACCEPTABLE_RATE}).
        2. If broker offer is below max rate, offer going down to the first bid rate and send email.
        3. If broker rejects first bid rate, offer going down to the second bid rate and send email.
        4. If broker rejects second bid rate, offer min_rate (${MIN_ACCEPTABLE_RATE}) as final and send email.
        5. Never offer below min_rate.

        Your task:
        - Find your next offer following the above rules.
        - Use real-case arguments referencing load details (commodity, route, weight, special requirements) to justify your offers.
        - If negotiation cannot proceed further (broker rejects min_rate), politely suggest escalation.

        Important:
        - Clearly state the proposed rate.
        - Do NOT mention the negotiation algorithm.
"""
    return instructions
