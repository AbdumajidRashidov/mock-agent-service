# main.py
"""
Simplified batch warnings processor main module.
"""

import asyncio
import logging
import time
import os
from openai import AsyncAzureOpenAI
from opentelemetry import trace
from .analyzer import LoadAnalyzer
from .models import FilterSeverity

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("batch-warnings-processor-v2")

async def process_batch_warnings_v2(request, agents_service_pb2):
    """
    Simplified batch processor using only AI filters.
    """
    start_time = time.time()

    # Initialize Async OpenAI client
    azure_client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )

    with tracer.start_as_current_span(
        "batch_warnings_processor_v2.process",
        attributes={
            "application_name": request.application_name,
            "truck_id": request.truck.id if request.truck else "unknown",
            "loads_count": len(request.loads) if request.loads else 0,
        },
    ) as span:

        try:
            logger.info(f"Processing batch warnings for {len(request.loads)} loads")

            # Initialize analyzer
            analyzer = LoadAnalyzer(azure_client)

            # Convert protobuf data
            truck_data = _protobuf_to_dict(request.truck)
            loads_data = [_protobuf_to_dict(load) for load in request.loads]
            custom_prompts = _protobuf_to_dict(request.custom_prompts)

            # Analyze all loads in parallel
            analysis_results = await asyncio.gather(
                *[analyzer.analyze_single_load(load_data, truck_data, custom_prompts)
                  for load_data in loads_data],
                return_exceptions=True
            )

            # Process results
            warning_items = []
            clean_loads = 0

            for i, result in enumerate(analysis_results):
                if isinstance(result, Exception):
                    logger.error(f"Analysis failed for load {i}: {result}")
                    continue

                warning_item = result.to_warning_item(agents_service_pb2)
                if warning_item is None:
                    clean_loads += 1
                else:
                    warning_items.append(warning_item)

            # Record metrics
            duration_ms = (time.time() - start_time) * 1000
            span.set_attribute("status", "success")
            span.set_attribute("duration_ms", duration_ms)
            span.set_attribute("clean_loads", clean_loads)
            span.set_attribute("problematic_loads", len(warning_items))

            logger.info(f"Batch processing completed: {clean_loads} clean, {len(warning_items)} problematic")

            return agents_service_pb2.BatchWarningsResponse(
                success=True,
                message=f"Processed {len(request.loads)} loads with {clean_loads} clean and {len(warning_items)} problematic",
                warning_items=warning_items
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            span.set_attribute("status", "error")
            span.set_attribute("duration_ms", duration_ms)
            span.record_exception(e)

            logger.error(f"Error processing batch warnings: {str(e)}")

            return agents_service_pb2.BatchWarningsResponse(
                success=False,
                message=f"Error processing batch warnings: {str(e)}",
                warning_items=[]
            )


def _protobuf_to_dict(pb_obj):
    """Convert protobuf object to dictionary."""
    if pb_obj is None:
        return {}

    result = {}
    try:
        for field_desc in pb_obj.DESCRIPTOR.fields:
            field_name = field_desc.name
            field_value = getattr(pb_obj, field_name)

            if field_desc.label == field_desc.LABEL_REPEATED:
                if field_desc.type == field_desc.TYPE_MESSAGE:
                    result[field_name] = [_protobuf_to_dict(item) for item in field_value]
                else:
                    result[field_name] = list(field_value)
            elif field_desc.type == field_desc.TYPE_MESSAGE:
                if field_name in ['origin', 'destination']:
                    result[field_name] = _protobuf_to_dict(field_value)
                elif field_name == 'is_permitted':
                    permits_dict = {}
                    for permit_field in field_value.DESCRIPTOR.fields:
                        permits_dict[permit_field.name] = getattr(field_value, permit_field.name)
                    result[field_name] = permits_dict
                elif field_name == 'security':
                    security_dict = {}
                    for security_field in field_value.DESCRIPTOR.fields:
                        security_dict[security_field.name] = getattr(field_value, security_field.name)
                    result[field_name] = security_dict
                else:
                    result[field_name] = _protobuf_to_dict(field_value)
            else:
                result[field_name] = field_value

    except Exception as e:
        logger.error(f"Error converting protobuf to dict: {str(e)}")
        # Fallback for basic fields
        basic_fields = ['id', 'truck_id', 'comments', 'equipment_type', 'team_solo', 'excluded_states', 'restrictions']
        for field in basic_fields:
            if hasattr(pb_obj, field):
                result[field] = getattr(pb_obj, field)

    return result
