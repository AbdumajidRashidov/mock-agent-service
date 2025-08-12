"""
Unit tests for permit filter functionality.
Test cases: 15 scenarios covering all permit requirement logic.
"""

import pytest
from unittest.mock import MagicMock
from workflows.batch_warnings_processor_v2.filters.permit_filter import PermitFilter
from workflows.batch_warnings_processor_v2.models import LoadInfo, TruckCapabilities, FilterSeverity


class TestPermitFilter:
    """Test suite for permit filter."""

    @pytest.fixture
    def permit_filter(self, mock_azure_client):
        """Create permit filter instance with mocked Azure client."""
        return PermitFilter(mock_azure_client)

    @pytest.mark.asyncio
    async def test_hazmat_permit_required_truck_lacks(self, permit_filter, mock_azure_client, ai_response_builder):
        """Test 1: Hazmat load with truck lacking hazmat permit."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.permit_violation_response(["hazmat"])
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="PERM_TEST_001",
            origin_state="TX",
            destination_state="LA",
            origin_city="Houston",
            destination_city="Baton Rouge",
            equipment_type="T",
            comments="Hazmat required - UN1203 gasoline"
        )

        truck = TruckCapabilities(
            id="TRUCK_001",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],  # No hazmat permit
            security_items=[],
            team_solo="solo"
        )

        results = await permit_filter.check_all_permits(load, truck)
        result = results[0]

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert "hazmat" in result.warnings[0].lower()
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_hazmat_permit_required_truck_has(self, permit_filter, mock_azure_client, ai_response_builder):
        """Test 2: Hazmat load with truck having hazmat permit."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.success_response(has_issues=False)
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="PERM_TEST_002",
            origin_state="TX",
            destination_state="LA",
            origin_city="Houston",
            destination_city="Baton Rouge",
            equipment_type="T",
            comments="Hazmat required - UN1203 gasoline"
        )

        truck = TruckCapabilities(
            id="TRUCK_002",
            excluded_states=[],
            restrictions=[],
            permitted_items=["hazmat"],  # Has hazmat permit
            security_items=[],
            team_solo="solo"
        )

        results = await permit_filter.check_all_permits(load, truck)
        result = results[0]

        assert not result.has_issues()
        assert len(result.warnings) == 0
        assert result.severity == FilterSeverity.INFO

    @pytest.mark.asyncio
    async def test_tanker_endorsement_required(self, permit_filter, mock_azure_client, ai_response_builder):
        """Test 3: Tanker equipment type requiring tanker endorsement."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.permit_violation_response(["tanker"])
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="PERM_TEST_003",
            origin_state="TX",
            destination_state="OK",
            origin_city="Houston",
            destination_city="Tulsa",
            equipment_type="T",  # Tanker
            comments="Liquid bulk cargo - food grade"
        )

        truck = TruckCapabilities(
            id="TRUCK_003",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],  # No tanker endorsement
            security_items=[],
            team_solo="solo"
        )

        results = await permit_filter.check_all_permits(load, truck)
        result = results[0]

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert "tanker" in result.warnings[0].lower()
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_oversize_permit_required(self, permit_filter, mock_azure_client, ai_response_builder):
        """Test 4: Oversize load requiring oversize permit."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.permit_violation_response(["oversize"])
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="PERM_TEST_004",
            origin_state="TX",
            destination_state="OK",
            origin_city="Houston",
            destination_city="Oklahoma City",
            equipment_type="LB",  # Lowboy
            comments="Oversize load - 12ft wide, pilot car required"
        )

        truck = TruckCapabilities(
            id="TRUCK_004",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],  # No oversize permit
            security_items=[],
            team_solo="solo"
        )

        results = await permit_filter.check_all_permits(load, truck)
        result = results[0]

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert "oversize" in result.warnings[0].lower()
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_double_triple_trailers_required(self, permit_filter, mock_azure_client, ai_response_builder):
        """Test 5: Double/triple trailers requiring special endorsement."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.permit_violation_response(["double_triple_trailers"])
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="PERM_TEST_005",
            origin_state="TX",
            destination_state="OK",
            origin_city="Dallas",
            destination_city="Oklahoma City",
            equipment_type="V2",  # Double van
            comments="Double trailer configuration"
        )

        truck = TruckCapabilities(
            id="TRUCK_005",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],  # No double/triple endorsement
            security_items=[],
            team_solo="solo"
        )

        results = await permit_filter.check_all_permits(load, truck)
        result = results[0]

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_canada_operating_authority_required(self, permit_filter, mock_azure_client, ai_response_builder):
        """Test 6: Canada destination requiring operating authority."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.permit_violation_response(["canada"])
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="PERM_TEST_006",
            origin_state="TX",
            destination_state="ON",  # Ontario, Canada
            origin_city="Laredo",
            destination_city="Toronto",
            equipment_type="V",
            comments="Cross border delivery to Canada"
        )

        truck = TruckCapabilities(
            id="TRUCK_006",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],  # No Canada authority
            security_items=[],
            team_solo="solo"
        )

        results = await permit_filter.check_all_permits(load, truck)
        result = results[0]

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert "canada" in result.warnings[0].lower()
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_mexico_operating_authority_required(self, permit_filter, mock_azure_client, ai_response_builder):
        """Test 7: Mexico destination requiring operating authority."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.permit_violation_response(["mexico"])
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="PERM_TEST_007",
            origin_state="CA",
            destination_state="BC",  # Baja California, Mexico
            origin_city="San Diego",
            destination_city="Tijuana",
            equipment_type="V",
            comments="Mexico cross border freight"
        )

        truck = TruckCapabilities(
            id="TRUCK_007",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],  # No Mexico authority
            security_items=[],
            team_solo="solo"
        )

        results = await permit_filter.check_all_permits(load, truck)
        result = results[0]

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert "mexico" in result.warnings[0].lower()
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_combination_endorsements_required(self, permit_filter, mock_azure_client, ai_response_builder):
        """Test 8: Complex load requiring combination endorsements."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.permit_violation_response(["combination_endorsements"])
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="PERM_TEST_008",
            origin_state="TX",
            destination_state="OK",
            origin_city="Houston",
            destination_city="Tulsa",
            equipment_type="TT",  # Truck and trailer
            comments="Complex vehicle combination"
        )

        truck = TruckCapabilities(
            id="TRUCK_008",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],  # No combination endorsements
            security_items=[],
            team_solo="solo"
        )

        results = await permit_filter.check_all_permits(load, truck)
        result = results[0]

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_hazardous_waste_permit_required(self, permit_filter, mock_azure_client, ai_response_builder):
        """Test 9: Hazardous waste requiring special permit."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.permit_violation_response(["hazardous_waste"])
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="PERM_TEST_009",
            origin_state="TX",
            destination_state="NM",
            origin_city="Houston",
            destination_city="Albuquerque",
            equipment_type="V",
            comments="Hazardous waste disposal - EPA regulated"
        )

        truck = TruckCapabilities(
            id="TRUCK_009",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],  # No hazardous waste permit
            security_items=[],
            team_solo="solo"
        )

        results = await permit_filter.check_all_permits(load, truck)
        result = results[0]

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_multiple_permits_required(self, permit_filter, mock_azure_client, ai_response_builder):
        """Test 10: Load requiring multiple permits."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.permit_violation_response(["hazmat", "tanker", "oversize"])
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="PERM_TEST_010",
            origin_state="TX",
            destination_state="LA",
            origin_city="Houston",
            destination_city="New Orleans",
            equipment_type="T",
            comments="Oversize hazmat tanker - UN1203, 14ft wide"
        )

        truck = TruckCapabilities(
            id="TRUCK_010",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],  # No permits
            security_items=[],
            team_solo="solo"
        )

        results = await permit_filter.check_all_permits(load, truck)
        result = results[0]

        assert result.has_issues()
        assert len(result.warnings) == 3
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_truck_has_all_required_permits(self, permit_filter, mock_azure_client, ai_response_builder):
        """Test 11: Truck has all required permits."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.success_response(has_issues=False)
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="PERM_TEST_011",
            origin_state="TX",
            destination_state="LA",
            origin_city="Houston",
            destination_city="Baton Rouge",
            equipment_type="T",
            comments="Hazmat tanker - UN1203 gasoline"
        )

        truck = TruckCapabilities(
            id="TRUCK_011",
            excluded_states=[],
            restrictions=[],
            permitted_items=["hazmat", "tanker"],  # Has required permits
            security_items=[],
            team_solo="solo"
        )

        results = await permit_filter.check_all_permits(load, truck)
        result = results[0]

        assert not result.has_issues()
        assert len(result.warnings) == 0
        assert result.severity == FilterSeverity.INFO

    @pytest.mark.asyncio
    async def test_no_permits_required_clean_load(self, permit_filter, mock_azure_client, ai_response_builder):
        """Test 12: Clean load requiring no permits."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.success_response(has_issues=False)
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="PERM_TEST_012",
            origin_state="TX",
            destination_state="OK",
            origin_city="Dallas",
            destination_city="Oklahoma City",
            equipment_type="V",
            comments="General freight - standard delivery"
        )

        truck = TruckCapabilities(
            id="TRUCK_012",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],  # No permits needed
            security_items=[],
            team_solo="solo"
        )

        results = await permit_filter.check_all_permits(load, truck)
        result = results[0]

        assert not result.has_issues()
        assert len(result.warnings) == 0
        assert result.severity == FilterSeverity.INFO

    @pytest.mark.asyncio
    async def test_international_loads_with_authority(self, permit_filter, mock_azure_client, ai_response_builder):
        """Test 13: International load with proper authority."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.success_response(has_issues=False)
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="PERM_TEST_013",
            origin_state="TX",
            destination_state="ON",
            origin_city="Laredo",
            destination_city="Toronto",
            equipment_type="V",
            comments="Cross border delivery to Canada"
        )

        truck = TruckCapabilities(
            id="TRUCK_013",
            excluded_states=[],
            restrictions=[],
            permitted_items=["canada"],  # Has Canada authority
            security_items=[],
            team_solo="solo"
        )

        results = await permit_filter.check_all_permits(load, truck)
        result = results[0]

        assert not result.has_issues()
        assert len(result.warnings) == 0
        assert result.severity == FilterSeverity.INFO

    @pytest.mark.asyncio
    async def test_ai_service_error_handling(self, permit_filter, mock_azure_client):
        """Test 14: AI service error should be handled gracefully."""
        # Simulate AI service error
        mock_azure_client.chat.completions.create.side_effect = Exception("AI service unavailable")

        load = LoadInfo(
            id="PERM_TEST_014",
            origin_state="TX",
            destination_state="OK",
            origin_city="Dallas",
            destination_city="Oklahoma City",
            equipment_type="V",
            comments="Test load"
        )

        truck = TruckCapabilities(
            id="TRUCK_014",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        results = await permit_filter.check_all_permits(load, truck)
        result = results[0]

        # Should return a warning result on error
        assert result.has_issues()
        assert len(result.warnings) == 1
        assert result.severity == FilterSeverity.WARNING
        assert "error" in result.details

    @pytest.mark.asyncio
    async def test_custom_prompt_usage(self, permit_filter, mock_azure_client, ai_response_builder):
        """Test 15: Custom prompts should be used when provided."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.success_response(has_issues=False)
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="PERM_TEST_015",
            origin_state="TX",
            destination_state="OK",
            origin_city="Dallas",
            destination_city="Oklahoma City",
            equipment_type="V",
            comments="Test load"
        )

        truck = TruckCapabilities(
            id="TRUCK_015",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        custom_prompt = "Custom permit analysis: {load_comments} {equipment_type} {truck_permits}"

        results = await permit_filter.check_all_permits(load, truck, custom_prompt)
        result = results[0]

        # Verify the custom prompt was used
        assert mock_azure_client.chat.completions.create.called
        call_args = mock_azure_client.chat.completions.create.call_args
        assert "Custom permit analysis" in call_args[1]["messages"][1]["content"]

        assert not result.has_issues()
        assert result.severity == FilterSeverity.INFO
