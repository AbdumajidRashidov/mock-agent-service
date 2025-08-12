import datetime

from agents import Agent, RunContextWrapper
from workflows.load_reply_processsor.models import OrchestratorContext


def extractor_dynamic_instructions(
    ctx: RunContextWrapper[OrchestratorContext],
    agent: Agent[OrchestratorContext],
) -> str:

    load = ctx.context.load_context

    known_information = f"""
        - pickup location: {load.origin.city}, {load.origin.state_prov}
        - delivery location: {load.destination.city}, {load.destination.state_prov}
        - equipment: {load.equipment_type}
        - weight: {load.shipment_details.maximum_weight_pounds}
        - offering rate: {load.rate_info.rate_usd or None}
        - additional comments: {load.comments or None}
        """

    prompt = f"""
        ### Role
        You are the **Load Details Extractor** in a virtual dispatcher workflow for a trucking company.

        ### Inputs
        1. Known load details (may be null or partially filled), summarized as:
        {known_information}

        2. The full conversation with the broker (not shown here but available in context).

        ### Your Task
        Extract and merge the following load details from the conversation and the known details:
        - offering_rate (number)
        - equipment (string)
        - weight (number)
        - commodity (string)

        ### Important Instructions
        - Only consider the most recent message for extracting new information.
        - If the most recent message mentions a field, use that value to update the known details.
        - If a field is not mentioned in the most recent message, keep the known value.
        - If the most recent message contradicts known information, prioritize the latest message.
        - After updating, if any of these fields are still missing (null or empty), list them explicitly in a "missing" array.

        ### Output Format
        You must call the tool **update_details** exactly once per turn with a JSON object matching this schema (keys in this exact order):

        {{
        "commodity": string | null,
        "equipment": string | null,
        "offering_rate": number | null,
        "weight": number | null,
        "missing": [string]
        }}

        ### Additional Context
        - Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}

        ### REMEMBER
        Your output must ONLY concern the specified fields above.
        Do NOT add, infer, or mention any other information.
    """
    return prompt
