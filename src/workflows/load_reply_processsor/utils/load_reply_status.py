import logging
import os
import time
from agents import RunContextWrapper
import requests
from typing import Dict, Any, Union
import json
from opentelemetry import trace
from opentelemetry import metrics
from otel.metrics import (
    record_api_request,
    record_api_duration,
    record_api_error,
    record_operation_duration
)
from workflows.load_reply_processsor.models import OrchestratorContext

# Get tracer
tracer = trace.get_tracer("load-reply-status-tracer")
logger = logging.getLogger(__name__)

import json


# Import LoadDetailsOutput type if available, otherwise use type alias
from workflows.load_reply_processsor.models import UpdateDetailsPayload


async def update_load_reply_status(
    ctx: RunContextWrapper[OrchestratorContext],
    details: Union[UpdateDetailsPayload, Dict[str, Any], str] = None,
):
    """
    Update the load reply status by sending a request to the API endpoint.

    Args:
        load_id: ID of the load
        application_name: Name of the application
        details: Load details as LoadDetailsOutput object, dict, or string

    Returns:
        Dict containing the API response
    """
    # Start timing the operation
    start_time = time.monotonic()

    load_id = ctx.context.load_id
    application_name = ctx.context.application_name



    # Assuming the JSON is stored in a variable called json_string
    details = json.loads(details)

    # Create a span for the update_load_reply_status operation
    with tracer.start_as_current_span(
        "update_load_reply_status",
        attributes={
            "load_id": load_id,
            "application_name": application_name or "unknown"
        }
    ) as span:
        try:
            api_base_url = os.getenv("NUMEO_API_URL", "https://dev-api.numeo.ai")
            url = f"{api_base_url}/v1/trucks/loads/reply-status/{load_id}"
            span.set_attribute("api_url", url)

            # Prepare the request payload
            payload = {
                "applicationName": application_name,
                "offeringRate": details.get("offering_rate", 0),
                "details": details
            }

            # Record API request
            record_api_request(
                endpoint="update_load_reply_status",
                method="PUT",
                status="pending"
            )

            # Make the PUT request with timeout and retry logic in a child span
            try:
                logger.debug(f"Updating load reply status for load_id: {load_id}")
                response = requests.put(url, json=payload, timeout=10)  # 10 second timeout
                logger.info(f"Load reply status updated successfully for load_id: {load_id}")

            except requests.exceptions.Timeout:

                return {
                    "success": False,
                    "error": "Request timed out",
                    "message": "Request timed out while updating load reply status",
                }

            except requests.exceptions.ConnectionError:

                return {
                    "success": False,
                    "error": "Connection error",
                    "message": "Failed to connect to the API endpoint",
                }

            logger.info(f"Load reply status update completed successfully for load_id: {load_id}")

            # Return the response data
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json() if response.content else None,
                "message": "Load reply status successfully updated",
            }
        except requests.exceptions.RequestException as e:
            # Handle request errors
            error_message = str(e)
            error_type = type(e).__name__


            # Log error details
            logger.error(
                f"Error updating load reply status for load_id: {load_id}",
                exc_info=True
            )

            return {
                "success": False,
                # "status_code": status_code,
                "error": error_message,
                "message": "Failed to update load reply status",
            }
        except Exception as e:
            # Handle other errors
            error_message = str(e)
            error_type = type(e).__name__

            # Log error details
            logger.error(
                f"Unexpected error in load_reply_status for load_id: {load_id}",
                exc_info=True
            )

            # Record operation duration with failure
            duration_ms = (time.monotonic() - start_time) * 1000
            record_operation_duration(
                operation_type="load_reply",
                operation="update_status",
                success=False,
                duration_ms=duration_ms,
                extra_attributes={
                    "load_id": load_id,
                    "application": application_name or "unknown",
                    "error.type": error_type
                }
            )

            # Set error attributes on span
            span.record_exception(e)
            span.set_attribute("status", "error")
            span.set_attribute("error.type", error_type)
            span.set_attribute("error.message", error_message)
            span.set_attribute("duration_ms", duration_ms)

            return {
                "success": False,
                "error": error_message,
                "message": "An unexpected error occurred while updating load reply status",
            }



# 1. Not generated email signature + company_footer
# 2.
