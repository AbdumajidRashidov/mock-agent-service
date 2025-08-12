#!/bin/bash

# Schedule weekly integration tests for the Load Reply Processor
# This script sets up a cron job to run the integration tests every week

# Get the absolute path to the test runner script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_RUNNER="${SCRIPT_DIR}/run_weekly_tests.py"
REPORT_DIR="${SCRIPT_DIR}/reports"

# Make the test runner executable
chmod +x "$TEST_RUNNER"

# Create the reports directory if it doesn't exist
mkdir -p "$REPORT_DIR"

# Set up the cron job to run every Sunday at 2:00 AM
(crontab -l 2>/dev/null; echo "0 2 * * 0 cd ${SCRIPT_DIR} && python3 ${TEST_RUNNER} --report-path ${REPORT_DIR} --notify") | crontab -

echo "Weekly integration tests scheduled to run every Sunday at 2:00 AM"
echo "Reports will be saved to: ${REPORT_DIR}"

# Show the current crontab to verify
echo "\nCurrent crontab:"
crontab -l
