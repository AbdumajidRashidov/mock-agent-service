import sys
from pathlib import Path
import json
from dataclasses import asdict

# Add paths for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from eval_runner import EvaluationReport
except ImportError:
    from .eval_runner import EvaluationReport


class ReportGenerator:
    """Generate console reports for evaluation results."""

    @staticmethod
    def print_detailed_report(report: EvaluationReport) -> None:
        """Print detailed evaluation report to console."""

        # Header
        print("\n" + "="*80)
        print("LOAD REPLY PROCESSOR EVALUATION REPORT")
        print("="*80)

        # Summary
        print(f"\n📊 SUMMARY")
        print("-" * 40)
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed_tests} ({report.success_rate:.1%})")
        print(f"Failed: {report.failed_tests}")
        print(f"Execution Time: {report.total_execution_time:.2f}s")
        print(f"Avg Response Time: {report.avg_response_time:.2f}s")

        # Overall status
        overall_status = "✅ PASS" if report.success_rate >= 0.9 else "❌ FAIL"
        print(f"Overall Status: {overall_status} (Threshold: 90%)")

        # Category breakdown
        print(f"\n📈 CATEGORY BREAKDOWN")
        print("-" * 40)

        for category, stats in report.category_results.items():
            success_rate = stats['success_rate']
            status = "✅" if success_rate >= 0.9 else "❌"

            print(f"{status} {category.replace('_', ' ').title()}")
            print(f"   Success Rate: {success_rate:.1%} ({stats['passed']}/{stats['total']})")
            print(f"   Failed: {stats['failed']}")
            print()

        # Failed tests details
        failed_tests = [r for r in report.test_results if not r.passed]
        if failed_tests:
            print(f"\n❌ FAILED TESTS DETAILS")
            print("-" * 40)

            for test in failed_tests:
                print(f"\nTest ID: {test.test_id}")
                print(f"Category: {test.category}")
                print(f"Description: {test.description}")
                print(f"Execution Time: {test.execution_time:.2f}s")

                if test.error:
                    print(f"Error: {test.error}")
                else:
                    # Field extraction issues
                    if test.field_extraction_score < 1.0:
                        details = test.field_extraction_details
                        print(f"Field Extraction Score: {test.field_extraction_score:.1%}")

                        # Show expected vs actual fields
                        expected_fields = test.expected_output.get('field_updates', {})
                        actual_fields = test.actual_output.get('field_updates', {})

                        print("  Expected Fields:")
                        if expected_fields:
                            for field, value in expected_fields.items():
                                print(f"    {field}: {value}")
                        else:
                            print("    No fields expected")

                        print("  Actual Fields:")
                        if actual_fields:
                            for field, value in actual_fields.items():
                                print(f"    {field}: {value}")
                        else:
                            print("    No fields extracted")

                        # Show AI judge feedback if available
                        if details and details.get('feedback'):
                            print(f"  AI Field Judge Feedback: {details.get('feedback')}")

                        # Legacy comparison details (if using old string matching)
                        if details and details.get('mismatches'):
                            print("  Mismatched Fields:")
                            for field, values in details['mismatches'].items():
                                print(f"    {field}: expected '{values['expected']}', got '{values['actual']}'")

                        if details and details.get('missing'):
                            print("  Missing Fields:")
                            for field, value in details['missing'].items():
                                print(f"    {field}: expected '{value}'")

                        if details and details.get('extra'):
                            print("  Extra Fields:")
                            for field, value in details['extra'].items():
                                print(f"    {field}: '{value}'")

                    # Email comparison issues
                    if test.email_comparison:
                        email_comp = test.email_comparison
                        if not email_comp.get('passes', True):
                            print(f"Email Comparison Score: {email_comp.get('overall_score', 0)}/10")
                            print(f"  Accuracy: {email_comp.get('accuracy_score', 0)}/10")
                            print(f"  Tone: {email_comp.get('tone_score', 0)}/10")
                            print(f"  Compliance: {email_comp.get('compliance_score', 0)}/10")
                            print(f"  AI Email Judge Feedback: {email_comp.get('feedback', 'No feedback')}")

                            expected_email = test.expected_output.get('email_to_send', '')
                            actual_email = test.actual_output.get('email_to_send', '')

                            print(f"  Expected Email: '{expected_email}'")
                            print(f"  Actual Email: '{actual_email}'")

                print("-" * 60)

        # Performance insights
        print(f"\n⚡ PERFORMANCE INSIGHTS")
        print("-" * 40)

        response_times = [r.response_time for r in report.test_results if r.response_time > 0]
        if response_times:
            min_time = min(response_times)
            max_time = max(response_times)
            print(f"Response Time Range: {min_time:.2f}s - {max_time:.2f}s")

            # Categorize by performance
            fast_tests = sum(1 for t in response_times if t < 5.0)
            slow_tests = sum(1 for t in response_times if t > 10.0)

            print(f"Fast Tests (<5s): {fast_tests}")
            print(f"Slow Tests (>10s): {slow_tests}")

        # Error analysis
        error_tests = [r for r in report.test_results if r.error]
        if error_tests:
            print(f"\n🐛 ERROR ANALYSIS")
            print("-" * 40)

            error_types = {}
            for test in error_tests:
                error_type = type(test.error).__name__ if hasattr(test.error, '__class__') else 'Unknown'
                error_types[error_type] = error_types.get(error_type, 0) + 1

            for error_type, count in error_types.items():
                print(f"{error_type}: {count} occurrences")

        # Recommendations
        print(f"\n💡 RECOMMENDATIONS")
        print("-" * 40)

        recommendations = []

        if report.success_rate < 0.9:
            recommendations.append("Overall success rate below 90% - review failed test cases")

        for category, stats in report.category_results.items():
            if stats['success_rate'] < 0.9:
                recommendations.append(f"Improve {category.replace('_', ' ')} handling - success rate: {stats['success_rate']:.1%}")

        if report.avg_response_time > 10.0:
            recommendations.append("Consider optimizing response time - current average above 10s")

        if not recommendations:
            recommendations.append("All metrics within acceptable ranges - good job!")

        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")

        print("\n" + "="*80)

    @staticmethod
    def print_summary_report(report: EvaluationReport) -> None:
        """Print a concise summary report."""

        status = "PASS" if report.success_rate >= 0.9 else "FAIL"
        status_icon = "✅" if status == "PASS" else "❌"

        print(f"\n{status_icon} EVALUATION {status}")
        print(f"Success Rate: {report.success_rate:.1%} ({report.passed_tests}/{report.total_tests})")
        print(f"Avg Response Time: {report.avg_response_time:.2f}s")

        # Show failing categories
        failing_categories = [
            name for name, stats in report.category_results.items()
            if stats['success_rate'] < 0.9
        ]

        if failing_categories:
            print(f"Failing Categories: {', '.join(failing_categories)}")

        if report.failed_tests > 0:
            print(f"Failed Tests: {report.failed_tests}")

    @staticmethod
    def save_json_report(report: EvaluationReport, filename: str) -> None:
        """Save detailed report as JSON file."""


        report_data = asdict(report)

        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        print(f"Detailed report saved to: {filename}")
