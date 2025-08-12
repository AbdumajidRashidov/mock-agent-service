"""
Test runner script with various execution modes.
Simplified version without webhook integration.
"""

import subprocess
import sys
import argparse
import os
from pathlib import Path

# Define the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

def run_command_from_dir(cmd, description, working_dir):
    """Run command from specific directory and handle errors."""
    print(f"\n{'='*50}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"Working Directory: {working_dir}")
    print(f"{'='*50}")

    result = subprocess.run(cmd, capture_output=False, cwd=working_dir)

    if result.returncode != 0:
        print(f"ERROR: {description} failed with code {result.returncode}")
        return False

    print(f"SUCCESS: {description} completed")
    return True


def run_command(cmd, description):
    """Run command and handle errors."""
    return run_command_from_dir(cmd, description, PROJECT_ROOT)

def run_unit_tests():
    """Run only unit tests."""
    test_root = PROJECT_ROOT / "workflows" / "batch_warnings_processor_v2"
    cmd = [
        "python", "-m", "pytest",
        "tests/unit_tests/",
        "-v",
        "--tb=short"
    ]
    return run_command_from_dir(cmd, "Unit Tests", test_root)

def run_evaluation_tests():
    """Run evaluation tests against real-world test cases."""
    test_root = PROJECT_ROOT / "workflows" / "batch_warnings_processor_v2"
    cmd = [
        "python", "-m", "pytest",
        "tests/evaluation_tests/",
        "-v",
        "--tb=short",
        "-m", "evaluation"
    ]
    return run_command_from_dir(cmd, "Evaluation Tests", test_root)

def run_all_tests():
    """Run complete test suite."""
    test_root = PROJECT_ROOT / "workflows" / "batch_warnings_processor_v2"

    # Ensure the reports directory exists (relative to test_root)
    reports_dir = test_root / "tests" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # The JSON report path as configured in pytest.ini
    json_report_path = test_root / "tests" / "reports" / "test_results.json"

    # Run tests from the batch_warnings_processor_v2 directory
    cmd = [
        "python", "-m", "pytest",
        "tests/",
    ]

    # Run the tests from the correct working directory
    print(f"\n{'='*50}")
    print(f"Running: Complete Test Suite")
    print(f"Command: {' '.join(cmd)}")
    print(f"Working Directory: {test_root}")
    print(f"Using pytest.ini configuration")
    print(f"{'='*50}")

    result = subprocess.run(cmd, capture_output=False, cwd=test_root)
    success = result.returncode == 0

    if not success:
        print(f"ERROR: Complete Test Suite failed with code {result.returncode}")
    else:
        print(f"SUCCESS: Complete Test Suite completed")

        # Verify the JSON report was created where pytest.ini expects it
        if json_report_path.exists():
            print(f"✓ JSON report successfully created at: {json_report_path}")
        else:
            print(f"Warning: JSON report not found at expected location: {json_report_path}")

    return success

def setup_test_environment():
    """Setup test environment and dependencies."""
    print("Setting up test environment...")

    # Create necessary directories
    test_root = PROJECT_ROOT / "workflows" / "batch_warnings_processor_v2"
    reports_dir = test_root / "tests" / "reports"
    test_data_dir = test_root / "tests" / "test_data"

    reports_dir.mkdir(parents=True, exist_ok=True)
    test_data_dir.mkdir(parents=True, exist_ok=True)

    # Check if requirements.txt exists in the tests directory
    test_requirements = test_root / "tests" / "requirements.txt"

    if test_requirements.exists():
        print(f"Installing test dependencies from {test_requirements}")
        deps_cmd = [
            "pip", "install", "-r", str(test_requirements)
        ]

        if not run_command(deps_cmd, "Install Test Dependencies"):
            return False
    else:
        print(f"No test requirements file found at {test_requirements}")
        print("Installing basic test dependencies...")
        basic_deps_cmd = [
            "pip", "install",
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "pytest-cov>=4.0.0",
            "pytest-json-report>=1.5.0"
        ]

        if not run_command(basic_deps_cmd, "Install Basic Test Dependencies"):
            return False

    print("Test environment setup complete")
    return True


def check_dependencies():
    """Check if required test dependencies are installed."""
    import pkg_resources

    required_packages = [
        'pytest>=7.0.0',
        'pytest-asyncio>=0.21.0',
        'pytest-mock>=3.10.0',
        'pytest-cov>=4.0.0',
        'pytest-json-report>=1.5.0'
    ]

    missing_packages = []

    for package_spec in required_packages:
        try:
            pkg_resources.require(package_spec)
        except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict):
            missing_packages.append(package_spec)

    if missing_packages:
        print(f"Missing required packages: {', '.join(missing_packages)}")
        print("Run 'python scripts/run_tests.py setup' to install dependencies")
        return False

    return True


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Batch Warnings Processor V2 Test Runner")

    parser.add_argument(
        "mode",
        choices=["unit", "evaluation", "all", "setup"],
        help="Test execution mode"
    )

    parser.add_argument(
        "--test",
        help="Specific test file or function to run"
    )

    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check if all required dependencies are installed"
    )

    args = parser.parse_args()

    # Check dependencies if requested
    if args.check_deps:
        if check_dependencies():
            print("✓ All required dependencies are installed")
            sys.exit(0)
        else:
            sys.exit(1)

    # Setup environment if requested
    if args.mode == "setup":
        success = setup_test_environment()
        sys.exit(0 if success else 1)

    # Check dependencies before running tests
    if not check_dependencies():
        print("Some dependencies are missing. Run setup first.")
        sys.exit(1)

    # Run specific test if provided
    if args.test:
        success = run_specific_test(args.test)
        sys.exit(0 if success else 1)

    # Run tests based on mode
    success = True

    if args.mode == "unit":
        success = run_unit_tests()
    elif args.mode == "evaluation":
        success = run_evaluation_tests()
    elif args.mode == "all":
        success = run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
