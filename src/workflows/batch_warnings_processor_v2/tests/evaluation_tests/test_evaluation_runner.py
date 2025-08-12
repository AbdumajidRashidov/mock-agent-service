"""
Real AI Evaluation Test Runner for Load Analysis System.
Uses actual Azure OpenAI API calls instead of mocks.
"""

import pytest
import json
import os
import sys
from pathlib import Path
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# Handle imports based on execution context
try:
    from .evaluation_engine import EvaluationEngine
except ImportError:
    try:
        from workflows.batch_warnings_processor_v2.evaluation_tests.evaluation_engine import EvaluationEngine
    except ImportError:
        current_file = Path(__file__).resolve()
        batch_processor_dir = current_file.parent.parent
        sys.path.insert(0, str(batch_processor_dir))
        from evaluation_tests.evaluation_engine import EvaluationEngine


def load_json_test_cases():
    """Load test cases from JSON file."""
    test_data_path = Path(__file__).parent.parent / "test_data" / "evaluation_cases.json"

    try:
        with open(test_data_path, 'r') as f:
            data = json.load(f)

        test_cases = data.get('test_cases', [])
        print(f"\nLoaded {len(test_cases)} JSON test cases")

        return test_cases
    except Exception as e:
        print(f"Error loading test cases: {e}")
        return []


def check_ai_credentials():
    """Check if AI credentials are available."""
    required_env_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT_NAME"
    ]

    missing_vars = []
    for var in required_env_vars:

        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"\n❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print(f"\nSet these variables to use real AI testing.")
        return False

    print(f"\n✅ All AI credentials found")
    return True

# Load test cases at module level
JSON_TEST_CASES = load_json_test_cases()
AI_CREDENTIALS_AVAILABLE = check_ai_credentials()

class TestRealAIEvaluationCases:
    """Test runner that uses real AI for evaluation."""

    @pytest.fixture
    def real_azure_client(self):
        """Create real Azure OpenAI client."""
        if not AI_CREDENTIALS_AVAILABLE:
            pytest.skip("AI credentials not available")

        return AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        )

    @pytest.fixture
    def evaluation_engine(self, real_azure_client):
        """Create evaluation engine with real AI client."""
        test_root = Path(__file__).parent.parent
        test_data_path = test_root / "test_data" / "evaluation_cases.json"
        return EvaluationEngine(str(test_data_path), real_azure_client)

    @pytest.mark.evaluation
    @pytest.mark.parametrize("test_case", JSON_TEST_CASES, ids=[tc['id'] for tc in JSON_TEST_CASES])
    @pytest.mark.asyncio
    async def test_real_ai_json_case(self, test_case, evaluation_engine):
        """Run individual JSON test case with real AI."""

        print(f"\n🤖 Testing with Real AI: {test_case['id']} - {test_case['name']}")
        print(f"   Load: {test_case['load']['comments'][:100]}...")

        # Run the evaluation with real AI
        result = await evaluation_engine.evaluate_single_case(test_case)

        # Validate basic execution
        assert result is not None
        assert result.test_case_id == test_case['id']
        assert result.test_case_name == test_case['name']
        assert result.execution_time_ms > 0

        # Print detailed results
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"\n{status}: {result.test_case_id}")
        print(f"   Expected: has_issues={test_case['expected_outcome'].get('has_issues', False)}")
        print(f"   Actual: has_issues={result.actual_has_issues}")
        print(f"   Expected warnings: {test_case['expected_outcome'].get('warning_count', 0)}")
        print(f"   Actual warnings: {result.actual_warning_count}")
        print(f"   Execution time: {result.execution_time_ms:.1f}ms")

        if result.actual_warnings:
            print(f"   AI-generated warnings:")
            for i, warning in enumerate(result.actual_warnings, 1):
                print(f"     {i}. {warning}")

        if not result.passed:
            print(f"   ❌ Evaluation failed:")
            if result.missing_keywords:
                print(f"      Missing keywords: {result.missing_keywords}")
            if result.unexpected_warnings:
                print(f"      Unexpected warnings: {result.unexpected_warnings}")

        # Store result for summary
        if not hasattr(self, '_results'):
            self._results = []
        self._results.append(result)
