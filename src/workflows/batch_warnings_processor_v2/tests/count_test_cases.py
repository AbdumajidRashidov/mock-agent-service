#!/usr/bin/env python3
"""
Script to count and analyze test cases in evaluation_cases.json
"""

import json
from pathlib import Path

def count_test_cases():
    """Count and analyze test cases in JSON file."""
    test_data_path = Path(__file__).parent / "test_data" / "evaluation_cases.json"

    try:
        with open(test_data_path, 'r') as f:
            data = json.load(f)

        test_cases = data.get('test_cases', [])
        total_cases = len(test_cases)

        print(f"Total Test Cases: {total_cases}")

    except Exception as e:
        print(f"Error loading test cases: {e}")
        return 0

if __name__ == "__main__":
    count_test_cases()
