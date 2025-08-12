import pytest
import asyncio
import sys
from pathlib import Path

# Add necessary paths
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(current_dir))

# Enable async test support
pytest_plugins = ('pytest_asyncio',)

try:
    from eval_runner import EvalRunner
    from report_generator import ReportGenerator
except ImportError:
    from .eval_runner import EvalRunner
    from .report_generator import ReportGenerator

class TestEvalSystem:
    """Test class for the evaluation system."""

    @pytest.fixture
    def eval_runner(self):
        """Create an evaluation runner instance."""
        test_cases_path = Path(__file__).parent / "test_cases.json"
        return EvalRunner(str(test_cases_path))

    @pytest.mark.asyncio
    async def test_load_test_cases(self, eval_runner):
        """Test loading test cases from API."""
        test_cases = await eval_runner.load_test_cases()

        assert isinstance(test_cases, list)
        assert len(test_cases) > 0

        # Verify structure of first test case
        test_case = test_cases[0]
        assert 'id' in test_case
        assert 'category' in test_case
        assert 'description' in test_case
        assert 'input' in test_case
        assert 'expected_output' in test_case

        # Verify input structure
        input_data = test_case['input']
        assert 'company_details' in input_data
        assert 'our_emails' in input_data
        assert 'truck' in input_data
        assert 'load' in input_data
        assert 'emails' in input_data

    def test_field_comparison(self, eval_runner):
        """Test field extraction comparison logic."""
        expected = {
            'field_updates': {
                'rateInfo.rateUsd': 1800,
                'emailHistory.details.commodity': 'electronics'
            }
        }

        # Perfect match
        actual = {
            'field_updates': {
                'rateInfo.rateUsd': 1800,
                'emailHistory.details.commodity': 'electronics'
            }
        }

        result = eval_runner.compare_field_extractions(expected, actual)
        assert result['score'] == 1.0
        assert len(result['matches']) == 2
        assert len(result['mismatches']) == 0
        assert len(result['missing']) == 0

        # Partial match
        actual_partial = {
            'field_updates': {
                'rateInfo.rateUsd': 1800,
                'emailHistory.details.commodity': 'auto parts'  # Wrong value
            }
        }

        result_partial = eval_runner.compare_field_extractions(expected, actual_partial)
        assert result_partial['score'] == 0.5  # 1 out of 2 correct
        assert len(result_partial['matches']) == 1
        assert len(result_partial['mismatches']) == 1

        # Missing fields
        actual_missing = {
            'field_updates': {
                'rateInfo.rateUsd': 1800
            }
        }

        result_missing = eval_runner.compare_field_extractions(expected, actual_missing)
        assert result_missing['score'] == 0.5  # 1 out of 2 correct
        assert len(result_missing['matches']) == 1
        assert len(result_missing['missing']) == 1

    @pytest.mark.asyncio
    async def test_single_test_execution(self, eval_runner):
        """Test running a single test case."""
        test_cases = eval_runner.load_test_cases()
        first_test = test_cases[0]

        result = await eval_runner.run_single_test(first_test)

        assert result.test_id == first_test['id']
        assert result.category == first_test['category']
        assert result.execution_time > 0
        assert result.actual_output is not None
        assert result.expected_output is not None
        assert isinstance(result.passed, bool)

    @pytest.mark.asyncio
    async def test_category_filtering(self, eval_runner):
        """Test filtering test cases by category."""
        # Test basic info requests only
        report = await eval_runner.run_evaluation(test_filter="basic_info_requests")

        assert report.total_tests > 0
        assert all(r.category == "basic_info_requests" for r in report.test_results)
        assert "basic_info_requests" in report.category_results

    @pytest.mark.asyncio
    async def test_full_evaluation_suite(self, eval_runner):
        """Test running the complete evaluation suite."""
        # This test runs the actual AI system - might take longer
        report = await eval_runner.run_evaluation()

        # Basic structure checks
        assert report.total_tests > 0
        assert report.total_tests == len(report.test_results)
        assert report.passed_tests + report.failed_tests == report.total_tests
        assert 0 <= report.success_rate <= 1

        # Category checks
        expected_categories = {
            "basic_info_requests",
            "load_cancellations",
            "rate_confirmations",
            "edge_cases",
            "complex_scenarios"
        }
        assert set(report.category_results.keys()) == expected_categories

        # Performance checks
        assert report.avg_response_time >= 0
        assert report.total_execution_time > 0

        # All test results should have required fields
        for result in report.test_results:
            assert result.test_id
            assert result.category in expected_categories
            assert result.execution_time >= 0
            assert result.actual_output is not None
            assert result.expected_output is not None

    def test_report_generation(self, eval_runner):
        """Test report generation functionality."""
        # Create a mock report
        from .eval_runner import EvaluationReport, TestResult

        mock_results = [
            TestResult(
                test_id="test_001",
                category="basic_info_requests",
                description="Test description",
                passed=True,
                execution_time=2.5,
                response_time=2.0,
                field_extraction_score=1.0,
                actual_output={'email_to_send': 'Need weight'},
                expected_output={'email_to_send': 'Need weight'}
            ),
            TestResult(
                test_id="test_002",
                category="basic_info_requests",
                description="Failed test",
                passed=False,
                execution_time=3.0,
                response_time=2.8,
                field_extraction_score=0.5,
                actual_output={'email_to_send': 'Wrong email'},
                expected_output={'email_to_send': 'Need rate'}
            )
        ]

        mock_report = EvaluationReport(
            total_tests=2,
            passed_tests=1,
            failed_tests=1,
            success_rate=0.5,
            category_results={
                "basic_info_requests": {
                    "total": 2,
                    "passed": 1,
                    "failed": 1,
                    "success_rate": 0.5
                }
            },
            avg_response_time=2.4,
            total_execution_time=5.5,
            test_results=mock_results,
            summary="Test summary"
        )

        # Test that report generation doesn't crash
        try:
            ReportGenerator.print_summary_report(mock_report)
            ReportGenerator.print_detailed_report(mock_report)
        except Exception as e:
            pytest.fail(f"Report generation failed: {e}")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_performance_thresholds(self, eval_runner):
        """Test that the system meets performance requirements."""
        # Run a subset of tests to check performance
        report = await eval_runner.run_evaluation(test_filter="basic_info")

        # Check that average response time is reasonable (< 15 seconds)
        assert report.avg_response_time < 15.0, f"Response time too slow: {report.avg_response_time}s"

        # Check that no individual test takes too long (< 30 seconds)
        for result in report.test_results:
            assert result.response_time < 30.0, f"Test {result.test_id} too slow: {result.response_time}s"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_success_rate_threshold(self, eval_runner):
        """Test that the system meets the 90% success rate requirement."""
        report = await eval_runner.run_evaluation()

        # Overall success rate should be >= 90%
        assert report.success_rate >= 0.9, f"Overall success rate below threshold: {report.success_rate:.1%}"

        # Each category should also meet the 90% threshold
        for category, stats in report.category_results.items():
            success_rate = stats['success_rate']
            assert success_rate >= 0.9, f"Category {category} below threshold: {success_rate:.1%}"


# Pytest configuration and fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Standalone CLI runner for manual testing
if __name__ == "__main__":
    import sys
    import argparse

    async def main():
        parser = argparse.ArgumentParser(description="Run load reply processor evaluation")
        parser.add_argument("--filter", help="Filter tests by category or ID")
        parser.add_argument("--detailed", action="store_true", help="Show detailed report")
        parser.add_argument("--save-json", help="Save detailed report to JSON file")

        args = parser.parse_args()

        # Initialize runner
        from .eval_runner import EvalRunner
        from .report_generator import ReportGenerator

        runner = EvalRunner()

        try:
            print("Starting evaluation...")
            report = await runner.run_evaluation(test_filter=args.filter)

            # Print reports
            if args.detailed:
                ReportGenerator.print_detailed_report(report)
            else:
                ReportGenerator.print_summary_report(report)

            # Save JSON report if requested
            if args.save_json:
                ReportGenerator.save_json_report(report, args.save_json)

            # Exit with appropriate code
            sys.exit(0 if report.success_rate >= 0.9 else 1)

        except Exception as e:
            print(f"❌ Evaluation failed: {e}")
            sys.exit(1)

    asyncio.run(main())
