import logging
import os
from agents import RunContextWrapper
import requests
from typing import List, Dict, Union, Any
from workflows.load_reply_processsor.models import OrchestratorContext

logger = logging.getLogger(__name__)


def upsert_load_warnings(
    ctx: RunContextWrapper[OrchestratorContext],
    warnings: Union[List[str], Dict[str, Any]],
):
    application_name = ctx.context.application_name

    try:
        # Record warnings operation
        logger.debug(f"Recording warnings operation for load_id: {ctx.context.load_id}")

        # Prepare API request

        api_base_url = os.getenv("NUMEO_API_URL", "https://dev-api.numeo.ai")
        url = f"{api_base_url}/v1/trucks/loads/{ctx.context.load_id}/warnings"

        # Handle different types of warnings input
        warnings_list = []
        if isinstance(warnings, dict):
            # If warnings is a dictionary with a "warnings" key
            if "warnings" in warnings and isinstance(warnings["warnings"], list):
                warnings_list = warnings["warnings"]
            # If warnings is a dictionary with other keys
            else:
                for key, value in warnings.items():
                    if isinstance(value, list):
                        warnings_list.extend(value)
                    else:
                        warnings_list.append(str(value))
        else:
            # If warnings is already a list
            warnings_list = warnings

        payload = {
            "applicationName": application_name,
            "warnings": warnings_list,  # Use the processed list
        }

        # Make the API request
        logger.debug(f"Sending warnings to API for load_id: {ctx.context.load_id}")
        response = requests.put(url, json=payload)

        # Parse response data
        response_data = response.json() if response.content else None

        logger.info(
            f"Warnings operation completed successfully for load_id: {ctx.context.load_id}"
        )

        return {
            "success": True,
            "status_code": response.status_code,
            "data": response_data,
            "message": "Warnings successfully sent",
        }

    except requests.exceptions.RequestException as e:
        # Handle request errors
        error_message = str(e)
        status_code = (
            e.response.status_code if hasattr(e, "response") and e.response else None
        )

        # Log error details
        logger.error(
            f"Error sending warnings for load_id: {ctx.context.load_id}", exc_info=True
        )

        return {
            "success": False,
            "status_code": status_code,
            "error": error_message,
            "message": "Failed to send warning notification",
        }

    except Exception as e:
        # Handle other errors
        error_message = str(e)

        # Log error details
        logger.error(
            f"Unexpected error in load_warnings for load_id: {ctx.context.load_id}",
            exc_info=True,
        )

        return {
            "success": False,
            "error": error_message,
            "message": "An unexpected error occurred while sending warning notification",
        }
