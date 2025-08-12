import logging
import os
import time
import requests
import json
from agents import RunContextWrapper
from db.utils import save_message

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

from workflows.load_reply_processsor.models import OrchestratorContext


async def send_reply(ctx: RunContextWrapper[OrchestratorContext], body: str) -> str:
    """
    Send a reply email through the API endpoint.

    Args:
        body: Email body content
        subject: Email subject
        thread_id: ID of the email thread
        email_id: ID of the email to reply to
        project_name: Name of the project

    Returns:
        Dict containing the API response with success status, status code, and data
    """

    message = json.loads(body).get("message", "")



    # Extract context values
    subject = ctx.context.subject
    thread_id = ctx.context.thread_id
    email_id = ctx.context.email_id
    project_name = ctx.context.application_name

    email_body= message

    try:
        # Get the API base URL from environment variables
        api_base_url = os.getenv("NUMEO_API_URL", "https://dev-api.numeo.ai")

        # Construct the URL with query parameters if provided
        url = f"{api_base_url}/v1/n8n/send-reply/{email_id}"

        # Prepare the request payload
        payload = {
            "subject": subject,
            "body": email_body,
            "threadId": thread_id,
            "projectName": project_name,
        }


        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses

        logger.info(f"Reply email sent successfully to {email_id}")

        # Save the reply message to postgres
        save_message(load_id=ctx.context.load_id, thread_id=thread_id, role="assistant", content=email_body)

        # Return a success message as a string
        return f"Reply sent successfully to {email_id}"

    except requests.exceptions.RequestException as e:
        # Log error details
        logger.error(
            f"Error sending reply email to {email_id}",
            exc_info=True
        )


        error_text = (
            getattr(e.response, "text", "Failed to send reply email")
            if hasattr(e, "response")
            else "Failed to send reply email"
        )

        return f"Error sending reply to {email_id}: {error_text}"
    except Exception as e:

        # Log error details
        logger.error(
            f"Unexpected error in reply_to_broker for thread_id: {thread_id}",
            exc_info=True,
        )

        return f"An unexpected error occurred while sending the reply to {email_id}: {str(e)}"
