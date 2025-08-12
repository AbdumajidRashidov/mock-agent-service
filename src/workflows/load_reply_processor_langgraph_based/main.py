import asyncio
import logging
from typing import Dict, Any, List, Callable
from .graph_builder import create_workflow
from datetime import datetime
from .utils.convert_emails_to_messages import map_email_to_message
import uuid
import os

LANGSMITH_ACCOUNT_ID = os.getenv('LANGSMITH_ACCOUNT_ID') or "f7787b69-0d06-4b60-970a-78668c58220c"
LANGSMITH_PROJECT_ID = os.getenv('LANGSMITH_PROJECT_ID') or "0aa01f45-930e-4c6f-838e-04a79e0315ef"

LANGSMITH_TRACER_DASHBOARD_URL = f"https://smith.langchain.com/o/{LANGSMITH_ACCOUNT_ID}/projects/p/{LANGSMITH_PROJECT_ID}"

async def process_reply(
    company_details: Dict[str, Any],
    our_emails: List[str],
    truck: Dict[str, Any],
    load: Dict[str, Any],
    emails: List[Dict[str, Any]],
) -> None:
    """
    Process email replies and generate appropriate responses using the graph workflow.

    Args:
        company_details: Dictionary containing company information
        our_emails: List of email addresses that belong to us
        truck: Dictionary containing truck information
        load: Dictionary containing load information
        emails: List of email dictionaries in the thread
    """
    try:
        # Process emails to create message history (all except the last one)
        if not emails:
            messages = []
            last_email = {}
        else:
            messages = [map_email_to_message(email, our_emails) for email in emails[:-1]]
            last_email = emails[-1]

        await asyncio.sleep(10) # 10 seconds delay

        graph = create_workflow()

        # Prepare the input for the graph
        graph_input = {
            "email_generator_agent_messages": messages,
            "company_info": company_details,
            "truck_info": truck,
            "load_info": load,
            "reply": last_email.get('body', '') if last_email else "",

            # These will be filled by the workflow
            "updated_load_fields": {},
            "generate_email_attempts": 0
        }

        config = {"run_id": uuid.uuid4()}
        logging.info(f"[STARTED] Processing load reply: Subject: {last_email.get('subject', '')} Trace: {LANGSMITH_TRACER_DASHBOARD_URL}?peek={config['run_id']}")

        # Get both response and run metadata from graph invocation
        response = await graph.ainvoke(graph_input, config)
        logging.error(f"[COMPLETED] Processing load reply: Subject: {last_email.get('subject', '')} Trace: {LANGSMITH_TRACER_DASHBOARD_URL}?peek={config['run_id']}")

        return {
            "email_to_send": response.get("email_to_send", ""),
            "field_updates": response.get("updated_load_fields", {}),
            "trace_id": str(config["run_id"]),
            "metadata": {
                "timestamp": datetime.now().isoformat(),
            }
        }
    except Exception as e:
        logging.error(f"[ERROR] Processing load reply: Subject: {last_email.get('subject', '')} Error: {str(e)} Trace: {LANGSMITH_TRACER_DASHBOARD_URL}?peek={config['run_id']}", exc_info=True)
        raise Exception(f"Error processing load reply: {str(e)}")
