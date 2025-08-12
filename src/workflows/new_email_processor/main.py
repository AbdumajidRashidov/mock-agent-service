import json
import re
import logging
import os
import requests
import time
import sys
from typing import Dict, Any, Optional
import asyncio
from openai import AsyncAzureOpenAI
import dotenv

dotenv.load_dotenv()

# Add the src directory to Python path
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.insert(0, src_dir)

# Import metrics and tracing
from otel.metrics import (
    record_email_processed,
    record_email_classification,
    record_email_processing_duration,
    record_order_extraction_duration,
    record_order_type,
    record_ai_request,
    record_ai_request_duration,
    record_route_generation,
)
from opentelemetry import trace

tracer = trace.get_tracer("email-processor-tracer")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("email-processor")

# Environment variables
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.environ.get(
    "AZURE_OPENAI_ENDPOINT", "https://numeo-oai-rtv1.cognitiveservices.azure.com"
)
AZURE_OPENAI_API_VERSION = os.environ.get(
    "AZURE_OPENAI_API_VERSION", "2025-03-01-preview"
)
HERE_API_KEY = os.environ.get("HERE_API_KEY")

# Initialize Azure OpenAI client (keeping for interface compatibility)
azure_client = AsyncAzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)


# Function to strip HTML tags
def strip_html(html_content: str) -> str:
    """Remove HTML tags from content and normalize whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"<\/?[^>]+(>|$)", "", html_content)).strip()


def clean_ai_response(response_text):
    """
    Clean AI response text by removing markdown code blocks and other formatting.
    """
    # Remove markdown code blocks (```json ... ```)
    if "```" in response_text:
        # Extract content between code blocks
        pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        matches = re.findall(pattern, response_text)
        if matches:
            return matches[0].strip()

    return response_text.strip()


async def mock_ai_classification_call(email_subject: str, email_body: str) -> str:
    """Mock AI classification call with 3-second timeout - always returns static response"""
    logger.info("Using mock AI classification - simulating 3s delay")
    await asyncio.sleep(3.0)  # 3-second timeout simulation

    # Always return static response indicating valid logistics email
    return json.dumps({"valid": True})


async def mock_ai_extraction_call(email_subject: str, email_body: str) -> str:
    """Mock AI extraction call with 3-second timeout - always returns static response"""
    logger.info("Using mock AI extraction - simulating 3s delay")
    await asyncio.sleep(3.0)  # 3-second timeout simulation

    # Always return static response with fixed order data
    mock_result = {
        "orderType": "spot",
        "orders": [
            {
                "pickup": "Chicago, IL",
                "delivery": "New York, NY",
                "route": "Chicago, IL → New York, NY",
                "offeringRate": 1500.0
            }
        ],
        "broker": {
            "mcNumber": "123456",
            "fullName": "John Doe",
            "companyName": "ABC Logistics",
            "email": "john.doe@abclogistics.com",
            "phone": "+1-555-123-4567",
            "website": "www.abclogistics.com"
        }
    }

    return json.dumps(mock_result)


async def is_order_related_email(email_subject: str, email_body: str) -> bool:
    """
    Use mock AI to determine if the email is related to logistics orders.
    """
    with tracer.start_as_current_span("is_order_related_email") as span:
        start_time = time.time()
        try:
            span.set_attribute("email_subject_length", len(email_subject))
            span.set_attribute("email_body_length", len(email_body))

            # Record AI request start
            with tracer.start_as_current_span("ai_classification_request") as ai_span:
                record_ai_request("classification", "email_processor", True)
                ai_start_time = time.time()

                ai_span.set_attribute("model", "mock-gpt-4o-mini")
                ai_span.set_attribute("request_type", "classification")

                # Use mock AI call instead of real API
                result_text = await mock_ai_classification_call(email_subject, email_body)

                # Record AI request duration
                ai_duration_ms = (time.time() - ai_start_time) * 1000
                ai_span.set_attribute("duration_ms", ai_duration_ms)
                record_ai_request_duration(
                    ai_duration_ms, "classification", "email_processor", True
                )

            try:
                with tracer.start_as_current_span(
                    "parse_classification_response"
                ) as parse_span:
                    # Clean the response text to handle markdown code blocks
                    cleaned_text = clean_ai_response(result_text)
                    result = json.loads(cleaned_text)
                    is_valid = result.get("valid", False)

                    parse_span.set_attribute("is_valid", is_valid)

                # Record classification result
                record_email_classification("email_processor", is_valid)

                # Record total duration
                duration_ms = (time.time() - start_time) * 1000
                span.set_attribute("duration_ms", duration_ms)
                span.set_attribute("is_valid", is_valid)
                record_email_processing_duration(
                    duration_ms, "email_processor", is_valid
                )

                return is_valid
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse mock AI response: {result_text}")
                # Record error in classification
                span.set_attribute("error", str(e))
                span.set_attribute("error_type", "json_decode_error")
                span.record_exception(e)
                record_ai_request("classification_parse", "email_processor", False)
                return False

        except Exception as e:
            logger.error(f"Error in mock AI classification: {str(e)}")
            # Record error in AI request
            span.set_attribute("error", str(e))
            span.set_attribute("error_type", "classification_error")
            span.record_exception(e)
            record_ai_request("classification", "email_processor", False)
            # Record total duration on error
            duration_ms = (time.time() - start_time) * 1000
            span.set_attribute("duration_ms", duration_ms)
            record_email_processing_duration(duration_ms, "email_processor", False)
            return False


async def extract_order_details(email_subject: str, email_body: str) -> Dict[str, Any]:
    """
    Extract order details from email using mock AI.
    """
    with tracer.start_as_current_span("extract_order_details") as span:
        start_time = time.time()
        success = False
        try:
            span.set_attribute("email_subject_length", len(email_subject))
            span.set_attribute("email_body_length", len(email_body))

            # Record AI request
            with tracer.start_as_current_span("ai_order_extraction_request") as ai_span:
                record_ai_request("order_extraction", "email_processor", True)
                ai_start_time = time.time()

                ai_span.set_attribute("model", "mock-gpt-4o-mini")
                ai_span.set_attribute("request_type", "order_extraction")

                # Use mock AI call instead of real API
                result_text = await mock_ai_extraction_call(email_subject, email_body)

                # Record AI request duration
                ai_duration_ms = (time.time() - ai_start_time) * 1000
                ai_span.set_attribute("duration_ms", ai_duration_ms)
                record_ai_request_duration(
                    ai_duration_ms, "order_extraction", "email_processor", True
                )

            try:
                with tracer.start_as_current_span(
                    "parse_order_extraction_response"
                ) as parse_span:
                    # Clean the response text to handle markdown code blocks
                    cleaned_text = clean_ai_response(result_text)
                    result = json.loads(cleaned_text)

                    # Additional validation to catch AI mistakes
                    result = validate_and_fix_extraction_result(result)

                    # Record order type
                    order_type = result.get("orderType", "unclassified")
                    parse_span.set_attribute("order_type", order_type)
                    record_order_type(order_type, "email_processor")

                    # Record location extraction success
                    orders = result.get("orders", [])
                    parse_span.set_attribute("orders_count", len(orders))

                success = True
                span.set_attribute("success", True)
                span.set_attribute("order_type", order_type)
                span.set_attribute("orders_count", len(orders))
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse mock AI response: {result_text}")
                # Record parse error
                span.set_attribute("error", str(e))
                span.set_attribute("error_type", "json_decode_error")
                span.record_exception(e)
                record_ai_request("order_extraction_parse", "email_processor", False)
                return {
                    "orderType": "unclassified",
                    "unclassificationReason": "Failed to parse mock AI response",
                    "orders": [],
                    "broker": {},
                }

        except Exception as e:
            logger.error(f"Error in mock AI extraction: {str(e)}")
            # Record AI error
            span.set_attribute("error", str(e))
            span.set_attribute("error_type", "extraction_error")
            span.record_exception(e)
            record_ai_request("order_extraction", "email_processor", False)
            return {
                "orderType": "unclassified",
                "unclassificationReason": f"Error in mock AI extraction: {str(e)}",
                "orders": [],
                "broker": {},
            }
        finally:
            # Record total duration
            duration_ms = (time.time() - start_time) * 1000
            span.set_attribute("duration_ms", duration_ms)
            record_order_extraction_duration(duration_ms, "email_processor", success)


def validate_and_fix_extraction_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and fix the AI extraction result to ensure consistency.
    """
    orders = result.get("orders", [])
    order_type = result.get("orderType", "unclassified")

    # Check if any orders have missing or invalid locations
    valid_orders = []
    has_invalid_orders = False

    for order in orders:
        pickup = order.get("pickup", "").strip()
        delivery = order.get("delivery", "").strip()

        # Validate pickup and delivery are not empty and follow City, State format
        if (pickup and delivery and
            is_valid_city_state_format(pickup) and
            is_valid_city_state_format(delivery)):

            # Fix route format if needed
            expected_route = f"{pickup} → {delivery}"
            order["route"] = expected_route
            valid_orders.append(order)
        else:
            has_invalid_orders = True
            logger.warning(f"Invalid order found - pickup: '{pickup}', delivery: '{delivery}'")

    # If we have invalid orders or no valid orders, mark as unclassified
    if has_invalid_orders or len(valid_orders) == 0:
        if order_type != "unclassified":
            logger.info(f"Reclassifying from '{order_type}' to 'unclassified' due to invalid/missing locations")
            result["orderType"] = "unclassified"
            result["unclassificationReason"] = "Missing or invalid pickup/delivery locations"
        result["orders"] = []
    else:
        result["orders"] = valid_orders

    return result


def is_valid_city_state_format(location: str) -> bool:
    """
    Check if location is in a valid format for logistics orders.
    Accepts both 'City, State' format and state-only format (e.g., 'VA', 'MD').
    """
    if not location or not isinstance(location, str):
        return False

    # Trim whitespace and check if empty after trimming
    location = location.strip()
    if not location:
        return False

    # Check for state-only format (e.g., 'VA', 'MD', 'California')
    if ',' not in location:
        # State should be at least 2 characters and not contain vague terms
        vague_terms = ["somewhere", "area", "region", "vicinity", "around", "near", "various"]
        if len(location) >= 2 and not any(term in location.lower() for term in vague_terms):
            return True
        return False

    # Check for City, State format
    parts = location.split(',')
    if len(parts) != 2:
        return False

    city = parts[0].strip()
    state = parts[1].strip()

    # City should not be empty and should not contain vague terms
    vague_terms = ["somewhere", "area", "region", "vicinity", "around", "near", "various"]
    if not city or any(term in city.lower() for term in vague_terms):
        return False

    # State should be 2 letters or full state name
    if not state or len(state) < 2:
        return False

    return True


async def generate_route(
    pickup: str, delivery: str, offering_rate: Optional[float] = None
) -> Dict[str, Any]:
    """
    Generate route information using HERE API.
    """
    with tracer.start_as_current_span("generate_route") as span:
        span.set_attribute("pickup", pickup)
        span.set_attribute("delivery", delivery)
        if offering_rate is not None:
            span.set_attribute("offering_rate", offering_rate)

        try:
            # Get coordinates for pickup location
            with tracer.start_as_current_span("geocode_pickup") as pickup_span:
                pickup_span.set_attribute("location", pickup)
                pickup_response = requests.get(
                    "https://geocode.search.hereapi.com/v1/geocode",
                    params={"q": pickup, "apiKey": HERE_API_KEY},
                )
                pickup_response.raise_for_status()
                pickup_data = pickup_response.json()

                if not pickup_data.get("items"):
                    span.set_attribute(
                        "error", f"Could not geocode pickup location: {pickup}"
                    )
                    return {"error": f"Could not geocode pickup location: {pickup}"}

                pickup_span.set_attribute("status_code", pickup_response.status_code)
                pickup_span.set_attribute(
                    "items_count", len(pickup_data.get("items", []))
                )

            pickup_coords = pickup_data["items"][0]["position"]
            pickup_address = pickup_data["items"][0]["address"]

            # Get coordinates for delivery location
            with tracer.start_as_current_span("geocode_delivery") as delivery_span:
                delivery_span.set_attribute("location", delivery)
                delivery_response = requests.get(
                    "https://geocode.search.hereapi.com/v1/geocode",
                    params={"q": delivery, "apiKey": HERE_API_KEY},
                )
                delivery_response.raise_for_status()
                delivery_data = delivery_response.json()

                if not delivery_data.get("items"):
                    span.set_attribute(
                        "error", f"Could not geocode delivery location: {delivery}"
                    )
                    return {"error": f"Could not geocode delivery location: {delivery}"}

                delivery_span.set_attribute(
                    "status_code", delivery_response.status_code
                )
                delivery_span.set_attribute(
                    "items_count", len(delivery_data.get("items", []))
                )

            delivery_coords = delivery_data["items"][0]["position"]
            delivery_address = delivery_data["items"][0]["address"]

            # NOTE: The original route calculation code was commented out
            # Keeping it commented as in the original
            # # Generate route
            # with tracer.start_as_current_span("route_calculation") as route_span:
            #     route_params = {
            #         "origin": f"{pickup_coords['lat']},{pickup_coords['lng']}",
            #         "destination": f"{delivery_coords['lat']},{delivery_coords['lng']}",
            #         "transportMode": "truck",
            #         "truck[width]": "25",
            #         "truck[height]": "40",
            #         "truck[length]": "180",
            #         "truck[grossWeight]": "40000",
            #         "routingMode": "fast",
            #         "departureTime": "any",
            #         "return": "polyline,summary,tolls,elevation",
            #         "apiKey": HERE_API_KEY,
            #     }

            #     route_span.set_attribute(
            #         "origin", f"{pickup_coords['lat']},{pickup_coords['lng']}"
            #     )
            #     route_span.set_attribute(
            #         "destination", f"{delivery_coords['lat']},{delivery_coords['lng']}"
            #     )

            #     route_response = requests.get(
            #         "https://router.hereapi.com/v8/routes", params=route_params
            #     )
            #     route_response.raise_for_status()
            #     route_data = route_response.json()

            #     route_span.set_attribute("status_code", route_response.status_code)

            #     if not route_data.get("routes"):
            #         span.set_attribute("error", "Could not generate route")
            #         return {"error": "Could not generate route"}

            # Mock route data since the route calculation is commented out
            route_data = {
                "routes": [{
                    "sections": [{
                        "id": "mock-route-id",
                        "polyline": "mock-polyline-data",
                        "summary": {
                            "duration": 18000,  # 5 hours in seconds
                            "length": 804672,   # ~500 miles in meters
                        },
                        "tolls": []
                    }]
                }]
            }

            route = route_data["routes"][0]["sections"][0]

            # Record route metrics
            duration_hours = round(route["summary"]["duration"] / 3600, 2)
            distance_miles = round(route["summary"]["length"] / 1609.344, 2)

            span.set_attribute("distance_miles", distance_miles)
            span.set_attribute("duration_hours", duration_hours)

            # Format the result
            result = {
                "routeId": route["id"],
                "polyline": route["polyline"],
                "duration": duration_hours,
                "length": distance_miles,
                "origin": {
                    "label": pickup_address.get("label", ""),
                    "state": pickup_address.get("state", ""),
                    "stateCode": pickup_address.get("stateCode", ""),
                    "city": pickup_address.get("city", ""),
                    "street": pickup_address.get("street", ""),
                    "postalCode": pickup_address.get("postalCode", ""),
                },
                "destination": {
                    "label": delivery_address.get("label", ""),
                    "state": delivery_address.get("state", ""),
                    "stateCode": delivery_address.get("stateCode", ""),
                    "city": delivery_address.get("city", ""),
                    "street": delivery_address.get("street", ""),
                    "postalCode": delivery_address.get("postalCode", ""),
                },
                "tolls": route.get("tolls", []),
            }

            if offering_rate is not None:
                result["offeringRate"] = offering_rate
                rate_per_mile = (
                    round(offering_rate / distance_miles, 2)
                    if distance_miles > 0
                    else None
                )
                if rate_per_mile:
                    result["ratePerMile"] = rate_per_mile
                    span.set_attribute("rate_per_mile", rate_per_mile)

            # Record successful route generation
            record_route_generation(True, "email_processor", offering_rate is not None)
            span.set_attribute("success", True)
            return result

        except Exception as e:
            logger.exception(e)
            span.set_attribute("error", str(e))
            span.set_attribute("error_type", "route_generation_error")
            span.record_exception(e)
            record_route_generation(False, "email_processor", offering_rate is not None)
            return {"error": f"generate_route: Error generating route: {str(e)}"}


async def process_email(
    email_data: Dict[str, Any], application_name: str
) -> Dict[str, Any]:
    logger.info(f"Processing email for application: {email_data, application_name}")
    """
    Main function to process an email and extract order information.
    This combines all the n8n workflows into a single function.
    """

    with tracer.start_as_current_span("process_email_metric_v2") as span:
        start_time = time.time()
        span.set_attribute("application_name", application_name)

        try:
            # Extract email data with its own span
            with tracer.start_as_current_span("extract_email_data") as data_span:
                email_subject = email_data.get("subject", "")
                email_body = email_data.get("body", "")
                thread_id = email_data.get("threadId", "")
                source = email_data.get("source", "unknown")

                data_span.set_attribute("thread_id", thread_id)
                data_span.set_attribute("source", source)
                data_span.set_attribute("email_subject_length", len(email_subject))
                data_span.set_attribute("email_body_length", len(email_body))

            # Set parent span attributes for important data
            span.set_attribute("thread_id", thread_id)
            span.set_attribute("source", source)

            # Step 1: Verify if it's a valid order-related email using mock AI
            with tracer.start_as_current_span("validate_order_email") as validate_span:
                validate_start_time = time.time()
                is_valid = await is_order_related_email(email_subject, email_body)
                validate_span.set_attribute("is_valid_order", is_valid)
                validate_span.set_attribute(
                    "duration_ms", (time.time() - validate_start_time) * 1000
                )

            span.set_attribute("is_valid_order", is_valid)

            if not is_valid:
                with tracer.start_as_current_span(
                    "prepare_not_valid_order_result"
                ) as result_span:
                    result = {
                        "threadId": thread_id,
                        "orderType": "unclassified",
                        "applicationName": application_name,
                        "unclassificationReason": "This might be unrelated email",
                        "orders": [],
                    }
                    result_span.set_attribute("result_type", "not_valid_order")

                span.set_attribute("result", "not_valid_order")
                return result

            # Step 2: Extract order details using mock AI
            with tracer.start_as_current_span(
                "extract_order_details_wrapper"
            ) as extract_span:
                extract_start_time = time.time()
                order_details = await extract_order_details(email_subject, email_body)
                order_type = order_details.get("orderType", "unclassified")
                extract_span.set_attribute("order_type", order_type)
                extract_span.set_attribute(
                    "duration_ms", (time.time() - extract_start_time) * 1000
                )

            span.set_attribute("order_type", order_type)

            # Step 3: Check if we have valid orders with pickup and delivery locations
            with tracer.start_as_current_span(
                "validate_orders"
            ) as validate_orders_span:
                orders = order_details.get("orders", [])
                valid_orders = [
                    order
                    for order in orders
                    if order.get("pickup") and order.get("delivery")
                ]

                validate_orders_span.set_attribute("orders_count", len(orders))
                validate_orders_span.set_attribute(
                    "valid_orders_count", len(valid_orders)
                )

            span.set_attribute("orders_count", len(orders))
            span.set_attribute("valid_orders_count", len(valid_orders))

            if not valid_orders:
                with tracer.start_as_current_span(
                    "prepare_no_valid_orders_result"
                ) as result_span:
                    result = {
                        "threadId": thread_id,
                        "orderType": order_details.get("orderType", "unclassified"),
                        "applicationName": application_name,
                        "unclassificationReason": order_details.get(
                            "unclassificationReason", "Couldn't extract locations"
                        ),
                        "orders": [],
                        "broker": order_details.get("broker", {}),
                    }
                    result_span.set_attribute("result_type", "no_valid_orders")

                span.set_attribute("result", "no_valid_orders")
                return result

            # Step 4: Generate routes for each valid order
            processed_orders = []
            with tracer.start_as_current_span("process_orders") as orders_span:
                orders_start_time = time.time()
                orders_span.set_attribute("orders_count", len(valid_orders))

                for i, order in enumerate(valid_orders):
                    with tracer.start_as_current_span(
                        f"process_order_{i}"
                    ) as order_span:
                        order_span.set_attribute("pickup", order.get("pickup", ""))
                        order_span.set_attribute("delivery", order.get("delivery", ""))
                        if "offeringRate" in order:
                            order_span.set_attribute(
                                "offering_rate", order.get("offeringRate")
                            )
                        order["threadId"] = thread_id
                        processed_orders.append(order)

                orders_span.set_attribute(
                    "processed_orders_count", len(processed_orders)
                )
                orders_span.set_attribute(
                    "duration_ms", (time.time() - orders_start_time) * 1000
                )

            # Step 5: Prepare the final result
            with tracer.start_as_current_span(
                "prepare_final_result"
            ) as final_result_span:
                if processed_orders:
                    final_result_span.set_attribute("result_type", "success")
                    final_result_span.set_attribute(
                        "processed_orders_count", len(processed_orders)
                    )
                    result = {
                        "threadId": thread_id,
                        "orderType": order_details.get("orderType", "unclassified"),
                        "applicationName": application_name,
                        "orders": processed_orders,
                        "broker": order_details.get("broker", {}),
                    }
                else:
                    final_result_span.set_attribute(
                        "result_type", "no_processed_orders"
                    )
                    result = {
                        "threadId": thread_id,
                        "orderType": "unclassified",
                        "applicationName": application_name,
                        "unclassificationReason": "Couldn't generate routes for any orders",
                        "orders": [],
                        "broker": order_details.get("broker", {}),
                    }

            if processed_orders:
                span.set_attribute("result", "success")
                span.set_attribute("processed_orders_count", len(processed_orders))
            else:
                span.set_attribute("result", "no_processed_orders")

            return result

        except Exception as e:
            with tracer.start_as_current_span("handle_processing_error") as error_span:
                logger.exception(e)
                error_span.set_attribute("error", str(e))
                error_span.set_attribute("error_type", "processing_error")
                error_span.record_exception(e)

                result = {
                    "threadId": email_data.get("threadId", ""),
                    "orderType": "unclassified",
                    "applicationName": application_name,
                    "unclassificationReason": f"EmailProcessingWorkflow: Error processing email: {str(e)}",
                    "orders": [],
                }

            span.set_attribute("error", str(e))
            span.set_attribute("error_type", "processing_error")
            span.record_exception(e)
            return result
        finally:
            # Record total email processing duration
            duration_ms = (time.time() - start_time) * 1000
            span.set_attribute("duration_ms", duration_ms)

            with tracer.start_as_current_span(
                "record_processing_metrics"
            ) as metrics_span:
                record_email_processing_duration(
                    duration_ms, application_name, len(email_data.get("orders", [])) > 0
                )
                metrics_span.set_attribute("duration_ms", duration_ms)
                metrics_span.set_attribute("application_name", application_name)
                metrics_span.set_attribute(
                    "has_orders", len(email_data.get("orders", [])) > 0
                )


# # Example usage with mock AI
# async def main():
#     # This is just an example of how to call the function with mock AI
#     sample_email = {
#         "subject": "Freight opportunity: Chicago to New York",
#         "body": "<p>We have a load that needs to be picked up from Chicago, IL and delivered to New York, NY. Rate: $1500. Please let me know if you're interested.</p><p>Thanks,<br>John Doe<br>ABC Logistics<br>MC# 123456<br>Phone: +1-555-123-4567<br>Email: john.doe@abclogistics.com<br>Website: www.abclogistics.com</p>",
#         "threadId": "thread_123456"
#     }

#     print("Processing email with mock AI (will take ~6 seconds due to mock delays)...")
#     result = await process_email(sample_email, "test-application")
#     print(json.dumps(result, indent=2))

# if __name__ == "__main__":
#     asyncio.run(main())
