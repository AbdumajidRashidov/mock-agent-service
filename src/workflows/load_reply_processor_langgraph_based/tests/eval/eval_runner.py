import json
import time
import os
import httpx
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add paths for imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# API configuration
TEST_CASES_API_URL = os.getenv('TEST_CASES_API_URL')
API_TIMEOUT = int(os.getenv('TEST_CASES_API_TIMEOUT', "30"))

try:
    from email_judge import EmailJudge
except ImportError:
    from .email_judge import EmailJudge

try:
    from field_extraction_judge import FieldExtractionJudge
except ImportError:
    from .field_extraction_judge import FieldExtractionJudge

# Import the main process_reply function
try:
    from main import process_reply
except ImportError:
    # Try different import paths
    try:
        from ...main import process_reply
    except ImportError:
        # Last resort - add more paths
        sys.path.insert(0, str(project_root.parent))
        from load_reply_processor_langgraph_based.main import process_reply


@dataclass
class TestResult:
    """Results from a single test case execution."""
    test_id: str
    category: str
    description: str
    passed: bool
    execution_time: float
    error: Optional[str] = None

    # Email comparison results
    email_comparison: Optional[Dict[str, Any]] = None

    # Field extraction results
    field_extraction_score: float = 0.0
    field_extraction_details: Dict[str, Any] = None

    # Performance metrics
    response_time: float = 0.0
    token_usage: Dict[str, int] = None

    # Actual vs expected outputs
    actual_output: Dict[str, Any] = None
    expected_output: Dict[str, Any] = None


@dataclass
class EvaluationReport:
    """Overall evaluation report."""
    total_tests: int
    passed_tests: int
    failed_tests: int
    success_rate: float

    # Category breakdown
    category_results: Dict[str, Dict[str, Any]]

    # Performance metrics
    avg_response_time: float
    total_execution_time: float

    # Test results
    test_results: List[TestResult]

    # Summary
    summary: str


class EvalRunner:
    """Main evaluation runner for load reply processor."""

    def __init__(self, test_cases_path: str = None, api_url: str = None):
        self.test_cases_path = test_cases_path  # Kept for backward compatibility
        self.api_url = api_url or TEST_CASES_API_URL
        self.email_judge = EmailJudge()
        self.field_judge = FieldExtractionJudge()

    async def load_test_cases(self) -> List[Dict[str, Any]]:
        """Load test cases from a JSON file or API endpoint.

        Priority:
        1. Load from file if test_cases_path is provided
        2. Fall back to API if file loading fails or no path provided

        Returns:
            List[Dict[str, Any]]: List of test cases

        Raises:
            RuntimeError: If unable to load test cases from either source
            ValueError: If the test cases format is invalid
        """
        # Try to load from file if path is provided
        if self.test_cases_path and os.path.exists(self.test_cases_path):
            try:
                with open(self.test_cases_path, 'r') as f:
                    data = json.load(f)

                # Check if the file has the expected structure
                if 'test_cases' in data:
                    test_cases = data['test_cases']
                else:
                    # If the file is just an array of test cases
                    test_cases = data if isinstance(data, list) else []

                if not isinstance(test_cases, list):
                    raise ValueError("Test cases must be a list")

                print(f"✅ Loaded {len(test_cases)} test cases from {self.test_cases_path}")
                return test_cases

            except json.JSONDecodeError as e:
                print(f"⚠️  Failed to parse JSON file: {e}. Falling back to API...")
            except Exception as e:
                print(f"⚠️  Error loading test cases from file: {e}. Falling back to API...")

        # Fall back to API if file loading fails or no path provided
        if not self.api_url:
            raise RuntimeError("No test cases file found and no API URL provided")

        try:
            print(f"🌐 Fetching test cases from API: {self.api_url}")
            async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
                response = await client.get(self.api_url)
                response.raise_for_status()
                data = response.json()

                # Handle different API response formats
                if isinstance(data.get('data'), dict) and 'test_cases' in data.get('data', {}):
                    test_cases = data['data']['test_cases']
                elif 'test_cases' in data:
                    test_cases = data['test_cases']
                elif isinstance(data, list):
                    test_cases = data
                else:
                    raise ValueError("Invalid API response format: could not find test cases")

                if not isinstance(test_cases, list):
                    raise ValueError("Test cases must be a list")

                print(f"✅ Loaded {len(test_cases)} test cases from API")
                return test_cases

        except Exception as e:
            raise RuntimeError(f"Failed to load test cases: {str(e)}")

    async def upload_test_cases(self, file_path: str) -> Dict[str, Any]:
        """Upload test cases to the Firestore agent config API.

        Args:
            file_path: Path to the JSON file containing test cases

        Returns:
            Dict[str, Any]: The API response data

        Raises:
            FileNotFoundError: If the specified file doesn't exist
            RuntimeError: If the upload fails
            ValueError: If the file is not valid JSON or has invalid format
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Test cases file not found: {file_path}")

        try:
            # Read and validate JSON file
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Extract test cases from the 'test_cases' key
            if not isinstance(data, dict) or 'test_cases' not in data:
                raise ValueError("Invalid test cases format: expected a JSON object with a 'test_cases' key")

            test_cases = data['test_cases']
            if not isinstance(test_cases, list):
                raise ValueError("Invalid test cases format: 'test_cases' should be a list")

            # Prepare the request payload
            payload = {
                'metadata': {
                    'test_cases': test_cases
                }
            }

            # Construct the upload URL
            upload_url = self.api_url

            async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
                response = await client.post(
                    upload_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()

                data = response.json()

                # Validate response structure
                if not isinstance(data, dict) or 'success' not in data:
                    raise ValueError("Invalid API response: missing 'success' key")

                return data

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON file: {str(e)}")
        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_detail += f" - {error_data.get('message', 'No details')}"
            except:
                error_detail += f" - {e.response.text}"
            raise RuntimeError(f"Failed to upload test cases: {error_detail}")
        except httpx.RequestError as e:
            raise RuntimeError(f"Request to upload test cases failed: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error while uploading test cases: {str(e)}")

    async def run_single_test(self, test_case: Dict[str, Any]) -> TestResult:
        """Run a single test case."""
        start_time = time.time()
        test_id = test_case['id']
        category = test_case['category']
        description = test_case['description']

        try:
            # Prepare test input
            input_data = test_case['input']
            expected_output = test_case['expected_output']

            # Mock response callback to capture output
            captured_output = {}

            async def mock_callback(response):
                captured_output.update(response)

            # Execute the load reply processor
            execution_start = time.time()

            await process_reply(
                company_details=input_data['company_details'],
                our_emails=input_data['our_emails'],
                truck=input_data['truck'],
                load=input_data['load'],
                emails=input_data['emails'],
                response_callback=mock_callback,
            )

            execution_time = time.time() - execution_start

            # Compare field extractions using AI judge
            field_comparison_result = self.field_judge.compare_field_extractions(
                expected=expected_output,
                actual=captured_output,
                context={
                    'description': description,
                    'category': category,
                    'test_id': test_id
                }
            )

            # Convert to dict and create compatibility structure
            field_comparison = field_comparison_result.dict()
            field_comparison['score'] = field_comparison['overall_score'] / 10.0  # Convert to 0-1 scale

            # Compare emails using AI judge
            expected_email = expected_output.get('email_to_send', '')
            actual_email = captured_output.get('email_to_send', '')

            email_comparison = None
            if expected_email and actual_email:
                email_comparison_result = self.email_judge.compare_emails(
                    expected=expected_email,
                    actual=actual_email,
                    context={
                        'description': description,
                        'category': category,
                        'test_id': test_id
                    }
                )
                # Convert Pydantic model to dict
                email_comparison = email_comparison_result.dict()

            # Determine if test passed
            field_score = field_comparison['score']
            email_score = email_comparison['overall_score'] / 10.0 if email_comparison else 1.0

            # Weight the scores (fields 60%, email 40%)
            overall_score = (field_score * 0.6) + (email_score * 0.4)
            passed = overall_score >= 0.7  # 70% threshold

            total_time = time.time() - start_time

            return TestResult(
                test_id=test_id,
                category=category,
                description=description,
                passed=passed,
                execution_time=total_time,
                email_comparison=email_comparison,
                field_extraction_score=field_score,
                field_extraction_details=field_comparison,
                response_time=execution_time,
                actual_output=captured_output,
                expected_output=expected_output
            )

        except Exception as e:
            total_time = time.time() - start_time
            return TestResult(
                test_id=test_id,
                category=category,
                description=description,
                passed=False,
                execution_time=total_time,
                error=str(e),
                actual_output={},
                expected_output=expected_output
            )

    async def run_evaluation(self, test_filter: Optional[str] = None) -> EvaluationReport:
        """Run the complete evaluation suite."""
        print("Loading test cases...")
        test_cases = await self.load_test_cases()

        # Filter test cases if specified
        if test_filter:
            test_cases = [tc for tc in test_cases if test_filter in tc['category'] or test_filter in tc['id']]

        print(f"Running {len(test_cases)} test cases...")

        start_time = time.time()
        test_results = []

        for i, test_case in enumerate(test_cases, 1):
            print(f"Running test {i}/{len(test_cases)}: {test_case['id']}")
            result = await self.run_single_test(test_case)
            test_results.append(result)

            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"  {status} - {result.description} ({result.execution_time:.2f}s)")

            if result.error:
                print(f"    Error: {result.error}")

        total_time = time.time() - start_time

        # Calculate statistics
        passed_tests = sum(1 for r in test_results if r.passed)
        failed_tests = len(test_results) - passed_tests
        success_rate = passed_tests / len(test_results) if test_results else 0

        # Category breakdown
        categories = {}
        for result in test_results:
            if result.category not in categories:
                categories[result.category] = {'total': 0, 'passed': 0, 'failed': 0}

            categories[result.category]['total'] += 1
            if result.passed:
                categories[result.category]['passed'] += 1
            else:
                categories[result.category]['failed'] += 1

        # Add success rates to categories
        for category in categories:
            total = categories[category]['total']
            passed = categories[category]['passed']
            categories[category]['success_rate'] = passed / total if total > 0 else 0

        # Average response time
        response_times = [r.response_time for r in test_results if r.response_time > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        # Generate summary
        summary_lines = [
            f"Evaluation completed in {total_time:.2f}s",
            f"Success Rate: {success_rate:.1%} ({passed_tests}/{len(test_results)})",
            f"Average Response Time: {avg_response_time:.2f}s"
        ]

        # Check category thresholds
        failing_categories = []
        for category, stats in categories.items():
            if stats['success_rate'] < 0.9:  # 90% threshold
                failing_categories.append(f"{category}: {stats['success_rate']:.1%}")

        if failing_categories:
            summary_lines.append(f"Categories below 90% threshold: {', '.join(failing_categories)}")

        return EvaluationReport(
            total_tests=len(test_results),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            success_rate=success_rate,
            category_results=categories,
            avg_response_time=avg_response_time,
            total_execution_time=total_time,
            test_results=test_results,
            summary='\n'.join(summary_lines)
        )
