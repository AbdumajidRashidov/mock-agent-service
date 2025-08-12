#!/usr/bin/env python3
"""
Standalone CLI runner for load reply processor evaluation.

Automatically looks for test_cases.json in the same directory.

Usage:
    # Run all tests with summary report
    python run_eval.py
    
    # Run with detailed report
    python run_eval.py --detailed
    
    # Filter tests by category or ID
    python run_eval.py --filter basic
    
    # Save detailed results to JSON
    python run_eval.py --save-json report.json
    
    # Run quietly (only show final results)
    python run_eval.py --quiet
"""

import asyncio
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the necessary paths to Python path
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent  # Go to load_reply_processor_langgraph_based
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(current_dir))

# Import with try/except to handle both direct execution and module import
try:
    from eval_runner import EvalRunner
    from report_generator import ReportGenerator
except ImportError:
    from .eval_runner import EvalRunner
    from .report_generator import ReportGenerator


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run load reply processor evaluation suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_eval.py                           # Run all tests, summary report
    python run_eval.py --detailed                # Run all tests, detailed report
    python run_eval.py --filter basic_info       # Run only basic info tests
    python run_eval.py --filter cancellation     # Run only cancellation tests
    python run_eval.py --save-json results.json  # Save detailed results to JSON
    python run_eval.py --detailed --filter edge  # Detailed report for edge cases only
        """
    )

    parser.add_argument(
        "--filter",
        help="Filter tests by category or test ID (e.g., 'basic_info', 'cancellation', 'test_001')"
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed report with failure analysis"
    )
    parser.add_argument(
        "--save-json",
        metavar="FILENAME",
        help="Save detailed report to JSON file"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only show final results, suppress progress output"
    )

    args = parser.parse_args()

    # Default: use local test_cases.json in the same directory
    test_cases_path = Path(__file__).parent / "test_cases.json"
    
    if not args.quiet:
        print(f"🔍 Looking for test cases at: {test_cases_path}")
    
    runner = EvalRunner(test_cases_path=str(test_cases_path))

    try:
        if not args.quiet:
            print("🚀 Starting Load Reply Processor Evaluation")
            print("-" * 50)

        # Run evaluation
        report = await runner.run_evaluation(test_filter=args.filter)

        if not args.quiet:
            print("\n" + "="*50)
            print("📊 EVALUATION COMPLETE")
            print("="*50)

        # Print appropriate report
        if args.detailed:
            ReportGenerator.print_detailed_report(report)
        else:
            ReportGenerator.print_summary_report(report)

        # Save JSON report if requested
        if args.save_json:
            ReportGenerator.save_json_report(report, args.save_json)

        # Print final recommendation
        if not args.quiet:
            print(f"\n💡 Recommendation:")
            if report.success_rate >= 0.9:
                print("   ✅ System is performing well - ready for production use")
            else:
                print("   ❌ System needs improvement before production deployment")
                print("   📋 Review failed test cases and address issues")

        # Exit with appropriate code (0 = success, 1 = failure)
        exit_code = 0 if report.success_rate >= 0.9 else 1
        sys.exit(exit_code)

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("📁 Make sure test_cases.json exists in the tests/eval/ directory")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Evaluation failed with error: {e}")
        if not args.quiet:
            import traceback
            print("\n🐛 Full error traceback:")
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Set up asyncio event loop policy for Windows compatibility
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())
