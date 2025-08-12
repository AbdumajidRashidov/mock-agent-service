from opentelemetry import metrics

# Use the same meter for all metrics
server_meter = metrics.get_meter("server_meter")
business_meter = metrics.get_meter("business_meter")

# Workflow metrics
workflow_duration = server_meter.create_histogram(
    "workflow.duration.ms", unit="ms", description="Total workflow execution time"
)

# Agent metrics
agent_invocation_counter = server_meter.create_counter(
    "agent.invocations", description="Number of times each agent is invoked", unit="1"
)

agent_duration = server_meter.create_histogram(
    "agent.duration.ms", unit="ms", description="Duration of each agent execution"
)

# Error metrics
error_counter = server_meter.create_counter(
    "workflow.errors",
    description="Number of errors encountered during workflow execution",
    unit="1",
)

# Business metrics
load_reply_counter = business_meter.create_counter(
    "business.load_replies", description="Number of load replies processed", unit="1"
)

# Message size metrics
message_size = server_meter.create_histogram(
    "message.size.bytes", unit="By", description="Size of messages processed"
)

# Server metrics
server_request_counter = server_meter.create_counter(
    "grpc_server.requests", description="Number of server requests received", unit="1"
)

server_request_duration = server_meter.create_histogram(
    "server.request.duration.ms",
    unit="ms",
    description="Duration of server request processing",
)

# API metrics
api_request_counter = server_meter.create_counter(
    "api.requests", description="Number of API requests made", unit="1"
)

api_request_duration = server_meter.create_histogram(
    "api.request.duration.ms", unit="ms", description="Duration of API requests"
)

api_error_counter = server_meter.create_counter(
    "api.errors", description="Number of API errors", unit="1"
)


# Email processor metrics
email_processor_counter = business_meter.create_counter(
    "email_processor.emails_processed",
    description="Number of emails processed by the email processor",
    unit="1",
)

email_classification_counter = business_meter.create_counter(
    "email_processor.classification",
    description="Number of emails classified by type",
    unit="1",
)

email_processing_duration = business_meter.create_histogram(
    "email_processor.processing_duration.ms",
    unit="ms",
    description="Duration of email processing",
)

order_extraction_duration = business_meter.create_histogram(
    "email_processor.order_extraction_duration.ms",
    unit="ms",
    description="Duration of order extraction from emails",
)

order_type_counter = business_meter.create_counter(
    "email_processor.order_types",
    description="Number of orders by type (spot, lane, etc.)",
    unit="1",
)

location_extraction_counter = business_meter.create_counter(
    "email_processor.location_extraction",
    description="Count of successful/failed location extractions",
    unit="1",
)

ai_request_counter = business_meter.create_counter(
    "email_processor.ai_requests",
    description="Number of AI requests made during email processing",
    unit="1",
)

ai_request_duration = business_meter.create_histogram(
    "email_processor.ai_request_duration.ms",
    unit="ms",
    description="Duration of AI requests during email processing",
)

route_generation_counter = business_meter.create_counter(
    "email_processor.route_generation",
    description="Count of route generation attempts and results",
    unit="1",
)

route_generation_duration = business_meter.create_histogram(
    "email_processor.route_generation_duration.ms",
    unit="ms",
    description="Duration of route generation",
)

# Create operation-specific metrics once at module level
operation_counters = {}
operation_durations = {}


# Initialize operation metrics for known operation types
def initialize_operation_metrics(operation_type):
    """Initialize counter and histogram for a specific operation type."""
    counter_name = f"{operation_type}.operations"
    if counter_name not in operation_counters:
        operation_counters[counter_name] = server_meter.create_counter(
            counter_name, description=f"Number of {operation_type} operations", unit="1"
        )

    duration_name = f"{operation_type}.operation.duration.ms"
    if duration_name not in operation_durations:
        operation_durations[duration_name] = server_meter.create_histogram(
            duration_name,
            unit="ms",
            description=f"Duration of {operation_type} operations",
        )


# Initialize metrics for known operation types
initialize_operation_metrics("warnings")
initialize_operation_metrics("info")
initialize_operation_metrics("rate")


# Helper functions
def record_workflow_duration(duration_ms: float, attributes: dict):
    """Record workflow execution duration."""
    workflow_duration.record(duration_ms, attributes)


def record_agent_invocation(agent_type: str, thread_id: str, application: str):
    """Record agent invocation."""
    agent_invocation_counter.add(
        1,
        {"agent.type": agent_type, "thread_id": thread_id, "application": application},
    )


def record_agent_duration(agent_type: str, duration_ms: float, attributes: dict):
    """Record agent execution duration."""
    agent_duration.record(duration_ms, {"agent.type": agent_type, **attributes})


def record_error(error_type: str, thread_id: str, application: str):
    """Record workflow error."""
    error_counter.add(
        1,
        {"error.type": error_type, "thread_id": thread_id, "application": application},
    )


def record_load_reply(
    application: str, has_truck_context: bool, has_load_context: bool
):
    """Record load reply processing."""
    load_reply_counter.add(
        1,
        {
            "application": application,
            "has_truck_context": str(has_truck_context),
            "has_load_context": str(has_load_context),
        },
    )


def record_message_size(size_bytes: int, message_type: str, thread_id: str):
    """Record message size."""
    message_size.record(
        size_bytes, {"message.type": message_type, "thread_id": thread_id}
    )


def record_server_request(endpoint: str, status: str):
    """Record server request."""
    server_request_counter.add(1, {"endpoint": endpoint, "status": status})


def record_server_request_duration(duration_ms: float, endpoint: str, status: str):
    """Record server request duration."""
    server_request_duration.record(
        duration_ms, {"endpoint": endpoint, "status": status}
    )


# Helper functions for API metrics
def record_api_request(endpoint: str, method: str, status: str):
    """Record API request."""
    api_request_counter.add(
        1, {"endpoint": endpoint, "method": method, "status": status}
    )


def record_api_duration(duration_ms: float, endpoint: str, method: str, status: str):
    """Record API request duration."""
    api_request_duration.record(
        duration_ms, {"endpoint": endpoint, "method": method, "status": status}
    )


def record_api_error(endpoint: str, error_type: str, status_code: str):
    """Record API error."""
    api_error_counter.add(
        1, {"endpoint": endpoint, "error.type": error_type, "status_code": status_code}
    )


# Helper functions for recording operations
def add_operation_count(operation_type, operation, success, extra_attributes=None):
    """Record an operation count only.

    Args:
        operation_type: Type of operation (e.g., "warnings", "info")
        operation: Name of the operation
        success: Whether the operation was successful
        extra_attributes: Additional attributes to record (optional)
    """
    # Base attributes
    attributes = {"operation": operation, "success": str(success).lower()}

    # Add extra attributes if provided
    if extra_attributes:
        attributes.update(extra_attributes)

    # Get counter and add count
    counter_name = f"{operation_type}.operations"
    if counter_name in operation_counters:
        operation_counters[counter_name].add(1, attributes)


def record_operation_duration(
    operation_type, operation, success, duration_ms, extra_attributes=None
):
    """Record an operation duration only.

    Args:
        operation_type: Type of operation (e.g., "warnings", "info")
        operation: Name of the operation
        success: Whether the operation was successful
        duration_ms: Duration of the operation in milliseconds
        extra_attributes: Additional attributes to record (optional)
    """
    # Base attributes
    attributes = {"operation": operation, "success": str(success).lower()}

    # Add extra attributes if provided
    if extra_attributes:
        attributes.update(extra_attributes)

    # Get histogram and record duration
    duration_name = f"{operation_type}.operation.duration.ms"
    if duration_name in operation_durations:
        operation_durations[duration_name].record(duration_ms, attributes)


# Helper functions for specific operation types
def record_warnings_operation(
    operation: str, success: bool, has_warnings: bool = False
):
    """Record warnings operation."""
    extra_attributes = {"has_warnings": str(has_warnings).lower()}
    add_operation_count("warnings", operation, success, extra_attributes)


def record_warnings_duration(duration_ms: float, operation: str, success: bool):
    """Record warnings operation duration."""
    extra_attributes = {"has_warnings": "false"}  # Default value
    record_operation_duration(
        "warnings", operation, success, duration_ms, extra_attributes
    )


def record_info_operation(operation: str, success: bool):
    """Record info operation."""
    add_operation_count("info", operation, success)


def record_info_duration(duration_ms: float, operation: str, success: bool):
    """Record info operation duration."""
    record_operation_duration("info", operation, success, duration_ms)


def record_rate_operation(operation: str, success: bool):
    """Record rate operation."""
    add_operation_count("rate", operation, success)


def record_rate_duration(duration_ms: float, operation: str, success: bool):
    """Record rate operation duration."""
    record_operation_duration("rate", operation, success, duration_ms)


# Helper functions for email processor metrics
def record_email_processed(
    application: str, source: str, has_order_related_keywords: bool
):
    """Record that an email has been processed."""
    email_processor_counter.add(
        1,
        {
            "application": application,
            "source": source,
            "has_order_related_keywords": str(has_order_related_keywords),
        },
    )


def record_email_classification(application: str, is_order_related: bool):
    """Record email classification result."""
    email_classification_counter.add(
        1, {"application": application, "is_order_related": str(is_order_related)}
    )


def record_email_processing_duration(
    duration_ms: float, application: str, is_order_related: bool
):
    """Record the duration of email processing."""
    email_processing_duration.record(
        duration_ms,
        {"application": application, "is_order_related": str(is_order_related)},
    )


def record_order_extraction_duration(
    duration_ms: float, application: str, success: bool
):
    """Record the duration of order extraction from an email."""
    order_extraction_duration.record(
        duration_ms, {"application": application, "success": str(success)}
    )


def record_order_type(order_type: str, application: str):
    """Record the type of order extracted from an email."""
    order_type_counter.add(1, {"order_type": order_type, "application": application})


def record_location_extraction(success: bool, location_type: str, application: str):
    """Record success/failure of location extraction."""
    location_extraction_counter.add(
        1,
        {
            "success": str(success),
            "location_type": location_type,
            "application": application,
        },
    )


def record_ai_request(request_type: str, application: str, success: bool):
    """Record an AI request made during email processing."""
    ai_request_counter.add(
        1,
        {
            "request_type": request_type,
            "application": application,
            "success": str(success),
        },
    )


def record_ai_request_duration(
    duration_ms: float, request_type: str, application: str, success: bool
):
    """Record the duration of an AI request made during email processing."""
    ai_request_duration.record(
        duration_ms,
        {
            "request_type": request_type,
            "application": application,
            "success": str(success),
        },
    )


def record_route_generation(success: bool, application: str, has_offering_rate: bool):
    """Record a route generation attempt."""
    route_generation_counter.add(
        1,
        {
            "success": str(success),
            "application": application,
            "has_offering_rate": str(has_offering_rate),
        },
    )


def record_route_generation_duration(
    duration_ms: float, application: str, success: bool
):
    """Record the duration of route generation."""
    route_generation_duration.record(
        duration_ms, {"application": application, "success": str(success)}
    )
