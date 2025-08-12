#!/usr/bin/env python3
"""
gRPC server for the EmailProcessingService.
"""
import os
import logging
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource, get_aggregated_resources
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.grpc import GrpcAioInstrumentorServer
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
    ConsoleMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.resourcedetector.gcp_resource_detector import GoogleCloudResourceDetector

import psutil
import gc
import tracemalloc

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

OTEL_EXPORTER = os.getenv("OTEL_EXPORTER", "none").lower()
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "agents-service")
OTEL_EXPORTER_ENDPOINT = os.getenv("OTEL_EXPORTER_ENDPOINT", "http://localhost:4318")

if os.getenv("ENVIRONMENT") == "development":
    resource = Resource.create(attributes={"service.name": OTEL_SERVICE_NAME})
else:
    custom_resource = Resource.create(attributes={"service.name": OTEL_SERVICE_NAME})
    gcp_resource = get_aggregated_resources([GoogleCloudResourceDetector()])
    resource = custom_resource.merge(gcp_resource)

if OTEL_EXPORTER != "none":
    #### METRICS ####
    if OTEL_EXPORTER == "otlp":
        logger.info("[Metrics]: Using OpenTelemetry Protocol exporter")
        metric_exporter = OTLPMetricExporter(endpoint=f"{OTEL_EXPORTER_ENDPOINT}/v1/metrics")
    else:  # default to console
        logger.info("[Metrics]: Using Console metric exporter")
        metric_exporter = ConsoleMetricExporter()

    metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=5000)
    meter_provider = MeterProvider(metric_readers=[metric_reader], resource=resource)
    metrics.set_meter_provider(meter_provider)


    #### TRACES ####
    if OTEL_EXPORTER == "otlp":
        logger.info("[Traces]: Using OpenTelemetry Protocol exporter")
        span_exporter = OTLPSpanExporter(endpoint=f"{OTEL_EXPORTER_ENDPOINT}/v1/traces")
    else:  # default to console
        logger.info("[Traces]: Using Console span exporter")
        span_exporter = ConsoleSpanExporter()

    span_processor = BatchSpanProcessor(
        span_exporter,
        export_timeout_millis=30000,
        max_export_batch_size=1000,
        schedule_delay_millis=5000,
        max_queue_size=2048,
    )
    trace_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(trace_provider)
    trace_provider.add_span_processor(span_processor)

    GrpcAioInstrumentorServer().instrument()

    # Start tracemalloc to track Python heap allocations
    tracemalloc.start()

    # Create OpenTelemetry meter
    meter = metrics.get_meter("custom.memory.metrics")

    # 1. Process Memory Usage (Resident Set Size - RSS)d
    process = psutil.Process()

    def process_rss_callback(_):
        rss_gb = process.memory_info().rss / (1024 ** 3)  # Convert bytes to GB
        yield metrics.Observation(rss_gb)

    meter.create_observable_gauge(
        name="process_resident_memory_gb",
        description="Resident Set Size (RSS) memory used by the process in gigabytes",
        unit="GB",
        callbacks=[process_rss_callback]
    )

    # 2. Virtual Memory Size
    def process_virtual_memory_callback(_):
        vms_gb = process.memory_info().vms / (1024 ** 3)  # Convert bytes to GB
        yield metrics.Observation(vms_gb)

    meter.create_observable_gauge(
        name="process_virtual_memory_gb",
        description="Total virtual memory allocated for the process in gigabytes",
        unit="GB",
        callbacks=[process_virtual_memory_callback]
    )

    # 3. Heap Memory (using tracemalloc)
    def heap_memory_callback(_):
        current, _peak = tracemalloc.get_traced_memory()
        yield metrics.Observation(current)

    meter.create_observable_gauge(
        name="python_heap_memory_bytes",
        description="Current Python heap memory used (tracked by tracemalloc)",
        unit="By",
        callbacks=[heap_memory_callback]
    )

    # 4. Garbage Collection Stats (number of collections for generation 0 as example)
    def gc_collections_callback(_):
        counts = gc.get_count()  # Returns tuple: (gen0, gen1, gen2)
        yield metrics.Observation(counts[0])

    meter.create_observable_gauge(
        name="python_gc_generation0_collections",
        description="Number of garbage collections for generation 0",
        callbacks=[gc_collections_callback]
    )

else:
    logger.info("OpenTelemetry metrics disabled (none mode)")
    # Set up a basic meter provider without exporters
    meter_provider = MeterProvider(resource=resource)
    metrics.set_meter_provider(meter_provider)
