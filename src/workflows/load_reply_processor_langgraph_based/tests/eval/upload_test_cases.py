#!/usr/bin/env python3
"""
Script to upload test cases to the Firestore agent config API.

Example usage:
    python upload_test_cases.py test_cases.json
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path to import EvalRunner
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from eval_runner import EvalRunner

# Default configuration
DEFAULT_API_URL = os.getenv("TEST_CASES_API_URL")

async def upload_test_cases(api_url: str, file_path: str) -> Dict[str, Any]:
    """Upload test cases to the Firestore agent config API.
    
    Args:
        api_url: Base URL of the agent config API
        file_path: Path to the JSON file containing test cases
        
    Returns:
        Dict[str, Any]: The API response data
    """
    print(f"📤 Uploading test cases to {api_url}...")
    runner = EvalRunner(api_url=api_url)
    return await runner.upload_test_cases(file_path=file_path)


def main():
    parser = argparse.ArgumentParser(description="Upload test cases to Firestore agent config API")
    parser.add_argument(
        "file",
        help="Path to the JSON file containing test cases"
    )
    parser.add_argument(
        "--api-url",
        default=os.getenv("TEST_CASES_API_URL"),
        required=not bool(os.getenv("TEST_CASES_API_URL")),
        help="Base URL of the agent config API (can also be set via TEST_CASES_API_URL environment variable)"
    )
    
    args = parser.parse_args()

    # Convert relative paths to absolute
    file_path = os.path.abspath(args.file)

    try:
        # Run the async function
        result = asyncio.run(upload_test_cases(args.api_url, file_path))
        print(f"✅ Successfully uploaded test cases")
        print(f"Response: {result}")
        return 0
    except Exception as e:
        print(f"❌ Error uploading test cases: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
