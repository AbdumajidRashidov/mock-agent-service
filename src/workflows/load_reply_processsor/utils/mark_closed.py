import logging
import os
from agents import RunContextWrapper
import requests
from typing import Any, Dict
from src.db.utils import save_message

logger = logging.getLogger(__name__)

async def mark_closed(ctx: RunContextWrapper[Any], draft: Dict[str, Any]):
    """
    Mark the load as closed through the API endpoint.

    Returns:
        Dict containing the API response with success status, status code, and data
    """

    project_name: str = ctx.context["project_name"]
    load_id: str = ctx.context["load_id"]
    email_body: str = draft
    email_subject: str = ctx.context["email_subject"]
    thread_id: str = ctx.context["thread_id"]

    logger.debug(f"Starting draft send operation for thread_id: {thread_id}, load_id: {load_id}")

    try:
        # API base URL
        # TODO: NEED TO IMPLEMENT IN MAIN SERVICE
        api_base_url = os.getenv("NUMEO_API_URL", "https://dev-api.numeo.ai")
        url = f"{api_base_url}/v1/trucks/loads/{load_id}/mark-closed"

        payload = {
            "projectName": project_name,
            "to": "yow1da01@gmail.com",
            "subject": email_subject,
            "body": email_body,
            "threadId": thread_id,
            "draft": draft
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('NUMEO_API_KEY')}"
        }

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        save_message("assistant", email_body, thread_id=thread_id, load_id=load_id)
        logger.info(f"Marked load as closed successfully for load_id: {load_id}")

        return {
            "success": True,
            "status_code": response.status_code,
            "data": response.json() if response.content else None,
            "message": "Marked load as closed successfully",
        }

    except requests.exceptions.RequestException as e:
        error_message = str(e)
        status_code = e.response.status_code if hasattr(e, "response") and e.response else None

        logger.error(
            f"RequestException while sending draft - error: {error_message}, thread_id: {thread_id}, load_id: {load_id}, status_code: {status_code}",
            exc_info=True
        )
        return {
            "success": False,
            "status_code": status_code,
            "error": error_message,
            "message": "Failed to mark load as closed",
        }
    except Exception as e:
        error_message = str(e)
        error_type = type(e).__name__

        logger.error(
            f"Unhandled error in mark_closed - error: {error_message}, thread_id: {thread_id}, load_id: {load_id}, error_type: {error_type}",
            exc_info=True
        )
        return {
            "success": False,
            "error": error_message,
            "message": "An unexpected error occurred while marking load as closed",
        }
