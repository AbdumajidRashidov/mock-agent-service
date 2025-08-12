"""
LoadAnalyzer class - simplified AI-only approach.
Only uses AI for material, permit, and security checks.
"""

import asyncio
import logging
from typing import List, Optional, Dict
from openai import AsyncAzureOpenAI

from .models import LoadAnalysisResult, FilterResult, FilterSeverity, TruckCapabilities, LoadInfo
from .filters.location_filter import LocationFilter
from .filters.material_filter import MaterialFilter
from .filters.permit_filter import PermitFilter
from .filters.security_filter import SecurityFilter
from .filters.email_filter import EmailFraudFilter

logger = logging.getLogger(__name__)


class LoadAnalyzer:
    """Main analyzer class that orchestrates simplified AI filters."""

    def __init__(self, azure_client: AsyncAzureOpenAI):
        self.azure_client = azure_client

        # Initialize all filters
        self.location_filter = LocationFilter()  # Disabled but kept for compatibility
        self.material_filter = MaterialFilter(azure_client)
        self.permit_filter = PermitFilter(azure_client)
        self.security_filter = SecurityFilter(azure_client)
        self.email_fraud_filter = EmailFraudFilter(azure_client)

    async def analyze_single_load(self, load_data: Dict, truck_data: Dict, custom_prompts: Optional[Dict] = None) -> LoadAnalysisResult:
        """Analyzes a single load against a truck's capabilities."""
        try:
            load = self._convert_load_data(load_data)
            truck = self._convert_truck_data(truck_data)
            logger.info(f"Analyzing load {load.id} for truck {truck.id}")

            # Get custom prompts
            material_prompt = custom_prompts.get('materialFilterPrompt') if custom_prompts else None
            permit_prompt = custom_prompts.get('permitFilterPrompt') if custom_prompts else None
            security_prompt = custom_prompts.get('securityFilterPrompt') if custom_prompts else None
            email_fraud_prompt = custom_prompts.get('emailFraudFilterPrompt') if custom_prompts else None

            # Run all filters in parallel
            filter_tasks = [
                self.location_filter.check_excluded_locations(load, truck),
                self.material_filter.check_restricted_materials(load, truck, material_prompt),
                self._run_permit_filter(load, truck, permit_prompt),
                self._run_security_filter(load, truck, security_prompt),
                self._run_email_fraud_filter(load, email_fraud_prompt)
            ]

            filter_results = await asyncio.gather(*filter_tasks, return_exceptions=True)

            logger.info(f"Completed all filters for load {load.id}, got {len(filter_results)} results")

            # Check for any exceptions from the filters
            exceptions = [res for res in filter_results if isinstance(res, Exception)]
            if exceptions:
                for exc in exceptions:
                    logger.error(f"Filter error for load {load.id}: {exc}")
                error_result = FilterResult(
                    warnings=[f"Analysis failed for load {load.id}"],
                    filter_type="system_error",
                    severity=FilterSeverity.WARNING,
                    details={"error": str(exceptions[0])}
                )
                # We create a result here so it can be processed into a WarningItem
                return self._process_filter_results(load.id, truck.id, [error_result])

            # Flatten results (permit and security filters return lists)
            all_results = []
            for result in filter_results:
                if isinstance(result, list):
                    all_results.extend(result)
                else:
                    all_results.append(result)

            # Process results to extract only issues
            return self._process_filter_results(load.id, truck.id, all_results)
        except Exception as e:
            logger.error(f"Critical error analyzing load {load_data.get('id', 'unknown')}: {str(e)}")
            error_result = FilterResult(
                warnings=[f"Analysis failed for load {load_data.get('id', 'unknown')}"],
                filter_type="system_error",
                severity=FilterSeverity.WARNING,
                details={"error": str(e)}
            )
            return self._process_filter_results(
                load_data.get('id', 'unknown'),
                truck_data.get('id', 'unknown'),
                [error_result]
            )

    async def _run_permit_filter(self, load: LoadInfo, truck: TruckCapabilities, permit_prompt: Optional[str] = None) -> List[FilterResult]:
        """Run all permit filters and return results."""
        return await self.permit_filter.check_all_permits(load, truck, permit_prompt)

    async def _run_security_filter(self, load: LoadInfo, truck: TruckCapabilities, security_prompt: Optional[str] = None) -> List[FilterResult]:
        """Run all security filters and return results."""
        return await self.security_filter.check_all_security(load, truck, security_prompt)

    async def _run_email_fraud_filter(self, load: LoadInfo, email_fraud_prompt: Optional[str] = None) -> List[FilterResult]:
        """Run email fraud filter and return result."""
        return await self.email_fraud_filter.check_email_fraud(load, email_fraud_prompt)

    def _process_filter_results(
        self,
        load_id: str,
        truck_id: str,
        filter_results: List[FilterResult]
    ) -> LoadAnalysisResult:
        """Process filter results and extract only actual issues."""
        warning_issues = []

        # Process each filter result
        for result in filter_results:
            if result.has_issues():  # Only process results with actual warnings
                warning_issues.extend(result.warnings)

        return LoadAnalysisResult(
            load_id=load_id,
            truck_id=truck_id,
            warning_issues=warning_issues,
            filter_results=filter_results
        )

    def _convert_load_data(self, load_data: dict) -> LoadInfo:
        """Convert protobuf load data to LoadInfo model - Updated for new schema."""
        try:
            # Extract location information using correct field names
            origin = load_data.get('origin', {})
            destination = load_data.get('destination', {})
            shipment_details = load_data.get('shipment_details', {})

            # Extract email history details
            email_history = load_data.get('email_history', {})
            details = email_history.get('details', {})

            return LoadInfo(
                id=load_data.get('id', ''),
                origin_state=origin.get('state_prov', ''),
                destination_state=destination.get('state_prov', ''),
                origin_city=origin.get('city', ''),
                destination_city=destination.get('city', ''),
                equipment_type=load_data.get('equipment_type', ''),
                comments=load_data.get('comments', ''),
                maximum_weight_pounds=shipment_details.get('maximum_weight_pounds'),
                maximum_length_feet=shipment_details.get('maximum_length_feet'),
                commodity=details.get('commodity'),
                special_notes=details.get('specialNotes'),
                driver_should_load=details.get('driverShouldLoad'),
                driver_should_unload=details.get('driverShouldUnload'),
                is_team_driver=details.get('isTeamDriver')
            )
        except Exception as e:
            logger.error(f"Error converting load data: {str(e)}")
            # Return minimal load info
            return LoadInfo(
                id=load_data.get('id', 'unknown'),
                origin_state='',
                destination_state='',
                origin_city='',
                destination_city='',
                equipment_type='',
                comments=''
            )

    def _convert_truck_data(self, truck_data: dict) -> TruckCapabilities:
        """Convert protobuf truck data to TruckCapabilities model - Updated for new schema."""
        try:
            # Extract truck capabilities
            is_permitted = truck_data.get('is_permitted', {})
            security = truck_data.get('security', {})

            # Convert boolean maps to lists of enabled features
            permitted_items = [key for key, value in is_permitted.items() if value is True]
            security_items = [key for key, value in security.items() if value is True]


            return TruckCapabilities(
                id=truck_data.get('id', '') or truck_data.get('truck_id', ''),
                excluded_states=truck_data.get('excluded_states', []),
                restrictions=truck_data.get('restrictions', []),
                permitted_items=permitted_items,
                security_items=security_items,
                team_solo=truck_data.get('team_solo', 'solo'),
                max_length=truck_data.get('length'),
                max_weight=truck_data.get('weight')
            )

        except Exception as e:
            logger.error(f"Error converting truck data: {str(e)}")
            # Return minimal truck capabilities
            return TruckCapabilities(
                id=truck_data.get('id', 'unknown'),
                excluded_states=[],
                restrictions=[],
                permitted_items=[],
                security_items=[],
                team_solo='solo'
            )
