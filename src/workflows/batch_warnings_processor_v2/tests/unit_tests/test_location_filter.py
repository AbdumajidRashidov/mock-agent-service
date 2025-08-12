"""
Unit tests for location filter functionality.
Test cases: 8 scenarios covering all location exclusion logic.
"""

import pytest
from workflows.batch_warnings_processor_v2.filters.location_filter import LocationFilter
from workflows.batch_warnings_processor_v2.models import LoadInfo, TruckCapabilities, FilterSeverity

class TestLocationFilter:
    """Test suite for location filter."""

    @pytest.fixture
    def location_filter(self):
        """Create location filter instance."""
        return LocationFilter()

    @pytest.mark.asyncio
    async def test_no_exclusions_clean_result(self, location_filter):
        """Test 1: No excluded states should return clean result."""
        load = LoadInfo(
            id="TEST_001",
            origin_state="TX",
            destination_state="OK",
            origin_city="Dallas",
            destination_city="Oklahoma City",
            equipment_type="V",
            comments="Test load"
        )

        truck = TruckCapabilities(
            id="TRUCK_001",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await location_filter.check_excluded_locations(load, truck)

        assert not result.has_issues()
        assert len(result.warnings) == 0
        assert result.severity == FilterSeverity.INFO

    @pytest.mark.asyncio
    async def test_excluded_origin_state(self, location_filter):
        """Test 2: Origin state in excluded list should trigger warning."""
        load = LoadInfo(
            id="TEST_002",
            origin_state="CA",
            destination_state="TX",
            origin_city="Los Angeles",
            destination_city="Houston",
            equipment_type="V",
            comments="Test load"
        )

        truck = TruckCapabilities(
            id="TRUCK_002",
            excluded_states=["CA"],
            restrictions=[],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await location_filter.check_excluded_locations(load, truck)

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert "excluded states: CA" in result.warnings[0]
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_excluded_destination_state(self, location_filter):
        """Test 3: Destination state in excluded list should trigger warning."""
        load = LoadInfo(
            id="TEST_003",
            origin_state="TX",
            destination_state="FL",
            origin_city="Houston",
            destination_city="Miami",
            equipment_type="V",
            comments="Test load"
        )

        truck = TruckCapabilities(
            id="TRUCK_003",
            excluded_states=["FL"],
            restrictions=[],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await location_filter.check_excluded_locations(load, truck)

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert "excluded states: FL" in result.warnings[0]
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_excluded_specific_city(self, location_filter):
        """Test 4: Specific city exclusion should trigger warning."""
        load = LoadInfo(
            id="TEST_004",
            origin_state="NY",
            destination_state="TX",
            origin_city="New York",
            destination_city="Houston",
            equipment_type="V",
            comments="Test load"
        )

        truck = TruckCapabilities(
            id="TRUCK_004",
            excluded_states=["New York, NY"],
            restrictions=[],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await location_filter.check_excluded_locations(load, truck)

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert "New York, NY" in result.warnings[0]
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_both_origin_and_destination_excluded(self, location_filter):
        """Test 5: Both origin and destination excluded should list both."""
        load = LoadInfo(
            id="TEST_005",
            origin_state="CA",
            destination_state="FL",
            origin_city="Los Angeles",
            destination_city="Miami",
            equipment_type="V",
            comments="Test load"
        )

        truck = TruckCapabilities(
            id="TRUCK_005",
            excluded_states=["CA", "FL"],
            restrictions=[],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await location_filter.check_excluded_locations(load, truck)

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert "CA" in result.warnings[0]
        assert "FL" in result.warnings[0]
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_mixed_city_and_state_exclusions(self, location_filter):
        """Test 6: Mix of city and state exclusions."""
        load = LoadInfo(
            id="TEST_006",
            origin_state="NY",
            destination_state="CA",
            origin_city="New York",
            destination_city="Los Angeles",
            equipment_type="V",
            comments="Test load"
        )

        truck = TruckCapabilities(
            id="TRUCK_006",
            excluded_states=["New York, NY", "CA"],
            restrictions=[],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await location_filter.check_excluded_locations(load, truck)

        assert result.has_issues()
        assert len(result.warnings) == 2  # One for city, one for state
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_case_sensitivity_handling(self, location_filter):
        """Test 7: Case insensitive matching for states."""
        load = LoadInfo(
            id="TEST_007",
            origin_state="ca",
            destination_state="tx",
            origin_city="los angeles",
            destination_city="houston",
            equipment_type="V",
            comments="Test load"
        )

        truck = TruckCapabilities(
            id="TRUCK_007",
            excluded_states=["CA"],
            restrictions=[],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await location_filter.check_excluded_locations(load, truck)

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_empty_location_data(self, location_filter):
        """Test 8: Empty location data should not cause errors."""
        load = LoadInfo(
            id="TEST_008",
            origin_state="",
            destination_state="",
            origin_city="",
            destination_city="",
            equipment_type="V",
            comments="Test load"
        )

        truck = TruckCapabilities(
            id="TRUCK_008",
            excluded_states=["CA", "FL"],
            restrictions=[],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await location_filter.check_excluded_locations(load, truck)

        assert not result.has_issues()
        assert len(result.warnings) == 0
        assert result.severity == FilterSeverity.INFO
