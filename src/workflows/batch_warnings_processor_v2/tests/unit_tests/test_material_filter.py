"""
Unit tests for material filter functionality.
Test cases: 12 scenarios covering all material restriction logic.
"""

import pytest
from unittest.mock import MagicMock
from workflows.batch_warnings_processor_v2.filters.material_filter import MaterialFilter
from workflows.batch_warnings_processor_v2.models import LoadInfo, TruckCapabilities, FilterSeverity


class TestMaterialFilter:
    """Test suite for material filter."""

    @pytest.fixture
    def material_filter(self, mock_azure_client):
        """Create material filter instance with mocked Azure client."""
        return MaterialFilter(mock_azure_client)

    @pytest.mark.asyncio
    async def test_no_restrictions_clean_result(self, material_filter):
        """Test 1: No truck restrictions should return clean result."""
        load = LoadInfo(
            id="MAT_TEST_001",
            origin_state="TX",
            destination_state="OK",
            origin_city="Dallas",
            destination_city="Oklahoma City",
            equipment_type="V",
            comments="General freight, no hazmat"
        )

        truck = TruckCapabilities(
            id="TRUCK_001",
            excluded_states=[],
            restrictions=[],  # No restrictions
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await material_filter.check_restricted_materials(load, truck)

        assert not result.has_issues()
        assert len(result.warnings) == 0
        assert result.severity == FilterSeverity.INFO
        assert result.details["reason"] == "no_restrictions"

    @pytest.mark.asyncio
    async def test_direct_material_match(self, material_filter, mock_azure_client, ai_response_builder):
        """Test 2: Direct material name match should trigger warning."""
        # Setup AI response for material violation
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.material_violation_response(["acetone"])
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="MAT_TEST_002",
            origin_state="TX",
            destination_state="LA",
            origin_city="Houston",
            destination_city="New Orleans",
            equipment_type="T",
            comments="Acetone drums - chemical delivery"
        )

        truck = TruckCapabilities(
            id="TRUCK_002",
            excluded_states=[],
            restrictions=["acetone"],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await material_filter.check_restricted_materials(load, truck)

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert "acetone" in result.warnings[0].lower()
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_hazmat_keyword_detection(self, material_filter, mock_azure_client, ai_response_builder):
        """Test 3: Hazmat keywords should trigger warning."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.material_violation_response(["hazmat"])
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="MAT_TEST_003",
            origin_state="TX",
            destination_state="OK",
            origin_city="Houston",
            destination_city="Tulsa",
            equipment_type="T",
            comments="Hazmat required - chemical tanker load"
        )

        truck = TruckCapabilities(
            id="TRUCK_003",
            excluded_states=[],
            restrictions=["hazmat"],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await material_filter.check_restricted_materials(load, truck)

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_alcohol_restriction(self, material_filter, mock_azure_client, ai_response_builder):
        """Test 4: Alcohol restriction should be detected."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.material_violation_response(["alcohol"])
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="MAT_TEST_004",
            origin_state="CA",
            destination_state="NV",
            origin_city="San Francisco",
            destination_city="Reno",
            equipment_type="V",
            comments="Beer and wine distribution delivery"
        )

        truck = TruckCapabilities(
            id="TRUCK_004",
            excluded_states=[],
            restrictions=["alcohol"],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await material_filter.check_restricted_materials(load, truck)

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_step_deck_ramp_requirement(self, material_filter, mock_azure_client, ai_response_builder):
        """Test 5: Step deck with ramp requirement should trigger warning."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.material_violation_response(["ramp required"])
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="MAT_TEST_005",
            origin_state="TX",
            destination_state="OK",
            origin_city="Dallas",
            destination_city="Oklahoma City",
            equipment_type="SD",
            comments="Heavy machinery - ramp required for loading/unloading"
        )

        truck = TruckCapabilities(
            id="TRUCK_005",
            excluded_states=[],
            restrictions=["ramp required"],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await material_filter.check_restricted_materials(load, truck)

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_equipment_type_inference(self, material_filter, mock_azure_client, ai_response_builder):
        """Test 6: Equipment type should influence material detection."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.material_violation_response(["liquid chemicals"])
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="MAT_TEST_006",
            origin_state="TX",
            destination_state="LA",
            origin_city="Houston",
            destination_city="Baton Rouge",
            equipment_type="T",  # Tanker
            comments="Liquid chemical delivery"
        )

        truck = TruckCapabilities(
            id="TRUCK_006",
            excluded_states=[],
            restrictions=["chemicals"],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await material_filter.check_restricted_materials(load, truck)

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_multiple_restricted_materials(self, material_filter, mock_azure_client, ai_response_builder):
        """Test 7: Multiple restricted materials should be detected."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.material_violation_response(["alcohol", "chemicals"])
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="MAT_TEST_007",
            origin_state="TX",
            destination_state="OK",
            origin_city="Houston",
            destination_city="Tulsa",
            equipment_type="T",
            comments="Mixed load: alcoholic beverages and cleaning chemicals"
        )

        truck = TruckCapabilities(
            id="TRUCK_007",
            excluded_states=[],
            restrictions=["alcohol", "chemicals"],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await material_filter.check_restricted_materials(load, truck)

        assert result.has_issues()
        assert len(result.warnings) == 2
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_clean_load_with_restrictions(self, material_filter, mock_azure_client, ai_response_builder):
        """Test 8: Clean load should pass even with truck restrictions."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.success_response(has_issues=False)
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="MAT_TEST_008",
            origin_state="TX",
            destination_state="OK",
            origin_city="Dallas",
            destination_city="Oklahoma City",
            equipment_type="V",
            comments="General merchandise - dry goods only"
        )

        truck = TruckCapabilities(
            id="TRUCK_008",
            excluded_states=[],
            restrictions=["alcohol", "hazmat", "chemicals"],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await material_filter.check_restricted_materials(load, truck)

        assert not result.has_issues()
        assert len(result.warnings) == 0
        assert result.severity == FilterSeverity.INFO

    @pytest.mark.asyncio
    async def test_empty_load_comments(self, material_filter, mock_azure_client, ai_response_builder):
        """Test 9: Empty load comments should not cause errors."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.success_response(has_issues=False)
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="MAT_TEST_009",
            origin_state="TX",
            destination_state="OK",
            origin_city="Dallas",
            destination_city="Oklahoma City",
            equipment_type="V",
            comments=""  # Empty comments
        )

        truck = TruckCapabilities(
            id="TRUCK_009",
            excluded_states=[],
            restrictions=["alcohol"],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await material_filter.check_restricted_materials(load, truck)

        assert not result.has_issues()
        assert len(result.warnings) == 0
        assert result.severity == FilterSeverity.INFO

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self, material_filter, mock_azure_client, ai_response_builder):
        """Test 10: Case insensitive material matching."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.material_violation_response(["ALCOHOL"])
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="MAT_TEST_010",
            origin_state="TX",
            destination_state="OK",
            origin_city="Dallas",
            destination_city="Oklahoma City",
            equipment_type="V",
            comments="BEER delivery - ALCOHOL shipment"
        )

        truck = TruckCapabilities(
            id="TRUCK_010",
            excluded_states=[],
            restrictions=["alcohol"],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await material_filter.check_restricted_materials(load, truck)

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_ai_service_error_handling(self, material_filter, mock_azure_client):
        """Test 11: AI service errors should be handled gracefully."""
        # Simulate AI service error
        mock_azure_client.chat.completions.create.side_effect = Exception("AI service unavailable")

        load = LoadInfo(
            id="MAT_TEST_011",
            origin_state="TX",
            destination_state="OK",
            origin_city="Dallas",
            destination_city="Oklahoma City",
            equipment_type="V",
            comments="Test load"
        )

        truck = TruckCapabilities(
            id="TRUCK_011",
            excluded_states=[],
            restrictions=["alcohol"],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        result = await material_filter.check_restricted_materials(load, truck)

        # Should return a warning result on error
        assert result.has_issues()
        assert len(result.warnings) == 1
        assert result.severity == FilterSeverity.WARNING
        assert "error" in result.details

    @pytest.mark.asyncio
    async def test_custom_prompt_usage(self, material_filter, mock_azure_client, ai_response_builder):
        """Test 12: Custom prompts should be used when provided."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.success_response(has_issues=False)
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="MAT_TEST_012",
            origin_state="TX",
            destination_state="OK",
            origin_city="Dallas",
            destination_city="Oklahoma City",
            equipment_type="V",
            comments="Test load"
        )

        truck = TruckCapabilities(
            id="TRUCK_012",
            excluded_states=[],
            restrictions=["alcohol"],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        custom_prompt = "Custom material analysis prompt: {load_comments} {equipment_type} {truck_restrictions}"

        result = await material_filter.check_restricted_materials(load, truck, custom_prompt)

        # Verify the custom prompt was used
        assert mock_azure_client.chat.completions.create.called
        call_args = mock_azure_client.chat.completions.create.call_args
        assert "Custom material analysis prompt" in call_args[1]["messages"][1]["content"]

        assert not result.has_issues()
        assert result.severity == FilterSeverity.INFO
