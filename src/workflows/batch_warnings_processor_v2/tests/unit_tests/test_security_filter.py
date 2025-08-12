"""
Unit tests for security filter functionality.
Test cases: 10 scenarios covering all security requirement logic.
"""

import pytest
import json
from unittest.mock import MagicMock
from workflows.batch_warnings_processor_v2.filters.security_filter import SecurityFilter
from workflows.batch_warnings_processor_v2.models import LoadInfo, TruckCapabilities, FilterSeverity

class TestSecurityFilter:
    """Test suite for security filter."""

    @pytest.fixture
    def security_filter(self, mock_azure_client):
        """Create security filter instance with mocked Azure client."""
        return SecurityFilter(mock_azure_client)

    @pytest.mark.asyncio
    async def test_tsa_requirement_airport_delivery(self, security_filter, mock_azure_client):
        """Test 1: Airport delivery requiring TSA clearance."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "has_issues": True,
            "warnings": ["Load requires TSA clearance - driver not certified"],
            "severity": "warning",
            "requirement_type": "facility_access",
            "keywords_found": ["airport delivery", "TSA required"],
            "reasoning": "Airport cargo requires TSA clearance"
        })
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="SEC_TEST_001",
            origin_state="CA",
            destination_state="CA",
            origin_city="Los Angeles",
            destination_city="Los Angeles",
            equipment_type="V",
            comments="Airport cargo delivery - TSA clearance required"
        )

        truck = TruckCapabilities(
            id="TRUCK_001",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],
            security_items=[],  # No TSA clearance
            team_solo="solo"
        )

        results = await security_filter.check_all_security(load, truck)
        result = results[0]

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert "TSA" in result.warnings[0]
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_twic_requirement_port_delivery(self, security_filter, mock_azure_client):
        """Test 2: Port facility delivery requiring TWIC card."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "has_issues": True,
            "warnings": ["Load requires TWIC card - driver not certified"],
            "severity": "warning",
            "requirement_type": "facility_access",
            "keywords_found": ["port delivery", "TWIC required"],
            "reasoning": "Port facility access requires TWIC card"
        })
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="SEC_TEST_002",
            origin_state="TX",
            destination_state="TX",
            origin_city="Houston",
            destination_city="Houston",
            equipment_type="V",
            comments="Port terminal delivery - TWIC card required"
        )

        truck = TruckCapabilities(
            id="TRUCK_002",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],
            security_items=[],  # No TWIC card
            team_solo="solo"
        )

        results = await security_filter.check_all_security(load, truck)
        result = results[0]

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert "TWIC" in result.warnings[0]
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_high_value_cargo_security(self, security_filter, mock_azure_client):
        """Test 3: High value cargo requiring additional security."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "has_issues": True,
            "warnings": ["Load requires high-value cargo security measures"],
            "severity": "warning",
            "requirement_type": "cargo_security",
            "keywords_found": ["high value", "security escort required"],
            "reasoning": "High value cargo requires additional security protocols"
        })
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="SEC_TEST_003",
            origin_state="NY",
            destination_state="NY",
            origin_city="New York",
            destination_city="New York",
            equipment_type="V",
            comments="High value electronics - security escort required, theft target"
        )

        truck = TruckCapabilities(
            id="TRUCK_003",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],
            security_items=[],  # No special security
            team_solo="solo"
        )

        results = await security_filter.check_all_security(load, truck)
        result = results[0]

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert "security" in result.warnings[0].lower()
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_military_facility_security(self, security_filter, mock_azure_client):
        """Test 4: Military base delivery requiring security clearance."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "has_issues": True,
            "warnings": ["Load requires military facility security clearance"],
            "severity": "warning",
            "requirement_type": "facility_access",
            "keywords_found": ["military base", "security clearance"],
            "reasoning": "Military facility requires security clearance"
        })
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="SEC_TEST_004",
            origin_state="VA",
            destination_state="VA",
            origin_city="Norfolk",
            destination_city="Norfolk",
            equipment_type="V",
            comments="Military base delivery - security clearance needed"
        )

        truck = TruckCapabilities(
            id="TRUCK_004",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],
            security_items=[],  # No security clearance
            team_solo="solo"
        )

        results = await security_filter.check_all_security(load, truck)
        result = results[0]

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert "military" in result.warnings[0].lower() or "security" in result.warnings[0].lower()
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_cross_border_security_protocols(self, security_filter, mock_azure_client):
        """Test 5: Cross-border delivery requiring security protocols."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "has_issues": True,
            "warnings": ["Load requires cross-border security protocols"],
            "severity": "warning",
            "requirement_type": "regulatory_compliance",
            "keywords_found": ["cross border", "customs security"],
            "reasoning": "International shipment requires border security compliance"
        })
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="SEC_TEST_005",
            origin_state="TX",
            destination_state="NL",  # Nuevo León, Mexico
            origin_city="Laredo",
            destination_city="Monterrey",
            equipment_type="V",
            comments="Cross border delivery - customs security required"
        )

        truck = TruckCapabilities(
            id="TRUCK_005",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],
            security_items=[],  # No cross-border security
            team_solo="solo"
        )

        results = await security_filter.check_all_security(load, truck)
        result = results[0]

        assert result.has_issues()
        assert len(result.warnings) == 1
        assert "border" in result.warnings[0].lower() or "security" in result.warnings[0].lower()
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_no_security_requirements_clean(self, security_filter, mock_azure_client, ai_response_builder):
        """Test 6: General delivery with no security requirements."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.success_response(has_issues=False)
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="SEC_TEST_006",
            origin_state="TX",
            destination_state="OK",
            origin_city="Dallas",
            destination_city="Oklahoma City",
            equipment_type="V",
            comments="General freight delivery - standard warehouse"
        )

        truck = TruckCapabilities(
            id="TRUCK_006",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],
            security_items=[],  # No special security needed
            team_solo="solo"
        )

        results = await security_filter.check_all_security(load, truck)
        result = results[0]

        assert not result.has_issues()
        assert len(result.warnings) == 0
        assert result.severity == FilterSeverity.INFO

    @pytest.mark.asyncio
    async def test_truck_has_required_security_features(self, security_filter, mock_azure_client, ai_response_builder):
        """Test 7: Truck has all required security features."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.success_response(has_issues=False)
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="SEC_TEST_007",
            origin_state="CA",
            destination_state="CA",
            origin_city="Los Angeles",
            destination_city="Los Angeles",
            equipment_type="V",
            comments="Airport cargo delivery - TSA clearance required"
        )

        truck = TruckCapabilities(
            id="TRUCK_007",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],
            security_items=["tsa", "twic", "heavy_duty_lock"],  # Has required security
            team_solo="solo"
        )

        results = await security_filter.check_all_security(load, truck)
        result = results[0]

        assert not result.has_issues()
        assert len(result.warnings) == 0
        assert result.severity == FilterSeverity.INFO

    @pytest.mark.asyncio
    async def test_multiple_security_requirements(self, security_filter, mock_azure_client):
        """Test 8: Load requiring multiple security features."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "has_issues": True,
            "warnings": [
                "Load requires TSA clearance - driver not certified",
                "Load requires TWIC card - driver not certified",
                "Load requires heavy duty lock - truck not equipped"
            ],
            "severity": "warning",
            "requirement_type": "multiple_facility_access",
            "keywords_found": ["airport", "port", "high value"],
            "reasoning": "Load requires multiple security clearances and equipment"
        })
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="SEC_TEST_008",
            origin_state="CA",
            destination_state="TX",
            origin_city="Long Beach",
            destination_city="Houston",
            equipment_type="V",
            comments="High value cargo from port to airport - TSA and TWIC required, heavy duty lock needed"
        )

        truck = TruckCapabilities(
            id="TRUCK_008",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],
            security_items=[],  # No security features
            team_solo="solo"
        )

        results = await security_filter.check_all_security(load, truck)
        result = results[0]

        assert result.has_issues()
        assert len(result.warnings) == 3
        assert result.severity == FilterSeverity.WARNING

    @pytest.mark.asyncio
    async def test_ai_service_error_handling(self, security_filter, mock_azure_client):
        """Test 9: AI service error should be handled gracefully."""
        # Simulate AI service error
        mock_azure_client.chat.completions.create.side_effect = Exception("AI service unavailable")

        load = LoadInfo(
            id="SEC_TEST_009",
            origin_state="TX",
            destination_state="OK",
            origin_city="Dallas",
            destination_city="Oklahoma City",
            equipment_type="V",
            comments="Test load"
        )

        truck = TruckCapabilities(
            id="TRUCK_009",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        results = await security_filter.check_all_security(load, truck)
        result = results[0]

        # Should return a warning result on error
        assert result.has_issues()
        assert len(result.warnings) == 1
        assert result.severity == FilterSeverity.WARNING
        assert "error" in result.details

    @pytest.mark.asyncio
    async def test_custom_prompt_usage(self, security_filter, mock_azure_client, ai_response_builder):
        """Test 10: Custom prompts should be used when provided."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ai_response_builder.success_response(has_issues=False)
        mock_azure_client.chat.completions.create.return_value = mock_response

        load = LoadInfo(
            id="SEC_TEST_010",
            origin_state="TX",
            destination_state="OK",
            origin_city="Dallas",
            destination_city="Oklahoma City",
            equipment_type="V",
            comments="Test load"
        )

        truck = TruckCapabilities(
            id="TRUCK_010",
            excluded_states=[],
            restrictions=[],
            permitted_items=[],
            security_items=[],
            team_solo="solo"
        )

        custom_prompt = "Custom security analysis: {load_comments} {equipment_type} {truck_security}"

        results = await security_filter.check_all_security(load, truck, custom_prompt)
        result = results[0]

        # Verify the custom prompt was used
        assert mock_azure_client.chat.completions.create.called
        call_args = mock_azure_client.chat.completions.create.call_args
        assert "Custom security analysis" in call_args[1]["messages"][1]["content"]

        assert not result.has_issues()
        assert result.severity == FilterSeverity.INFO
