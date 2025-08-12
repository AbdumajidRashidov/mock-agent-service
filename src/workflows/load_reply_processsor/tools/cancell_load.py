import os
import time
import requests
from agents import RunContextWrapper

from dotenv import load_dotenv
from opentelemetry import trace
from otel.metrics import (
    record_api_request,
    record_api_duration,
    record_api_error,
    record_error
)

from workflows.load_reply_processsor.models import OrchestratorContext

load_dotenv()

# Get tracer
tracer = trace.get_tracer("cancel-load-tracer")


async def cancel_load(ctx: RunContextWrapper[OrchestratorContext], args: str):
    """
    Send a request to the main service to change the status of a load to cancelled.

    Args:
        ctx: The context wrapper containing load information
        args: Arguments passed to the function (not used)

    Returns:
        Dict containing the API response with success status, status code, and data
    """
    # Start timing the operation
    start_time = time.monotonic()

    # Create a span for the cancel_load operation
    with tracer.start_as_current_span(
        "cancel_load",
        attributes={
            "operation": "cancel_load"
        }
    ) as span:
        # Get load_id from context
        load_id = ctx.context.load_id

        # Get project name from context
        databaseName = ctx.context.application_name

        # Add context attributes to span
        span.set_attributes({
            "load_id": load_id,
            "database_name": databaseName
        })

        try:
            # Get the API base URL from environment variables
            api_base_url = os.getenv("NUMEO_API_URL", "https://dev-api.numeo.ai")

            # Construct the URL for the cancel endpoint
            url = f"{api_base_url}/v1/trucks/loads/{load_id}/voice-info-agent"
            span.set_attribute("api_url", url)

            # Prepare the request payload
            payload = {
                "cancelled": True,
                "projectName": databaseName
            }

            # Record API request
            record_api_request(
                endpoint="cancel_load",
                method="PUT",
                status="pending"
            )

            # Make the PUT request in a child span
            with tracer.start_as_current_span("api_cancel_load", attributes={"url": url}):
                api_start_time = time.monotonic()
                response = requests.put(url, json=payload, timeout=10)  # 10 second timeout
                response.raise_for_status()  # Raise an exception for 4XX/5XX responses

                # Record API duration
                api_duration_ms = (time.monotonic() - api_start_time) * 1000
                record_api_duration(
                    api_duration_ms,
                    endpoint="cancel_load",
                    method="PUT",
                    status="success"
                )
                span.set_attribute("api_duration_ms", api_duration_ms)
                span.set_attribute("api_status_code", response.status_code)

            # Record overall duration
            duration_ms = (time.monotonic() - start_time) * 1000
            span.set_attribute("duration_ms", duration_ms)
            span.set_attribute("status", "success")

            # Return the response data
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json() if response.content else None,
                "message": "Load successfully cancelled"
            }

        except requests.exceptions.Timeout:
            error_message = "Request timed out"
            error_type = "Timeout"

            # Record API error
            record_api_error(
                endpoint="cancel_load",
                error_type=error_type,
                status_code="timeout"
            )

            # Set error attributes on span
            span.set_attribute("status", "error")
            span.set_attribute("error.type", error_type)
            span.set_attribute("error.message", error_message)
            span.set_attribute("duration_ms", (time.monotonic() - start_time) * 1000)

            return {
                "success": False,
                "error": error_message,
                "message": "Request timed out while cancelling load"
            }

        except requests.exceptions.ConnectionError:
            error_message = "Connection error"
            error_type = "ConnectionError"

            # Record API error
            record_api_error(
                endpoint="cancel_load",
                error_type=error_type,
                status_code="connection_error"
            )

            # Set error attributes on span
            span.set_attribute("status", "error")
            span.set_attribute("error.type", error_type)
            span.set_attribute("error.message", error_message)
            span.set_attribute("duration_ms", (time.monotonic() - start_time) * 1000)

            return {
                "success": False,
                "error": error_message,
                "message": "Failed to connect to the API endpoint"
            }

        except requests.exceptions.RequestException as e:
            # Handle request errors
            error_message = str(e)
            error_type = type(e).__name__
            status_code = (
                e.response.status_code if hasattr(e, "response") and e.response else None
            )

            # Record API error
            record_api_error(
                endpoint="cancel_load",
                error_type=error_type,
                status_code=str(status_code) if status_code else "unknown"
            )

            # Set error attributes on span
            span.record_exception(e)
            span.set_attribute("status", "error")
            span.set_attribute("error.type", error_type)
            span.set_attribute("error.message", error_message)
            span.set_attribute("error.status_code", status_code)
            span.set_attribute("duration_ms", (time.monotonic() - start_time) * 1000)

            return {
                "success": False,
                "status_code": status_code,
                "error": error_message,
                "message": "Failed to cancel load"
            }

        except Exception as e:
            # Handle other errors
            error_message = str(e)
            error_type = type(e).__name__

            # Record error
            record_error(error_type, "unknown", databaseName)

            # Set error attributes on span
            span.record_exception(e)
            span.set_attribute("status", "error")
            span.set_attribute("error.type", error_type)
            span.set_attribute("error.message", error_message)
            span.set_attribute("duration_ms", (time.monotonic() - start_time) * 1000)

            return {
                "success": False,
                "error": error_message,
                "message": "An unexpected error occurred while cancelling the load"
            }
