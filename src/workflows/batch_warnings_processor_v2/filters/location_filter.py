"""
Simplified Location filter for checking geographic exclusions.
Handles excludedStates format: ["FL", "Orlando, FL", "CA"]
"""

import logging
from typing import List, Set

from ..models import FilterResult, FilterSeverity, TruckCapabilities, LoadInfo

logger = logging.getLogger(__name__)


class LocationFilter:
    """Filter to check load locations against truck exclusions."""

    def __init__(self):
        self.filter_type = "location_exclusions"

    async def check_excluded_locations(
        self,
        load: LoadInfo,
        truck: TruckCapabilities
    ) -> FilterResult:
        """
        Check if load origin/destination are in excluded states/cities.

        Logic:
        - "City, State" exclusions: BLOCKING (specific city excluded)
        - "State" exclusions: WARNING (entire state preference)

        Returns:
        - Empty warnings = No location issues
        - "🚫 BLOCKED: ..." = Specific city is excluded
        - "⚠️  WARNING: ..." = State is excluded
        """
        try:
            logger.info(f"Checking excluded locations for load {load.id} for truck {truck.id}")
            # Quick check - if no excluded states, return clean
            if not truck.excluded_states:
                return FilterResult(
                    warnings=[],
                    filter_type=self.filter_type,
                    severity=FilterSeverity.INFO,
                )

            # Parse exclusions into cities and states
            excluded_cities, excluded_states = self._parse_exclusions(truck.excluded_states)

            # Check for matches
            city_blocks = self._check_city_exclusions(load, excluded_cities)
            state_warnings = self._check_state_exclusions(load, excluded_states)

            # Build result
            warnings = []
            severity = FilterSeverity.INFO

            # City exclusions are BLOCKING
            if city_blocks:
                warnings.append(f"⚠️ WARNING: Excluded locations: {', '.join(city_blocks)}")
                severity = FilterSeverity.WARNING

            # State exclusions are WARNINGS
            if state_warnings:
                warnings.append(f"⚠️ WARNING: Load travels through excluded states: {', '.join(state_warnings)}")
                if severity == FilterSeverity.INFO:
                    severity = FilterSeverity.WARNING

            return FilterResult(
                warnings=warnings,
                filter_type=self.filter_type,
                severity=severity,
                details={
                    "city_blocks": city_blocks,
                    "state_warnings": state_warnings
                }
            )

        except Exception as e:
            logger.error(f"Error in location filter: {str(e)}")
            return FilterResult(
                warnings=[],
                filter_type=self.filter_type,
                severity=FilterSeverity.INFO,
                details={"error": str(e)}
            )

    def _parse_exclusions(self, excluded_list: List[str]) -> tuple[Set[str], Set[str]]:
        """
        Parse exclusions into cities and states.

        Examples:
        - "FL" -> state exclusion
        - "Orlando, FL" -> city exclusion (only Orlando, not all of FL)
        """
        excluded_cities = set()
        excluded_states = set()

        for exclusion in excluded_list:
            exclusion = exclusion.strip()

            if ',' in exclusion:
                # Format: "City, State" - specific city exclusion
                excluded_cities.add(exclusion)
            else:
                # Format: "State" - entire state exclusion
                excluded_states.add(exclusion.upper())

        return excluded_cities, excluded_states

    def _check_city_exclusions(self, load: LoadInfo, excluded_cities: Set[str]) -> List[str]:
        """Check if specific cities are excluded."""
        matches = []

        # Check origin
        origin_location = f"{load.origin_city}, {load.origin_state}"
        if origin_location in excluded_cities:
            matches.append(origin_location)

        # Check destination
        dest_location = f"{load.destination_city}, {load.destination_state}"
        if dest_location in excluded_cities and dest_location != origin_location:
            matches.append(dest_location)

        return matches

    def _check_state_exclusions(self, load: LoadInfo, excluded_states: Set[str]) -> List[str]:
        """Check if entire states are excluded."""
        matches = []

        if load.origin_state and load.origin_state.upper() in excluded_states:
            matches.append(load.origin_state)

        if (load.destination_state and
            load.destination_state.upper() in excluded_states and
            load.destination_state.upper() != load.origin_state.upper()):
            matches.append(load.destination_state)

        return matches
