#!/usr/bin/env python3
"""
Main entry point for rate confirmation processing.
This module focuses on the core extraction, sanitization, and response generation.
Geographic processing and broker information lookup have been moved to separate modules.
"""
import asyncio
import time
import logging
from typing import Any

# Import modules from our package structure
from .ai import configure_gemini_model
from .utils import (
    sanitize_processing_result,
    add_broker_contact_from_email
)
from .constants import GOOGLE_API_KEY

# Configure logger
logger = logging.getLogger(__name__)

async def mock_recognize() -> dict:
    """Mock AI document recognition with 3-second timeout - always returns static response"""
    print("Using mock Gemini AI for rate confirmation processing - simulating 15s delay")
    await asyncio.sleep(15.0)  # 15-second timeout simulation

    # Always return static rate confirmation data
    return {
        "rateConf": {
            "isRateConfirmation": True,
            "documentId": "RC-MOCK-123456",
            "rate": {
                "amount": 1500.00,
                "currency": "USD"
            },
            "route": [
                {
                    "location": {
                        "city": "Chicago",
                        "state": "IL",
                        "address": "123 Main St, Chicago, IL 60601"
                    },
                    "type": "pickup",
                    "scheduledDate": "2025-08-07"
                },
                {
                    "location": {
                        "city": "New York",
                        "state": "NY",
                        "address": "456 Broadway, New York, NY 10001"
                    },
                    "type": "delivery",
                    "scheduledDate": "2025-08-08"
                }
            ],
            "broker": {
                "companyName": "Mock Logistics LLC",
                "contactName": "John Smith",
                "email": "john@mocklogistics.com",
                "phone": "+1-555-123-4567"
            },
            "commodity": "freight",
            "weight": 40000,
            "equipmentType": "dry van"
        },
        "emailBodyContent": {
            "extractedText": "Rate confirmation document processed (static mock response)",
            "broker": {
                "mcNumber": "123456"
            }
        }
    }

async def process_ratecon(request, response_pb2) -> Any:
    """
    Process a rate confirmation document from a GCS URL.
    This function focuses on extraction, sanitization, and response generation.
    Geographic processing and broker information lookup have been moved to separate modules.

    Args:
        request: The gRPC request containing document URL and metadata
        response_pb2: The response protobuf module

    Returns:
        A ProcessRateconResponse object
    """
    start_time = time.time()

    try:
        # Extract request parameters
        document_url = request.document_url
        email_subject = request.email_subject
        email_body = request.email_body
        sender_email = request.sender_email
        sender_name = request.sender_name

        # Get Gemini API key from environment variables
        gemini_api_key = GOOGLE_API_KEY
        # Handle SecretStr object if needed
        if hasattr(gemini_api_key, 'get_secret_value'):
            gemini_api_key = gemini_api_key.get_secret_value()

        if not gemini_api_key:
            logger.error("Missing GOOGLE_API_KEY environment variable")
            return response_pb2.ProcessRateconResponse(
                success=False,
                error_message="Missing GOOGLE_API_KEY environment variable",
                is_rate_confirmation=False,
            )

        # Configure Gemini model
        model = configure_gemini_model(gemini_api_key)

        # Download the document
        # document_content = download_document(document_url)
        # if not document_content:
        #     return response_pb2.ProcessRateconResponse(
        #         success=False,
        #         error_message="Failed to download document from URL",
        #         is_rate_confirmation=False,
        #     )

        # Get the MIME type from the URL (assuming PDF for now)
        mime_type = "application/pdf"
        # Process the document with Gemini AI using the recognize function
        processing_result = await mock_recognize()

        rateConf = processing_result.get("rateConf", {})
        emailBodyContent = processing_result.get("emailBodyContent", {})

        # Only continue if it's a rate confirmation
        if not rateConf.get("isRateConfirmation", False):
            return response_pb2.ProcessRateconResponse(
                success=True, is_rate_confirmation=False
            )

        # Sanitize the processing result
        sanitized_result = sanitize_processing_result(rateConf)

        # Validate required fields
        if (
            not sanitized_result.get("documentId")
            or not sanitized_result.get("rate", {}).get("amount")
            or len(sanitized_result.get("route", [])) < 2
        ):
            return response_pb2.ProcessRateconResponse(
                success=True, is_rate_confirmation=False
            )

        # Extract sender information
        sender_info = {
            "email": sender_email.lower() if sender_email else None,
            "name": sender_name or "",
        }

        # Add broker contact from email if not already present
        sanitized_result["broker"] = add_broker_contact_from_email(
            sanitized_result.get("broker", {}),
            sender_info.get("email"),
            sender_info.get("name"),
        )


        # Calculate processing time
        processing_time = int(
            (time.time() - start_time) * 1000
        )  # Convert to milliseconds

        # In main-service, this would save to GCS and database
        # For agents-service, we just return the processed data

        # Convert result to protobuf struct
        from google.protobuf.json_format import ParseDict
        from google.protobuf.struct_pb2 import Struct

        result_struct = Struct()
        ParseDict({"fields": sanitized_result}, result_struct)

        logger.info("Ratecon processing successful")

        # Create and return the response
        return response_pb2.ProcessRateconResponse(
            success=True,
            is_rate_confirmation=True,
            rate_conf_data=result_struct,
            processing_time_ms=processing_time,
            document_id=sanitized_result.get("documentId", ""),
        )

    except Exception as e:
        logger.error(f"Error processing rate confirmation: {str(e)}")
        return response_pb2.ProcessRateconResponse(
            success=False,
            error_message=f"Error processing rate confirmation: {str(e)}",
            is_rate_confirmation=False,
        )
