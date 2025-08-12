# Sub-Agents OpenTelemetry Instrumentation Guide

## Overview

This document explains how we've instrumented the sub-agents in the Numeo Agents Service with OpenTelemetry tracing and metrics. This instrumentation provides comprehensive observability into the behavior and performance of each sub-agent, allowing for better monitoring, debugging, and optimization.

We have instrumented the following sub-agents:

1. **Info Master**: Handles company information queries
2. **Load Scan**: Extracts structured data from load details
3. **Rate Negotiator**: Handles rate negotiations and pricing inquiries
4. **Warnings AI**: Analyzes load information for compliance issues and restrictions

## Instrumentation Pattern

We follow a consistent pattern for instrumenting sub-agents:

1. **Span Hierarchy**: Create a hierarchical structure of spans that represent the flow of operations
2. **Contextual Attributes**: Add relevant attributes to spans for better correlation and filtering
3. **Metrics Recording**: Capture performance metrics at key points in the execution flow
4. **Error Handling**: Properly record errors and exceptions with detailed context

## Examples of Instrumented Sub-Agents

### Info Master Sub-Agent

The `info_master.py` sub-agent has been instrumented with OpenTelemetry to provide detailed tracing and metrics. Here's a breakdown of the implementation:

### 1. Imports and Setup

```python
# Import OpenTelemetry
from opentelemetry import trace
from otel.metrics import (
    record_info_operation,
    record_info_duration,
    record_agent_duration,
    record_error,
    record_api_request,
    record_api_duration,
    record_api_error
)

# Initialize tracer
tracer = trace.get_tracer("info-master-tracer")
```

### 2. Main Function Instrumentation

The main `run_info_master` function is wrapped with a span that captures the overall execution:

```python
async def run_info_master(ctx: RunContextWrapper[Any], args: str):
    # Start timing for metrics
    start_time = time.time()

    # Parse the request and extract context
    parsed = AgentsReq.model_validate_json(args)
    # ... extract other context ...

    # Start the OpenTelemetry span
    with tracer.start_as_current_span("info_master_processing") as span:
        # Set span attributes for better context
        span.set_attribute("agent_type", "info_master")
        span.set_attribute("thread_id", thread_id)
        # ... other attributes ...

        # Record agent invocation in metrics
        record_info_operation("company_info", True)

        # ... agent logic ...
```

### 3. API Call Instrumentation

API calls to external services (like Azure OpenAI) are instrumented with nested spans:

```python
# Create a nested span for the API call
with tracer.start_as_current_span("azure_openai_api_call") as api_span:
    api_span.set_attribute("model", os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"))
    # ... other attributes ...

    # Record API request metrics
    api_start_time = time.time()
    record_api_request("azure_openai", "POST", "pending")

    # Make the API call
    response = await azure_client.chat.completions.create(...)

    # Calculate API call duration and record metrics
    api_duration_ms = (time.time() - api_start_time) * 1000
    record_api_duration(api_duration_ms, "azure_openai", "POST", "success")
    record_api_request("azure_openai", "POST", "success")
```

### 4. Error Handling

Errors are captured and recorded with detailed context:

```python
except Exception as e:
    # Record error metrics
    error_message = str(e)
    error_type = type(e).__name__

    # Set error attributes on the current span
    current_span = trace.get_current_span()
    current_span.set_attribute("error", True)
    current_span.set_attribute("error.type", error_type)
    current_span.set_attribute("error.message", error_message)

    # Record error metrics
    record_error("info_master", thread_id, application_name)
    record_info_operation("company_info", False)

    # Calculate duration for failed operation
    duration_ms = (time.time() - start_time) * 1000
    record_info_duration(duration_ms, "company_info", False)
```

### 5. Duration Metrics

Duration metrics are recorded at the end of processing:

```python
# Calculate total duration and record metrics
duration_ms = (time.time() - start_time) * 1000
record_info_duration(duration_ms, "company_info", True)
record_agent_duration("info_master", duration_ms, {
    "thread_id": thread_id,
    "load_id": load_id,
    "application": application_name,
    "found": result.get("found", False)
})
```

## Metrics Collected

The following metrics are collected for sub-agents:

1. **Agent Invocation Count**: Number of times each sub-agent is invoked
2. **Agent Duration**: Time taken for each sub-agent execution
3. **Operation Success/Failure**: Success and failure counts for specific operations
4. **API Request Metrics**: Counts and durations for external API calls
5. **Error Counts**: Number of errors by type and agent

## Traces and Spans

### Info Master Sub-Agent

The following spans are created for the info_master sub-agent:

1. `info_master_processing`: Overall processing of the request
2. `azure_openai_api_call`: API call to Azure OpenAI
3. `send_reply`: Sending a reply when information is found

### Load Scan Sub-Agent

The following spans are created for the load_scan sub-agent:

1. `load_scan_processing`: Overall processing of the request
2. `azure_openai_api_call`: API call to Azure OpenAI
3. `update_load_reply_status`: Updating the load reply status in the database

### Rate Negotiator Sub-Agent

The following spans are created for the rate_negotiator sub-agent:

1. `rate_negotiator_processing`: Overall processing of the request
2. `db_operations`: Database operations for conversation history
3. `openai_agent_run`: OpenAI API call for rate negotiation
4. `process_result`: Processing the agent response
5. `send_draft`: Sending draft email
6. `save_assistant_message`: Saving assistant message to database
7. `save_handoff_message`: Saving handoff message to database

### Warnings AI Sub-Agent

The following spans are created for the warnings_ai sub-agent:

1. `warnings_ai_processing`: Overall processing of the request
2. `azure_openai_api_call`: API call to Azure OpenAI for analyzing load information
3. `upsert_load_warnings`: Database operations for saving warnings

Each span includes relevant attributes such as:

-   `thread_id`: ID of the conversation thread
-   `load_id`: ID of the load being processed
-   `agent_type`: Type of agent (e.g., "info_master" or "load_scan")
-   `query_length`: Length of the user query
-   `response_length`: Length of the response
-   `success`: Whether the operation was successful
-   `error`: Error information if applicable

### Load Scan Sub-Agent

The `load_scan.py` sub-agent has also been instrumented with OpenTelemetry. Here's a breakdown of its implementation:

#### 1. Imports and Setup

```python
# Import OpenTelemetry
from opentelemetry import trace
from otel.metrics import (
    record_agent_duration,
    record_error,
    record_api_request,
    record_api_duration,
    record_operation_duration,
    add_operation_count
)

# Initialize tracer
tracer = trace.get_tracer("load-scan-tracer")
```

#### 2. Main Function Instrumentation

```python
async def run_load_scan(ctx: RunContextWrapper[Any], args: str):
    # Start timing for metrics
    start_time = time.time()

    # Parse the request and extract context
    query = AgentsReq.model_validate_json(args).query
    application_name = ctx.context.get("application_name")
    load_id = ctx.context.get("load_id")
    thread_id = ctx.context.get("thread_id")

    # Start the OpenTelemetry span
    with tracer.start_as_current_span("load_scan_processing") as span:
        # Set span attributes for better context
        span.set_attribute("agent_type", "load_scan")
        span.set_attribute("thread_id", thread_id)
        span.set_attribute("load_id", load_id)
        span.set_attribute("query_length", len(query))

        # Record agent invocation in metrics
        add_operation_count("load", "scan", True)
```

#### 3. API Call Instrumentation

Similar to the info_master sub-agent, the load_scan sub-agent also instruments API calls with nested spans:

```python
# Create a nested span for the API call
with tracer.start_as_current_span("azure_openai_api_call") as api_span:
    api_span.set_attribute("model", os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"))
    # ... other attributes ...

    # Record API request metrics
    api_start_time = time.time()
    record_api_request("azure_openai", "POST", "pending")

    # Make the API call
    response = await azure_client.chat.completions.create(...)

    # Calculate API call duration and record metrics
    api_duration_ms = (time.time() - api_start_time) * 1000
    record_api_duration(api_duration_ms, "azure_openai", "POST", "success")
```

#### 4. Database Update Instrumentation

Unique to the load_scan sub-agent, we also instrument the database update operation:

```python
# Create a nested span for updating load reply status
with tracer.start_as_current_span("update_load_reply_status") as update_span:
    update_span.set_attribute("thread_id", thread_id)
    update_span.set_attribute("load_id", load_id)
    update_span.set_attribute("application", application_name)

    update_start_time = time.time()
    update_result = await update_load_reply_status(load_id, application_name, result)
    update_duration_ms = (time.time() - update_start_time) * 1000

    # Record metrics for the update operation
    record_operation_duration("load", "update_status", update_result.get("success", False), update_duration_ms)
```

#### 5. Error Handling

Comprehensive error handling is implemented to capture and record all exceptions:

```python
except Exception as e:
    # Record error metrics
    error_message = str(e)
    error_type = type(e).__name__

    # Set error attributes on the current span
    current_span = trace.get_current_span()
    current_span.set_attribute("error", True)
    current_span.set_attribute("error.type", error_type)
    current_span.set_attribute("error.message", error_message)

    # Record error metrics
    record_error("load_scan", thread_id, application_name)
    add_operation_count("load", "scan", False)
```

### Rate Negotiator Sub-Agent

The `rate_negotiator.py` sub-agent has been instrumented with OpenTelemetry to provide detailed tracing and metrics for rate negotiation operations. Here's a breakdown of its implementation:

#### 1. Imports and Setup

```python
# Import OpenTelemetry
from opentelemetry import trace
from otel.metrics import (
    record_agent_duration,
    record_error,
    record_api_request,
    record_api_duration,
    record_operation_duration,
    add_operation_count,
    record_rate_operation,
    record_rate_duration
)

# Initialize tracer
tracer = trace.get_tracer("rate-negotiator-tracer")
```

#### 2. Send Draft Function Instrumentation

The `send_draft` function is instrumented to track API calls for sending draft emails:

```python
async def send_draft(project_name: str, load_id: str, email_body: str, email_subject: str, thread_id: str, draft: str):
    # Start timing for metrics
    start_time = time.time()

    # Start the OpenTelemetry span
    with tracer.start_as_current_span("send_draft") as span:
        # Set span attributes for better context
        span.set_attribute("thread_id", thread_id)
        span.set_attribute("load_id", load_id)
        span.set_attribute("application", project_name)
        span.set_attribute("email_subject_length", len(email_subject))
        span.set_attribute("draft_length", len(draft))

        try:
            # API call implementation...

            # Record API request metrics
            record_api_request("draft_api", "POST", "pending")

            # Make the API call...

            # Calculate API call duration and record metrics
            api_duration_ms = (time.time() - api_start_time) * 1000
            record_api_duration(api_duration_ms, "draft_api", "POST", "success")
            record_api_request("draft_api", "POST", "success")
```

#### 3. Main Function Instrumentation

The `run_rate_negotiator` function is instrumented with a hierarchical span structure:

```python
async def run_rate_negotiator(ctx: RunContextWrapper[Any], args: str):
    # Start timing for metrics
    start_time = time.time()

    # Start the OpenTelemetry span
    with tracer.start_as_current_span("rate_negotiator_processing") as span:
        # Set span attributes for better context
        span.set_attribute("agent_type", "rate_negotiator")

        try:
            # Parse arguments and extract context...

            # Add more span attributes now that we have the context
            span.set_attribute("thread_id", thread_id)
            span.set_attribute("load_id", load_id)
            span.set_attribute("query_length", len(user_input))

            # Record agent invocation metrics
            record_rate_operation("negotiation", True)
```

#### 4. Database Operations Instrumentation

Database operations are tracked with dedicated spans:

```python
# Create a nested span for database operations
with tracer.start_as_current_span("db_operations") as db_span:
    db_span.set_attribute("thread_id", thread_id)
    db_span.set_attribute("operation", "get_conversation_history")

    try:
        db_start_time = time.time()
        db_conversation_history = get_conversation_history(thread_id=thread_id)
        # ...
        db_duration_ms = (time.time() - db_start_time) * 1000

        # Record metrics for database operation
        record_operation_duration("rate", "db_get", True, db_duration_ms)
```

#### 5. OpenAI API Call Instrumentation

The OpenAI API call is tracked with a dedicated span:

```python
# Create a nested span for the OpenAI API call
with tracer.start_as_current_span("openai_agent_run") as agent_span:
    agent_span.set_attribute("thread_id", thread_id)
    agent_span.set_attribute("load_id", load_id)
    agent_span.set_attribute("model", deployment_name)

    # Record API request metrics
    api_start_time = time.time()
    record_api_request("openai_agent", "POST", "pending")

    try:
        result = await Runner.run(rate_negotiator, conversation_history)

        # Calculate API call duration and record metrics
        api_duration_ms = (time.time() - api_start_time) * 1000
        record_api_duration(api_duration_ms, "openai_agent", "POST", "success")
```

#### 6. Comprehensive Error Handling

Each level of the operation has dedicated error handling with metrics recording:

```python
except Exception as e:
    error_message = str(e)
    error_type = type(e).__name__

    # Set error attributes on the span
    current_span = trace.get_current_span()
    current_span.set_attribute("error", True)
    current_span.set_attribute("error.type", error_type)
    current_span.set_attribute("error.message", error_message)

    # Record error metrics
    record_error("rate_negotiator", thread_id, application_name)
    record_rate_operation("negotiation", False)
    duration_ms = (time.time() - start_time) * 1000
    record_rate_duration(duration_ms, "negotiation", False)
```

## Best Practices

When instrumenting other sub-agents, follow these best practices:

1. **Consistent Naming**: Use consistent naming for spans and metrics across all sub-agents
2. **Hierarchical Structure**: Maintain a hierarchical structure of spans
3. **Contextual Attributes**: Include relevant context in span attributes
4. **Comprehensive Error Handling**: Capture all errors with detailed context
5. **Performance Metrics**: Record duration metrics for all significant operations

## Visualization and Monitoring

The collected traces and metrics can be visualized in Google Cloud Trace and Monitoring. You can create custom dashboards to monitor:

1. Sub-agent performance and latency
2. Error rates and types
3. API call performance
4. Overall workflow execution time

This instrumentation provides a comprehensive view of the sub-agents' behavior and performance, enabling better monitoring, debugging, and optimization of the Numeo Agents Service.
