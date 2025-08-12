"""Batch Warnings Processor Module

This module handles the processing of batch warnings for multiple loads.
It leverages the OpenAI API to analyze load information against truck restrictions.
Uses asyncio for parallel processing of multiple loads.
"""

import json
import time
import os
import asyncio

from openai import AsyncAzureOpenAI
from opentelemetry import trace


# Initialize logger
import logging

logger = logging.getLogger(__name__)

# Initialize tracer
tracer = trace.get_tracer("batch-warnings-processor-tracer")

# Initialize Async OpenAI client
azure_client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)


# Move to utils
def get_keys_with_value(obj, target_value=True):
    """Extract keys/fields from protobuf where value == target_value."""
    if not obj:
        return []

    return [
        field_name
        for field_name in obj.DESCRIPTOR.fields_by_name
        if getattr(obj, field_name) == target_value
    ]


#  Move to utils
def get_restricted_items(truck):
    result = {"permittedItems": [], "securityItems": []}

    # Safe access to protobuf fields using dot notation
    if hasattr(truck, "is_permitted") and truck.is_permitted is not None:
        result["permittedItems"] = get_keys_with_value(truck.is_permitted, False)
    if hasattr(truck, "security") and truck.security is not None:
        result["securityItems"] = get_keys_with_value(truck.security, False)

    return result


async def process_batch_warnings(request, agents_serivce_pb2):
    """Process batch warnings for multiple loads asynchronously.

    Args:
        request: The BatchWarningsRequest containing application_name, truck, and loads.
        agents_serivce_pb2: The generated protobuf module containing message definitions.

    Returns:
        BatchWarningsResponse with success status, message, and warning items.
    """
    start_time = time.time()

    with tracer.start_as_current_span(
        "batch_warnings_processor.process",
        attributes={
            "application_name": request.application_name,
            "truck_id": request.truck.id if request.truck else "unknown",
            "loads_count": len(request.loads) if request.loads else 0,
        },
    ) as span:
        logger.info(f"Processing batch warnings for {len(request.loads)} loads")

        try:
            # Get truck restrictions and attributes
            warnings_list = get_restricted_items(request.truck)

            # Create a response object
            response = agents_serivce_pb2.BatchWarningsResponse(
                success=True,
                message="Batch warnings processed successfully",
            )

            # Create a response object
            response = agents_serivce_pb2.BatchWarningsResponse(
                success=True,
                message="Batch warnings processed successfully",
            )

            async def process_load_warnings(load):
                """Process warnings for a single load asynchronously.

                Args:
                    load: The load to process warnings for.

                Returns:
                    A WarningItem with the processed warnings.
                """
                load_id = load.id
                span.set_attribute(f"load_{load_id}_processing", True)

                # Create system prompt with truck restrictions
                system_prompt = f"""
                ## Context ##
                You are an analyst of the broker's emails.
                Your job is to analyze load information to ensure that all necessary restrictions, securities, and permits are met.

                ### Available Permits & Endorsements (reference only)
                - Hazmat
                - Tanker
                - Double/Triple Trailers
                - Combination Endorsements
                - Oversize/Overweight
                - Hazardous Waste/Radiological
                - Canada Operating Authority
                - Mexico Operating Authority

                ### Available Security Features (reference only)
                - TSA
                - TWIC
                - Heavy Duty Lock
                - Escort Driving OK
                - Cross Border Loads

                ## Instructions ##
                1. **Restrictions**
                - Flag a commodity **only** if it exactly matches an item in the restrictions array.

                2. **Missing Permits**
                - If the load explicitly requires a permit or endorsement (e.g., "TWIC required", "Hazmat needed") and it is **present** in the truck's attributes **permits**.
                - Only use the exact names from the **Available Permits & Endorsements** list.
                - Do not flag required permit if the required permit is not present

                3. **Lacking Security Features**
                - If the load explicitly requires a security feature (e.g., "Needs TSA", "TWIC required"), and it is **present** in the truck's attributes **securities**.
                - Only use the exact names from the **Available Security Features** list.
                - Do not flag required security feature if the required security feature is not present

                4. **Driver Configuration Issues**
                - If teamDriverRequired = true but the truck is configured for solo driving, flag a warning.
                """

                if (
                    request.truck.length is not None
                    and request.truck.length > 0
                    and request.truck.weight is not None
                    and request.truck.weight > 0
                ):
                    system_prompt += f"""
                5. **Dimensional Limits**
                - If both Max Length and Max Weight are present:
                    - Flag a warning if the load exceeds either of these limits.
                """

                system_prompt += f"""
                ## Notes
                - Do **not infer** anything that is not clearly stated in the load information.
                - All compliance issues must be based on **explicitly provided data**.
                - Carefully review the truck attributes and the load information to ensure accuracy.
                - If there are no issues, return an empty JSON object or warnings: [].

                ### Truck Attributes
                restrictions: {request.truck.restrictions}
                permits: {warnings_list['permittedItems']}
                securities: {warnings_list['securityItems']}
                Team/Solo Driver: {request.truck.team_solo}
                """

                if request.truck.length is not None and request.truck.length > 0:
                    system_prompt += f"""Max Length: {request.truck.length}
                """
                if request.truck.weight is not None and request.truck.weight > 0:
                    system_prompt += f"""Max Weight: {request.truck.weight}
                """

                # Create user message with load details
                load_details = f"""
                ## Load Information ##
                Load ID: {load.id}
                Comments: {load.comments if hasattr(load, 'comments') and load.comments else 'Not specified'}
                Equipment Type: {load.equipment_type}
                Commodity: {load.comments if hasattr(load, 'comments') and load.comments else 'Not specified'}
                Weight: {load.shipment_details.maximum_weight_pounds if hasattr(load, 'shipment_details') and hasattr(load.shipment_details, 'maximum_weight_pounds') else 'Not specified'}
                Length: {load.shipment_details.maximum_length_feet if hasattr(load, 'shipment_details') and hasattr(load.shipment_details, 'maximum_length_feet') else 'Not specified'}
                """

                # Create a nested span for the OpenAI API call
                with tracer.start_as_current_span("azure_openai_api_call") as api_span:
                    api_span.set_attribute("load_id", load_id)
                    api_span.set_attribute("application_name", request.application_name)
                    api_span.set_attribute(
                        "model", os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
                    )

                    # Record API request metrics
                    api_start_time = time.time()

                    try:
                        # Call OpenAI API asynchronously
                        response_obj = await azure_client.chat.completions.create(
                            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": load_details},
                            ],
                            temperature=0.1,
                            response_format={"type": "json_object"},
                        )

                        # Calculate API call duration and record metrics
                        api_duration_ms = (time.time() - api_start_time) * 1000
                        api_span.set_attribute("duration_ms", api_duration_ms)

                        # Process the result
                        result = response_obj.choices[0].message.content
                        warnings_data = json.loads(result)
                        raw_warnings = warnings_data.get("warnings", [])

                        # Extract warning messages if warnings are objects with 'message' field
                        warnings = []
                        for warning in raw_warnings:
                            if isinstance(warning, dict) and "message" in warning:
                                warnings.append(warning["message"])
                            elif isinstance(warning, str):
                                warnings.append(warning)
                            else:
                                # Log unexpected warning format
                                logger.warning(f"Unexpected warning format: {warning}")

                        logger.info(
                            f"Processed warnings for load {load_id}: {warnings}"
                        )

                        # Return warning item
                        return agents_serivce_pb2.WarningItem(
                            truck_id=request.truck.id if request.truck else "",
                            load_id=load_id,
                            warnings=warnings,
                        )

                    except Exception as e:
                        # Record API failure metrics
                        api_duration_ms = (time.time() - api_start_time) * 1000
                        api_span.set_attribute("error", True)
                        api_span.set_attribute("error.type", type(e).__name__)
                        api_span.set_attribute("error.message", str(e))

                        logger.error(
                            f"Error processing warnings for load {load_id}: {str(e)}"
                        )

                        # Return error warning item
                        return

            # Process all loads in parallel using asyncio.gather
            logger.info(f"Processing {len(request.loads)} loads in parallel")
            warning_items = await asyncio.gather(
                *[process_load_warnings(load) for load in request.loads]
            )

            # Add all warning items to the response
            response.warning_items.extend(warning_items)

            # Record success in span
            span.set_attribute("status", "success")
            span.set_attribute("duration_ms", (time.time() - start_time) * 1000)

            return response

        except Exception as e:
            # Record error in span
            span.set_attribute("status", "error")
            span.record_exception(e)
            span.set_attribute("duration_ms", (time.time() - start_time) * 1000)

            logger.error(f"Error processing batch warnings: {str(e)}")

            return agents_serivce_pb2.BatchWarningsResponse(
                success=False,
                message=f"Error processing batch warnings: {str(e)}",
            )
