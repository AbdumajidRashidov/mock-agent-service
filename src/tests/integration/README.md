# AI Agent Integration Tests

This directory contains integration tests for the AI agents in the load reply processor workflow. The tests verify that the agents function correctly both individually and as part of a complete conversation flow.

## Test Structure

The test suite is organized into several key files:

### Core Test Files

-   **test_agent_conversations.py**: Tests the conversation flow with different types of emails, verifying that the appropriate agent is triggered based on the email content.
-   **test_agent_functions.py**: Direct tests for the core functionality of AI agents, focusing on individual functions.
-   **data.py**: Contains helper functions and test data for creating protobuf messages used in tests.

### Test Data

The `data.py` file provides:

1. **Helper Functions**:

    - `create_email()`: Creates Email protobuf messages
    - `create_truck()`: Creates Truck protobuf messages with customizable parameters
    - `create_load()`: Creates Load protobuf messages with customizable parameters
    - `create_company_details()`: Creates CompanyDetails protobuf messages

2. **Test Emails**:
    - Standard test emails for different scenarios
    - Specialized test emails for specific agent tests

## Agents Tested

### 1. Info Master

**Purpose**: Responds to inquiries about company information.

**Test Cases**:

-   Answering questions about MC numbers
-   Providing company details
-   Handling general inquiries

### 2. Load Scan

**Purpose**: Extracts structured data from unstructured text in emails.

**Test Cases**:

-   Extracting load details (rate, commodity, weight, equipment, locations)
-   Updating load reply status in the database
-   Handling different formats of load information

### 3. Warnings AI

**Purpose**: Identifies warnings based on truck attributes and load details.

**Test Cases**:

-   Detecting hazmat restrictions
-   Identifying incompatible cargo types
-   Checking for truck capability limitations
-   Updating load warnings in the database

### 4. Rate Negotiator

**Purpose**: Calculates rates based on thresholds and applies rounding rules.

**Test Cases**:

-   Calculating counter-offers based on configurable thresholds
-   Applying rounding rules to rates
-   Generating appropriate negotiation responses
-   Sending draft responses

## Test Scenarios

### Individual Agent Tests

Each agent has dedicated tests that verify its specific functionality:

```python
# Example: Testing the warnings_ai agent
test_warnings_ai_agent(in_memory_conversation, mock_send_reply, mock_update_load_reply_status, mock_upsert_load_warnings, mock_send_draft)
```

### Full Conversation Flow

The `test_full_conversation_flow` test verifies the entire conversation flow with multiple emails triggering different agents in sequence:

1. Starting with an info master inquiry
2. Continuing with load details for load scan
3. Processing hazmat load information for warnings
4. Finishing with rate negotiation

## Mock Functions

To prevent actual API calls during testing, the following functions are mocked:

-   `send_reply`: Mocks sending replies to users
-   `update_load_reply_status`: Mocks updating load status in the database
-   `upsert_load_warnings`: Mocks saving warnings to the database
-   `send_draft`: Mocks sending draft responses

## Running Tests

Tests can be run using pytest:

```bash
# Run all tests in the integration directory
python -m pytest src/tests/integration/

# Run a specific test file
python -m pytest src/tests/integration/test_agent_conversations.py

# Run a specific test function
python -m pytest src/tests/integration/test_agent_conversations.py::test_warnings_ai_agent
```

## File Organization

### Current Test Files

After cleanup and optimization, the test suite now consists of these key files:

-   **test_agent_conversations.py**: Main test file for agent conversations and workflow testing
-   **test_agent_functions_fixed.py**: Tests for individual agent functions with proper mocking
-   **test_load_scan.py**: Specific tests for the load_scan agent functionality
-   **test_rate_negotiator.py**: Specific tests for the rate_negotiator agent functionality
-   **test_warnings_ai.py**: Specific tests for the warnings_ai agent functionality
-   **conftest.py**: Shared fixtures and test configuration
-   **data.py**: Test data and helper functions

### Files Removed During Cleanup

The following files were removed as part of the test suite cleanup:

-   **test_agent_functions.py**: Replaced by test_agent_functions_fixed.py
-   **test_agents.py**: Redundant with individual agent test files
-   **test_all_agents.py**: Just a runner that imported tests from other files
-   **test_load_scan_fix.py**: Utility script to fix test_load_scan.py
-   **test_load_reply_flow.py**: Contained failing tests covered by other files
-   **test_load_reply_flow_fix.py**: Utility script to fix test_load_reply_flow.py
-   **test_load_reply_flow_mocks.py**: Had errors due to outdated mocks
-   **test_working_agents.py**: Functionality covered by test_agent_functions_fixed.py
-   **utils/**: Folder with unused mock utilities

## Best Practices

1. **Use Predefined Test Emails**: The `data.py` file contains predefined test emails for each agent. Use these instead of creating new ones in test files.

2. **Mock External Dependencies**: Always mock external dependencies like API calls to ensure tests are isolated and reliable.

3. **Clear Conversation History**: Always clear the conversation history before each test to ensure test isolation.

4. **Verify Agent Responses**: Check that the agent responses contain the expected information and that the appropriate functions were called.

5. **Use Descriptive Test Names**: Name tests descriptively to make it clear what functionality they're testing.
