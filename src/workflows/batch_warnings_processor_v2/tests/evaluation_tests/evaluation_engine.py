"""
Evaluation Engine for Load Analysis System
Loads test cases from JSON and validates system performance against real-world scenarios.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys
from pathlib import Path
import time


# Add project root to path for imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent  # Go up to the batch_warnings_processor_v2 directory
sys.path.insert(0, str(project_root))

try:
    from analyzer import LoadAnalyzer
except ImportError:
    # This handles the case when running tests from the project root
    from workflows.batch_warnings_processor_v2.analyzer import LoadAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of a single evaluation test case."""
    test_case_id: str
    test_case_name: str
    passed: bool
    actual_has_issues: bool
    expected_has_issues: bool
    actual_warning_count: int
    expected_warning_count: int
    actual_warnings: List[str]
    expected_contains: List[str]
    missing_keywords: List[str]
    unexpected_warnings: List[str]
    execution_time_ms: float
    error_message: Optional[str] = None


@dataclass
class EvaluationSummary:
    """Summary of evaluation results."""
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    total_execution_time_ms: float
    failed_test_cases: List[EvaluationResult]


class EvaluationEngine:
    """Main evaluation engine for testing load analysis system."""

    def __init__(self, test_cases_path: str, azure_client):
        self.test_cases_path = Path(test_cases_path)
        self.azure_client = azure_client
        self.analyzer = LoadAnalyzer(azure_client)
        self.test_cases = self._load_test_cases()

    def _load_test_cases(self) -> List[Dict[str, Any]]:
        """Load test cases from JSON file."""
        try:
            with open(self.test_cases_path, 'r') as f:
                data = json.load(f)

            logger.info(f"Loaded {len(data['test_cases'])} test cases from {self.test_cases_path}")
            return data['test_cases']
        except Exception as e:
            logger.error(f"Failed to load test cases from {self.test_cases_path}: {e}")
            return []

    def _validate_result(self,
                        actual_result,
                        expected_outcome: Dict[str, Any]) -> EvaluationResult:
        """Validate actual result against expected outcome."""
        # Extract actual data
        actual_has_issues = actual_result.has_issues()
        actual_warning_count = len(actual_result.warning_issues)
        actual_warnings = actual_result.warning_issues

        # Extract expected data
        expected_has_issues = expected_outcome.get('has_issues', False)
        expected_warning_count = expected_outcome.get('warning_count', 0)
        expected_contains = expected_outcome.get('should_contain', [])

        # Check if basic expectations match
        issues_match = actual_has_issues == expected_has_issues
        count_match = actual_warning_count == expected_warning_count

        # Check if expected keywords are present in warnings
        missing_keywords = []
        if expected_contains:
            all_warnings_text = ' '.join(actual_warnings).lower()
            for keyword in expected_contains:
                if keyword.lower() not in all_warnings_text:
                    missing_keywords.append(keyword)

        # Determine if test passed
        passed = (
            issues_match and
            count_match and
            len(missing_keywords) == 0
        )

        # Find unexpected warnings for analysis
        unexpected_warnings = []
        if not expected_has_issues and actual_has_issues:
            unexpected_warnings = actual_warnings

        return EvaluationResult(
            test_case_id="",  # Will be set by caller
            test_case_name="",  # Will be set by caller
            passed=passed,
            actual_has_issues=actual_has_issues,
            expected_has_issues=expected_has_issues,
            actual_warning_count=actual_warning_count,
            expected_warning_count=expected_warning_count,
            actual_warnings=actual_warnings,
            expected_contains=expected_contains,
            missing_keywords=missing_keywords,
            unexpected_warnings=unexpected_warnings,
            execution_time_ms=0.0  # Will be set by caller
        )

    async def evaluate_single_case(self, test_case: Dict[str, Any]) -> EvaluationResult:
        """Evaluate a single test case."""

        start_time = time.time()

        try:
            # Run analysis
            result = await self.analyzer.analyze_single_load(
                test_case['load'],
                test_case['truck']
            )

            # Validate result
            evaluation_result = self._validate_result(result, test_case['expected_outcome'])

            # Set metadata
            evaluation_result.test_case_id = test_case['id']
            evaluation_result.test_case_name = test_case['name']
            evaluation_result.execution_time_ms = (time.time() - start_time) * 1000

            return evaluation_result

        except Exception as e:
            logger.error(f"Error evaluating test case {test_case['id']}: {e}")
            execution_time = (time.time() - start_time) * 1000

            return EvaluationResult(
                test_case_id=test_case['id'],
                test_case_name=test_case['name'],
                passed=False,
                actual_has_issues=False,
                expected_has_issues=test_case['expected_outcome'].get('has_issues', False),
                actual_warning_count=0,
                expected_warning_count=test_case['expected_outcome'].get('warning_count', 0),
                actual_warnings=[],
                expected_contains=test_case['expected_outcome'].get('should_contain', []),
                missing_keywords=[],
                unexpected_warnings=[],
                execution_time_ms=execution_time,
                error_message=str(e)
            )
