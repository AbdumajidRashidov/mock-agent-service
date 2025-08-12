#!/usr/bin/env python3
"""
Weekly Integration Test Runner for Load Reply Processor

This script runs comprehensive integration tests for the load reply processor workflow
and generates a detailed report of the results. It's designed to be scheduled to run
weekly to ensure all components are functioning correctly.

Usage:
    python run_weekly_tests.py [--report-path REPORT_PATH] [--notify]

Options:
    --report-path REPORT_PATH    Path to save the test report (default: ./reports)
    --notify                    Send notification with test results
"""

import os
import sys
import json
import time
import argparse
import asyncio
import pytest
import datetime
import traceback
from pathlib import Path

# Add the parent directory to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Import notification utilities if available
try:
    from utils.notifications import send_notification
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False


class TestReporter:
    """Handles test execution and report generation."""
    
    def __init__(self, report_path="./reports"):
        """Initialize the test reporter."""
        self.report_path = Path(report_path)
        self.report_path.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.report_file = self.report_path / f"load_reply_test_report_{self.timestamp}.json"
        self.html_report_file = self.report_path / f"load_reply_test_report_{self.timestamp}.html"
        self.results = {
            "timestamp": datetime.datetime.now().isoformat(),
            "overall_status": "PENDING",
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "error": 0
            }
        }
    
    def run_tests(self):
        """Run all integration tests and collect results."""
        print("Starting Load Reply Processor integration tests...")
        
        # Create a custom pytest plugin to capture test results
        class ResultCollector:
            def __init__(self):
                self.results = []
            
            def pytest_runtest_logreport(self, report):
                if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
                    test_result = {
                        "name": report.nodeid,
                        "outcome": report.outcome,
                        "duration": report.duration,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    
                    # Add error details if test failed
                    if report.outcome == "failed":
                        test_result["error"] = {
                            "message": str(report.longrepr),
                            "traceback": self._format_traceback(report)
                        }
                    
                    self.results.append(test_result)
            
            def _format_traceback(self, report):
                """Format traceback information from the report."""
                if hasattr(report, "longrepr") and hasattr(report.longrepr, "reprtraceback"):
                    return str(report.longrepr.reprtraceback)
                return "No traceback available"
        
        # Initialize the result collector
        collector = ResultCollector()
        
        # Run the tests with the collector plugin
        test_file = os.path.join(os.path.dirname(__file__), "integration_tests.py")
        pytest.main(['-xvs', test_file, "--no-header"], plugins=[collector])
        
        # Process and store results
        self.results["tests"] = collector.results
        
        # Calculate summary statistics
        for test in collector.results:
            self.results["summary"]["total"] += 1
            self.results["summary"][test["outcome"]] += 1
        
        # Set overall status
        if self.results["summary"]["failed"] > 0 or self.results["summary"]["error"] > 0:
            self.results["overall_status"] = "FAILED"
        else:
            self.results["overall_status"] = "PASSED"
        
        # Save the results
        self._save_results()
        self._generate_html_report()
        
        return self.results
    
    def _save_results(self):
        """Save test results to a JSON file."""
        with open(self.report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Test results saved to {self.report_file}")
    
    def _generate_html_report(self):
        """Generate an HTML report from the test results."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Load Reply Processor Integration Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .summary {{ margin: 20px 0; padding: 10px; background-color: #f5f5f5; border-radius: 5px; }}
                .passed {{ color: green; }}
                .failed {{ color: red; }}
                .skipped {{ color: orange; }}
                .error {{ color: darkred; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .test-details {{ margin-top: 10px; padding: 10px; background-color: #f8f8f8; border-left: 3px solid #ccc; }}
                .error-details {{ background-color: #fff0f0; border-left: 3px solid #ffcccb; padding: 10px; margin-top: 5px; }}
                .timestamp {{ color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <h1>Load Reply Processor Integration Test Report</h1>
            <p class="timestamp">Generated on: {self.results['timestamp']}</p>
            
            <div class="summary">
                <h2>Summary</h2>
                <p>Overall Status: <span class="{self.results['overall_status'].lower()}">{self.results['overall_status']}</span></p>
                <p>Total Tests: {self.results['summary']['total']}</p>
                <p>Passed: <span class="passed">{self.results['summary']['passed']}</span></p>
                <p>Failed: <span class="failed">{self.results['summary']['failed']}</span></p>
                <p>Skipped: <span class="skipped">{self.results['summary']['skipped']}</span></p>
                <p>Errors: <span class="error">{self.results['summary']['error']}</span></p>
            </div>
            
            <h2>Test Results</h2>
            <table>
                <tr>
                    <th>Test Name</th>
                    <th>Outcome</th>
                    <th>Duration (s)</th>
                    <th>Timestamp</th>
                </tr>
        """
        
        for test in self.results["tests"]:
            html_content += f"""
                <tr>
                    <td>{test['name']}</td>
                    <td class="{test['outcome']}">{test['outcome'].upper()}</td>
                    <td>{test['duration']:.2f}</td>
                    <td>{test['timestamp']}</td>
                </tr>
            """
            
            # Add error details if test failed
            if test["outcome"] == "failed" and "error" in test:
                html_content += f"""
                <tr>
                    <td colspan="4">
                        <div class="error-details">
                            <h4>Error Details:</h4>
                            <p>{test['error']['message']}</p>
                            <pre>{test['error']['traceback']}</pre>
                        </div>
                    </td>
                </tr>
                """
        
        html_content += """
            </table>
        </body>
        </html>
        """
        
        with open(self.html_report_file, 'w') as f:
            f.write(html_content)
        
        print(f"HTML report generated at {self.html_report_file}")
        
        return self.html_report_file
    
    def get_summary_text(self):
        """Generate a text summary of the test results for notifications."""
        summary = f"Load Reply Processor Integration Test Results ({self.timestamp})\n"
        summary += f"Overall Status: {self.results['overall_status']}\n"
        summary += f"Total Tests: {self.results['summary']['total']}\n"
        summary += f"Passed: {self.results['summary']['passed']}\n"
        summary += f"Failed: {self.results['summary']['failed']}\n"
        summary += f"Skipped: {self.results['summary']['skipped']}\n"
        summary += f"Errors: {self.results['summary']['error']}\n\n"
        
        if self.results['summary']['failed'] > 0 or self.results['summary']['error'] > 0:
            summary += "Failed Tests:\n"
            for test in self.results["tests"]:
                if test["outcome"] in ["failed", "error"]:
                    summary += f"- {test['name']} ({test['outcome'].upper()})\n"
                    if "error" in test and "message" in test["error"]:
                        summary += f"  Error: {test['error']['message']}\n"
        
        return summary


def send_test_notification(reporter):
    """Send a notification with the test results."""
    if not NOTIFICATIONS_AVAILABLE:
        print("Notification module not available. Skipping notification.")
        return False
    
    try:
        summary = reporter.get_summary_text()
        subject = f"Load Reply Processor Tests: {reporter.results['overall_status']}"
        
        # Attach the HTML report if it exists
        attachments = []
        if reporter.html_report_file.exists():
            attachments.append(str(reporter.html_report_file))
        
        # Send the notification
        send_notification(
            subject=subject,
            message=summary,
            recipients=["engineering@numeo.ai"],  # Update with actual recipients
            attachments=attachments
        )
        
        print("Test notification sent successfully")
        return True
    except Exception as e:
        print(f"Failed to send notification: {str(e)}")
        traceback.print_exc()
        return False


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Run weekly integration tests for Load Reply Processor")
    parser.add_argument("--report-path", default="./reports", help="Path to save the test report")
    parser.add_argument("--notify", action="store_true", help="Send notification with test results")
    args = parser.parse_args()
    
    # Run the tests and generate reports
    reporter = TestReporter(report_path=args.report_path)
    results = reporter.run_tests()
    
    # Print summary to console
    print("\nTest Summary:")
    print(f"Overall Status: {results['overall_status']}")
    print(f"Total Tests: {results['summary']['total']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Skipped: {results['summary']['skipped']}")
    print(f"Errors: {results['summary']['error']}")
    
    # Send notification if requested
    if args.notify:
        send_test_notification(reporter)
    
    # Return non-zero exit code if tests failed
    if results["overall_status"] == "FAILED":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
