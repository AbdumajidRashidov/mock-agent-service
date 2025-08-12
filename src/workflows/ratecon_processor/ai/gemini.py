#!/usr/bin/env python3
"""
Gemini AI model configuration and document recognition functionality.
"""
import asyncio
import base64
import json
import logging
from typing import Dict, Any, Optional, Union

import aiohttp

# Configure logger
logger = logging.getLogger(__name__)

# Import prompt from constants
from ..constants import RATECON_PROMPT

# Gemini API endpoints
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1"
GENERATE_CONTENT_ENDPOINT = f"{GEMINI_API_BASE}/models/gemini-2.0-flash:generateContent"

class GeminiClient:
    """Client for interacting with the Gemini API directly."""

    def __init__(self, api_key: str):
        """Initialize the Gemini client with an API key."""
        self.api_key = api_key.get_secret_value() if hasattr(api_key, 'get_secret_value') else api_key
        self.session = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            self.session = None

    async def generate_content(
        self,
        prompt: str,
        document_content: bytes,
        mime_type: str,
        max_retries: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """Generate content using the Gemini API with retry logic."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async with statement.")

        headers = {
            "Content-Type": "application/json",
        }

        # Prepare the request payload
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.b64encode(document_content).decode("utf-8")
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.8,
                "topK": 40,
                "maxOutputTokens": 8192,
            }
        }

        url = f"{GENERATE_CONTENT_ENDPOINT}?key={self.api_key}"

        for attempt in range(max_retries):
            try:
                async with self.session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=60
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed after {max_retries} attempts: {str(e)}")
                    return None
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                await asyncio.sleep(wait_time)

        return None

def configure_gemini_model(api_key: Union[str, object]) -> GeminiClient:
    """
    Configure the Gemini client with the provided API key.

    Args:
        api_key: The Gemini API key (can be a string or a SecretStr)

    Returns:
        GeminiClient: Configured Gemini client instance
    """
    return GeminiClient(api_key)

async def recognize(
    model: GeminiClient,
    document_content: bytes,
    mime_type: str,
    email_snippet: str
) -> Dict[str, Any]:
    """
    Process a document with Gemini AI via direct API calls to extract rate confirmation data.

    Args:
        model: Configured GeminiClient instance
        document_content: Binary content of the document to process
        mime_type: MIME type of the document
        email_snippet: Additional context from the email

    Returns:
        Dict containing rate confirmation data and email body content
    """
    try:
        # Create the prompt with the email context
        prompt = f"{RATECON_PROMPT}\n\nAdditional context from email: {email_snippet}"

        async with model as client:
            # Generate content using the direct API client
            response = await client.generate_content(
                prompt=prompt,
                document_content=document_content,
                mime_type=mime_type
            )

            if not response:
                logger.error("Empty response from Gemini API")
                return {"rateConf": {"isRateConfirmation": False}, "emailBodyContent": {}}

            # Extract the response text
            try:
                response_text = response.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                if not response_text:
                    raise ValueError("Empty response text from Gemini API")

            except (IndexError, AttributeError, KeyError, ValueError) as e:
                logger.error(f"Failed to extract text from response: {str(e)}")
                return {"rateConf": {"isRateConfirmation": False}, "emailBodyContent": {}}

            # Find JSON in the response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                try:
                    result = json.loads(json_str)

                    # Handle the new dual JSON structure (emailBodyContent and rateConf)
                    if "emailBodyContent" in result and "rateConf" in result:
                        # The model returned the expected dual structure
                        return result
                    elif "isRateConfirmation" in result:
                        # Legacy format - just a single JSON object for rate confirmation
                        logger.warning(
                            "Model returned legacy single JSON format instead of dual structure"
                        )
                        return {"rateConf": result, "emailBodyContent": {}}
                    else:
                        # Unknown format
                        logger.error("Unexpected JSON structure in response")
                        return {
                            "rateConf": {"isRateConfirmation": False},
                            "emailBodyContent": {},
                        }
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from response: {str(e)}")
                    return {
                        "rateConf": {"isRateConfirmation": False},
                        "emailBodyContent": {},
                    }
            else:
                logger.error("No JSON found in response")
                return {"rateConf": {"isRateConfirmation": False}, "emailBodyContent": {}}

    except Exception as e:
        logger.error(f"Error processing document with Gemini: {str(e)}")
        return {"rateConf": {"isRateConfirmation": False}, "emailBodyContent": {}}
