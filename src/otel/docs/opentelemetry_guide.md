# OpenTelemetry Implementation Guide for Numeo Agents Service

## Table of Contents

1. [Introduction](#introduction)
2. [Traces](#traces)
    - [Span Structure](#span-structure)
    - [Span Attributes](#span-attributes)
    - [Span Events](#span-events)
3. [Metrics](#metrics)
    - [Workflow Metrics](#workflow-metrics)
    - [Agent Metrics](#agent-metrics)
    - [Business Metrics](#business-metrics)
    - [Message Metrics](#message-metrics)
4. [Error Handling](#error-handling)
    - [Capturing Exceptions](#capturing-exceptions)
    - [Error Metrics](#error-metrics)
    - [Error Attribution](#error-attribution)
5. [Best Practices](#best-practices)
6. [Examples](#examples)

## Introduction

This document provides a comprehensive guide to the OpenTelemetry implementation in the Numeo Agents Service. OpenTelemetry is used to instrument, generate, collect, and export telemetry data (metrics, logs, and traces) to help analyze the service's performance and behavior.

The Agents Service uses OpenTelemetry for:

-   Tracing request flows through the system
-   Measuring performance of different components
-   Monitoring error rates and types
-   Capturing business metrics for operational insights

## Traces

Traces provide a way to track the flow of requests through the distributed system, showing the relationships between operations and their timing.

### Span Structure

The Agents Service implements a hierarchical span structure:

```
LoadReplyWorkflow
├── Conversation History Retrieval
├── Orchestrator Agent Run
│   └── Agent Execution
├── Sub-Agent Invocations
│   ├── Rate Negotiator Agent
│   ├── Info Master Agent
│   ├── Warnings AI Agent
│   └── Load Scan Agent
└── Message Processing
```

Each span represents a unit of work and has a start time, end time, and set of attributes.

### Span Attributes

Standard attributes used across spans:

| Attribute           | Description                        | Example           |
| ------------------- | ---------------------------------- | ----------------- |
| `thread_id`         | Conversation thread identifier     | `"thread_123"`    |
| `load_id`           | Load identifier                    | `"load_456"`      |
| `application_name`  | Name of the calling application    | `"control-panel"` |
| `email_id`          | Email identifier                   | `"email_789"`     |
| `agent_type`        | Type of agent being executed       | `"orchestrator"`  |
| `has_truck_context` | Whether truck context is available | `true`            |
| `has_load_context`  | Whether load context is available  | `true`            |
| `has_company_info`  | Whether company info is available  | `true`            |
| `success`           | Whether the operation succeeded    | `true`            |
| `error`             | Error message if operation failed  | `"API timeout"`   |

### Span Events

Events are used to mark important points within a span:

```python
span.add_event("agent_decision", {"decision": "rate_negotiation", "confidence": 0.95})
span.add_event("api_request_start", {"endpoint": "/v1/trucks/loads/reply-status"})
span.add_event("api_request_complete", {"status_code": 200})
```

## Metrics

Metrics provide quantitative data about the system's performance and behavior.

### Workflow Metrics

| Metric                 | Type      | Description                            | Labels                                                            |
| ---------------------- | --------- | -------------------------------------- | ----------------------------------------------------------------- |
| `workflow.duration.ms` | Histogram | Total workflow execution time          | `workflow_type`, `thread_id`, `load_id`, `application`, `success` |
| `workflow.errors`      | Counter   | Number of errors in workflow execution | `error_type`, `thread_id`, `application`                          |

### Agent Metrics

| Metric              | Type      | Description                 | Labels                                              |
| ------------------- | --------- | --------------------------- | --------------------------------------------------- |
| `agent.invocations` | Counter   | Number of agent invocations | `agent_type`, `thread_id`, `application`            |
| `agent.duration.ms` | Histogram | Duration of agent execution | `agent_type`, `thread_id`, `load_id`, `application` |

### Business Metrics

| Metric                     | Type    | Description                      | Labels                                                 |
| -------------------------- | ------- | -------------------------------- | ------------------------------------------------------ |
| `business.load_replies`    | Counter | Number of load replies processed | `application`, `has_truck_context`, `has_load_context` |
| `operation.warnings.count` | Counter | Number of warning operations     | `operation`, `success`, `has_warnings`                 |
| `operation.info.count`     | Counter | Number of info operations        | `operation`, `success`                                 |
| `operation.rate.count`     | Counter | Number of rate operations        | `operation`, `success`                                 |

### Message Metrics

| Metric               | Type      | Description                | Labels                      |
| -------------------- | --------- | -------------------------- | --------------------------- |
| `message.size.bytes` | Histogram | Size of messages processed | `message_type`, `thread_id` |

## Error Handling

Error handling is a critical part of the observability implementation. The Agents Service captures errors at multiple levels.

### Capturing Exceptions

Exceptions are captured and recorded in spans:

```python
try:
    result = process_data(input_data)
    span.set_attribute("success", True)
except Exception as e:
    span.set_attribute("success", False)
    span.set_attribute("error", str(e))
    span.record_exception(e)
    record_error("process_data", thread_id, application_name)
```

### Error Metrics

Errors are tracked using dedicated metrics:

```python
error_counter = meter.create_counter(
    "workflow.errors",
    description="Number of errors encountered during workflow execution",
    unit="1"
)

def record_error(error_type: str, thread_id: str, application: str):
    error_counter.add(
        1,
        {
            "error_type": error_type,
            "thread_id": thread_id,
            "application": application
        }
    )
```

### Error Attribution

Errors are attributed to specific components using the `error_type` label:

-   `process_message`: Errors in the main message processing workflow
-   `rate_negotiator`: Errors in the rate negotiation agent
-   `info_master`: Errors in the company info agent
-   `warnings_ai`: Errors in the warnings AI agent
-   `load_scan`: Errors in the load scanning agent
-   `api_request`: Errors in API requests

## Best Practices

1. **Consistent Naming**: Use consistent naming conventions for spans and metrics
2. **Appropriate Granularity**: Create spans for operations that are meaningful for debugging
3. **Contextual Attributes**: Include relevant context in span attributes
4. **Error Handling**: Always record exceptions in spans and update metrics
5. **Timing Accuracy**: Use the same time source for start and end times

## Examples

### Tracing a Complete Workflow

```python
with tracer.start_as_current_span("LoadReplyWorkflow") as span:
    start_time = time.time()

    # Set span attributes for context
    span.set_attribute("thread_id", thread_id)
    span.set_attribute("load_id", load_id)
    span.set_attribute("application_name", application_name)

    try:
        # Process the message
        result = process_message(message_data)
        span.set_attribute("success", True)

        # Record workflow duration metrics
        workflow_duration_ms = (time.time() - start_time) * 1000
        record_workflow_duration(workflow_duration_ms, {
            "workflow_type": "load_reply",
            "thread_id": thread_id,
            "load_id": load_id,
            "application": application_name,
            "success": True
        })

        return result
    except Exception as e:
        # Record error in span
        span.set_attribute("success", False)
        span.set_attribute("error", str(e))
        span.record_exception(e)

        # Record error metrics
        record_error("process_message", thread_id, application_name)

        # Record workflow duration with failure
        workflow_duration_ms = (time.time() - start_time) * 1000
        record_workflow_duration(workflow_duration_ms, {
            "workflow_type": "load_reply",
            "thread_id": thread_id,
            "load_id": load_id,
            "application": application_name,
            "success": False
        })

        # Re-raise or handle the exception
        raise
```

### Tracing Sub-Agent Execution

```python
def run_warnings_agent(req):
    with tracer.start_as_current_span("warnings_ai_agent") as span:
        start_time = time.time()
        span.set_attribute("agent_type", "warnings_ai")
        span.set_attribute("thread_id", req.get("thread_id", ""))
        span.set_attribute("load_id", req.get("load_id", ""))

        try:
            # Execute the agent
            result = original_run_warnings_agent(req)

            # Determine if warnings were found
            has_warnings = False
            if isinstance(result, str) and ("warning" in result.lower() or "restrict" in result.lower()):
                has_warnings = True
            span.set_attribute("has_warnings", has_warnings)

            # Record metrics
            duration_ms = (time.time() - start_time) * 1000
            record_warnings_operation("check_warnings", True, has_warnings)
            record_warnings_duration(duration_ms, "check_warnings", True)
            record_agent_duration("warnings_ai", duration_ms, {
                "thread_id": req.get("thread_id", ""),
                "load_id": req.get("load_id", ""),
                "application": req.get("application_name", ""),
                "has_warnings": has_warnings
            })

            return result
        except Exception as e:
            # Record error metrics
            duration_ms = (time.time() - start_time) * 1000
            record_warnings_operation("check_warnings", False)
            record_warnings_duration(duration_ms, "check_warnings", False)
            record_error("warnings_ai", req.get("thread_id", ""), req.get("application_name", ""))

            # Record exception in span
            span.set_attribute("success", False)
            span.set_attribute("error", str(e))
            span.record_exception(e)

            # Re-raise the exception
            raise
```

### Recording API Request Errors

```python
def call_api(endpoint, payload, thread_id, application_name):
    with tracer.start_as_current_span("api_request") as span:
        span.set_attribute("endpoint", endpoint)
        span.set_attribute("thread_id", thread_id)

        start_time = time.time()
        try:
            response = requests.post(endpoint, json=payload, timeout=10)
            response.raise_for_status()  # Raise exception for 4XX/5XX status codes

            # Record successful API request
            duration_ms = (time.time() - start_time) * 1000
            record_api_request(endpoint, "POST", "success")
            record_api_duration(duration_ms, endpoint, "POST", "success")

            return response.json()
        except requests.exceptions.Timeout:
            # Handle timeout specifically
            span.set_attribute("error", "API request timed out")
            span.record_exception(Exception("API request timed out"))

            # Record API timeout error
            record_api_error(endpoint, "timeout", "504")
            record_error("api_request", thread_id, application_name)

            raise
        except requests.exceptions.HTTPError as e:
            # Handle HTTP errors (4XX/5XX)
            status_code = str(e.response.status_code)
            span.set_attribute("error", f"HTTP error {status_code}")
            span.set_attribute("status_code", status_code)
            span.record_exception(e)

            # Record API HTTP error
            record_api_error(endpoint, "http_error", status_code)
            record_error("api_request", thread_id, application_name)

            raise
        except Exception as e:
            # Handle other exceptions
            span.set_attribute("error", str(e))
            span.record_exception(e)

            # Record general API error
            record_api_error(endpoint, "general_error", "500")
            record_error("api_request", thread_id, application_name)

            raise
```
