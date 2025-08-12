#!/usr/bin/env python3
"""
Route calculation utilities for determining distances between locations.
"""
import logging
import math
import requests
import asyncio
from typing import Dict, Any, List, Optional, Tuple

from ..constants import HERE_API_KEY
from .coordinates import get_coordinates

# Configure logger
logger = logging.getLogger(__name__)


async def calculate_route_distances(route: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate distances between route stops using HERE API or haversine formula."""
    try:
        total_distance = 0
        
        # We need at least two stops to calculate a route
        if len(route) < 2:
            return {"route": route, "totalDistance": 0}

        # First, ensure all stops have coordinates using parallel processing
        await _ensure_all_coordinates(route)
        
        # Calculate distances between stops in parallel
        distance_results = await _calculate_all_distances(route)
        
        # Apply the calculated distances to the route
        for i, distance in enumerate(distance_results):
            if i < len(route) - 1 and distance is not None:
                route[i]["distanceToNext"] = distance
                total_distance += distance

        return {"route": route, "totalDistance": total_distance}

    except Exception as e:
        logger.error(f"Error calculating route distances: {str(e)}")
        return {"route": route, "totalDistance": 0}


async def _ensure_all_coordinates(route: List[Dict[str, Any]]) -> None:
    """Ensure all stops in the route have coordinates using parallel processing."""
    # Create a list of stops that need coordinates
    stops_needing_coords = []
    indices = []
    
    for i, stop in enumerate(route):
        if stop.get("location") and not stop["location"].get("coordinates"):
            stops_needing_coords.append(stop["location"])
            indices.append(i)
    
    if not stops_needing_coords:
        return
    
    # Process all geocoding requests in parallel
    coordinates_results = await asyncio.gather(
        *[get_coordinates(location) for location in stops_needing_coords]
    )
    
    # Update the route with the obtained coordinates
    for i, coords in zip(indices, coordinates_results):
        if coords:
            route[i]["location"]["coordinates"] = {
                "type": "Point",
                "coordinates": [coords["lng"], coords["lat"]]
            }


async def _calculate_all_distances(route: List[Dict[str, Any]]) -> List[Optional[float]]:
    """Calculate all distances between consecutive stops in parallel."""
    distance_tasks = []
    
    for i in range(len(route) - 1):
        from_stop = route[i]
        to_stop = route[i + 1]
        
        # Skip if either stop is missing location information
        if (
            not from_stop.get("location")
            or not to_stop.get("location")
            or not from_stop["location"].get("coordinates")
            or not to_stop["location"].get("coordinates")
        ):
            distance_tasks.append(None)
            continue
        
        # Get coordinates
        from_coords = from_stop["location"]["coordinates"]
        to_coords = to_stop["location"]["coordinates"]
        
        # Create a task for calculating this distance
        task = _calculate_single_distance(from_coords, to_coords)
        distance_tasks.append(task)
    
    # Execute all distance calculations in parallel
    return await asyncio.gather(*[task for task in distance_tasks if task is not None])


async def _calculate_single_distance(from_coords: Dict[str, Any], to_coords: Dict[str, Any]) -> Optional[float]:
    """Calculate distance between two points using HERE API with fallback to haversine."""
    # Calculate distance using HERE API if available
    distance = await calculate_distance_with_here_api(from_coords, to_coords)
    
    # If HERE API fails, fall back to haversine formula
    if distance is None:
        distance = calculate_haversine_distance(
            from_coords["coordinates"][1],  # lat
            from_coords["coordinates"][0],  # lng
            to_coords["coordinates"][1],    # lat
            to_coords["coordinates"][0]     # lng
        )
    
    return distance


async def calculate_distance_with_here_api(
    from_coords: Dict[str, Any], to_coords: Dict[str, Any]
) -> Optional[float]:
    """Calculate distance between two points using HERE Routing API."""
    try:
        if not HERE_API_KEY:
            return None

        # Extract coordinates
        from_lat = from_coords["coordinates"][1]
        from_lng = from_coords["coordinates"][0]
        to_lat = to_coords["coordinates"][1]
        to_lng = to_coords["coordinates"][0]

        # Call HERE Routing API
        url = f"https://router.hereapi.com/v8/routes?transportMode=truck&origin={from_lat},{from_lng}&destination={to_lat},{to_lng}&return=summary&apiKey={HERE_API_KEY}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("routes") and len(data["routes"]) > 0:
                sections = data["routes"][0].get("sections", [])
                if sections and len(sections) > 0:
                    summary = sections[0].get("summary", {})
                    if summary.get("length"):
                        # Convert meters to miles
                        return summary["length"] / 1609.34

        return None

    except Exception as e:
        logger.error(f"Error with HERE Routing API: {str(e)}")
        return None


def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees).
    Returns distance in miles.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 3956  # Radius of earth in miles
    
    # Apply a factor to account for road distance vs. straight line
    road_factor = 1.3
    
    return c * r * road_factor
