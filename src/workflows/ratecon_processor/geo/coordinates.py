#!/usr/bin/env python3
"""
Geographic utilities for handling coordinates and location data.
"""
import logging
import requests
import asyncio
import sys
import os
from typing import Dict, Any, Optional, List

# Add the project root to the path
# This allows absolute imports from the root
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import centralized MongoDB connection module
from db import mongo

from ..constants import HERE_API_KEY, GOOGLE_API_KEY

# Configure logger
logger = logging.getLogger(__name__)

async def get_coordinates(location: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get coordinates for a location."""
    try:
        # Check if we already have coordinates
        if location.get("coordinates") and location["coordinates"].get("coordinates"):
            return {
                "lat": location["coordinates"]["coordinates"][1],
                "lng": location["coordinates"]["coordinates"][0],
            }
        
        # Build location string
        location_string = ""
        if location.get("street"):
            location_string += location["street"] + ", "
        if location.get("city"):
            location_string += location["city"] + ", "
        if location.get("state"):
            location_string += location["state"] + " "
        if location.get("zip"):
            location_string += location["zip"]

        # Clean up location string
        location_string = location_string.strip()
        if location_string.endswith(","):
            location_string = location_string[:-1]

        # Check if we have this location in our database
        location_doc = mongo.find_one(
            "locations",
            {"location_string": location_string}
        )
        if location_doc and location_doc.get("coordinates"):
            return {
                "lat": location_doc["coordinates"]["coordinates"][1],
                "lng": location_doc["coordinates"]["coordinates"][0],
            }

        # If we have HERE API key, try that first
        if HERE_API_KEY:
            try:
                url = f"https://geocode.search.hereapi.com/v1/geocode?q={location_string}&apiKey={HERE_API_KEY}"
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("items") and len(data["items"]) > 0:
                        position = data["items"][0].get("position")
                        if position:
                            # Save to database for future use
                            try:
                                mongo.update_one(
                                    "locations",
                                    {"location_string": location_string},
                                    {
                                        "$set": {
                                            "coordinates": {
                                                "type": "Point",
                                                "coordinates": [position["lng"], position["lat"]],
                                            }
                                        }
                                    },
                                    upsert=True
                                )
                            except Exception as db_error:
                                logger.warning(f"Failed to update location in database: {str(db_error)}")
                            return position
            except Exception as e:
                logger.warning(f"Error with HERE geocoding API: {str(e)}")

        # If HERE API fails or is not available, try Google Maps API
        if GOOGLE_API_KEY:
            result = await fetch_from_google_api(location)
            if result:
                # Save to database for future use
                try:
                    mongo.update_one(
                        "locations",
                        {"location_string": location_string},
                        {
                            "$set": {
                                "coordinates": {
                                    "type": "Point",
                                    "coordinates": [result["lng"], result["lat"]],
                                }
                            }
                        },
                        upsert=True
                    )
                except Exception as db_error:
                    logger.warning(f"Failed to update location in database: {str(db_error)}")
                return result

        return None

    except Exception as e:
        logger.error(f"Error getting coordinates: {str(e)}")
        return None


async def fetch_from_google_api(location: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fetch coordinates from Google Maps API."""
    try:
        # Build location string
        location_string = ""
        if location.get("street"):
            location_string += location["street"] + ", "
        if location.get("city"):
            location_string += location["city"] + ", "
        if location.get("state"):
            location_string += location["state"] + " "
        if location.get("zip"):
            location_string += location["zip"]

        # Clean up location string
        location_string = location_string.strip()
        if location_string.endswith(","):
            location_string = location_string[:-1]

        # Call Google Maps API
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location_string}&key={GOOGLE_API_KEY}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if data.get("results") and len(data["results"]) > 0:
                geometry = data["results"][0].get("geometry", {})
                location_data = geometry.get("location", {})
                if location_data.get("lat") and location_data.get("lng"):
                    return {
                        "lat": location_data["lat"],
                        "lng": location_data["lng"],
                    }

        return None

    except Exception as e:
        logger.error(f"Error with Google Maps API: {str(e)}")
        return None
