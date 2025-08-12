import dotenv
dotenv.load_dotenv()

import otel.setup
import os
import logging
import asyncio
import sys
import grpc.aio  # Using AsyncIO gRPC
import grpc  # Keep this for gRPC types
from google.protobuf import json_format
from datetime import datetime
from google.protobuf.struct_pb2 import Struct

# Add the generated proto files to the Python path
sys.path.append(os.path.dirname(__file__))
# Import the generated proto classes
from generated.agents_service.process_new_email import response_pb2 as process_new_email_response_pb2
from generated.agents_service.load_reply import response_pb2 as process_load_reply_response_pb2
from generated.agents_service.process_batch_warnings import response_pb2 as process_batch_warnings_response_pb2
from generated.agents_service.stream_negotiation import response_pb2 as stream_negotiation_response_pb2
from generated.agents_service.process_ratecon import response_pb2 as process_ratecon_response_pb2
from generated.agents_service import index_pb2_grpc as agents_service_pb2_grpc
from test_agent.TestAgent import test_agent

# Import the workflow processors
from workflows.new_email_processor.main import process_email
from workflows.load_reply_processor_langgraph_based.main import process_reply as process_reply_langgraph_based
from workflows.ratecon_processor.main import process_ratecon

from otel.metrics import (
    record_message_size,
    record_server_request,
)

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class EmailProcessingServiceServicer(
    agents_service_pb2_grpc.EmailProcessingServiceServicer
):
    """Implementation of the EmailProcessingService service."""

    async def ProcessBatchWarnings(self, request, context):
        """Process batch warnings for multiple loads."""
        try:
            # Import the batch warnings processor module
            from workflows.batch_warnings_processor_v2.main import process_batch_warnings_v2
            # Process batch warnings using the dedicated module - await the async function
            response = await process_batch_warnings_v2(request, process_batch_warnings_response_pb2)
            return response

        except Exception as e:
            logger.error(f"Error processing batch warnings: {str(e)}")
            return process_batch_warnings_response_pb2.BatchWarningsResponse(
                success=False,
                message=f"Error processing batch warnings: {str(e)}",
            )

    async def ProcessLoadReply(self, request, context):
        """Process a load reply email with streaming response."""
        try:
            # Convert protobuf objects to dictionaries
            company_details = json_format.MessageToDict(request.company_details)
            truck = json_format.MessageToDict(request.truck)
            load = json_format.MessageToDict(request.load)
            emails = [json_format.MessageToDict(email) for email in request.emails]
            our_emails = list(request.our_emails)

            if not emails:
                raise ValueError("No emails provided in the request")

            response_data = await process_reply_langgraph_based(
                company_details=company_details,
                our_emails=our_emails,
                truck=truck,
                load=load,
                emails=emails,
            )

            response = process_load_reply_response_pb2.LoadReplyProcessorResponse(success=True)
            if 'email_to_send' in response_data:
                response.email_to_send = response_data['email_to_send']
            if 'field_updates' in response_data:
                response.field_updates.update(response_data['field_updates'])
            if 'plugin_response' in response_data:
                response.plugin_response.CopyFrom(json_format.ParseDict(response_data['plugin_response'], Struct()))
            if 'message' in response_data:
                response.message = response_data['message']
            if 'metadata' in response_data:
                response.metadata.update(response_data['metadata'])
            if 'trace_id' in response_data:
                response.trace_id = response_data['trace_id']

            yield response
        except Exception as e:
            response = process_load_reply_response_pb2.LoadReplyProcessorResponse(success=False)
            if str(e):
                response.error_message = str(e)
            yield response

    async def _process_email_async(self, request):
        """Process email asynchronously using the process_email function."""
        try:
            email_data = {
                "subject": request.email.subject,
                "body": request.email.body,
                "threadId": request.email.thread_id,
            }

            # Record message size
            if request.email.body:
                record_message_size(
                    size_bytes=len(request.email.body.encode("utf-8")),
                    message_type="email",
                    thread_id=request.email.thread_id,
                )

            result = await process_email(email_data, request.application_name)
            return result
        except Exception as e:

            logger.error(f"Error processing email: {str(e)}")
            raise

    async def ProcessNewEmail(self, request, context):
        """Process a new email."""
        logger.info(f"Processing new email with subject: {request.email.subject}")

        try:
            # Record server request
            record_server_request(
                endpoint="agent_service.process_new_email", status="processing"
            )

            # Process the email
            result = await self._process_email_async(request)

            logger.info(f"Email processing result: {result}")

            # Convert the result to the gRPC response format
            orders = []
            for order_data in result.get("orders", []):
                # Create Order object
                order = process_new_email_response_pb2.Order(
                    pickup=order_data.get("pickup", ""),
                    delivery=order_data.get("delivery", ""),
                    route=order_data.get("route", ""),
                    offering_rate=float(order_data.get("offeringRate", 0.0)),
                    thread_id=order_data.get("threadId", ""),
                )

                orders.append(order)

            # Create Broker object if broker data exists
            broker_data = result.get("broker", {})
            broker = process_new_email_response_pb2.Broker(
                mc_number=broker_data.get("mcNumber", ""),
                full_name=broker_data.get("fullName", ""),
                email=broker_data.get("email", ""),
                phone=broker_data.get("phone", ""),
                company=broker_data.get("companyName", ""),
            )

            # Create and return the response
            return process_new_email_response_pb2.EmailProcessingResponse(
                success=True,
                message="New email processed successfully",
                session_id=f"session_{request.email.thread_id}",
                thread_id=result.get("threadId", request.email.thread_id),
                order_type=result.get("orderType", "unclassified"),
                unclassification_reason=result.get("unclassificationReason", ""),
                orders=orders,
                broker=broker,
                execution_link="https://example.com/execution/123",
            )

        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")

            return process_new_email_response_pb2.EmailProcessingResponse(
                success=False,
                message=f"Error processing email: {str(e)}",
                session_id=f"session_{request.email.thread_id}",
                thread_id=request.email.thread_id,
                order_type="unclassified",
                unclassification_reason=f"Error: {str(e)}",
            )

    async def StreamNegotiation(self, request, context):
        """Unified method for all negotiation operations - makes the agent service stateless."""
        # Extract common fields
        negotiation_id = getattr(request, "negotiation_id", "")
        action = getattr(request, "action", "")
        application_name = getattr(request, "application_name", "")

        logger.info(
            f"[StreamNegotiation] Received {action} request for negotiation_id={negotiation_id}, app={application_name}"
        )

        try:
            # Handle different action types
            if action == "initiate":
                # Handle initialization
                async for response in self._handle_initiate_negotiation(request):
                    yield response

            elif action == "message":
                # Handle message processing with streaming responses
                async for response in self._handle_negotiation_message(request):
                    yield response

            elif action == "history":
                # Handle history retrieval
                response = await self._handle_get_negotiation_history(request)
                yield response

            else:
                # Handle unknown action
                logger.error(f"[StreamNegotiation] Unknown action: {action}")
                yield stream_negotiation_response_pb2.NegotiationResponse(
                    response_type="error",
                    negotiation_id=negotiation_id,
                    success=False,
                    error_message=f"Unknown action: {action}",
                    timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                )

        except Exception as e:
            # Handle any exceptions
            logger.error(f"[StreamNegotiation] Error: {e}")
            yield stream_negotiation_response_pb2.NegotiationResponse(
                response_type="error",
                negotiation_id=negotiation_id,
                success=False,
                error_message=f"Error processing request: {str(e)}",
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            )

    async def _handle_initiate_negotiation(self, request):
        """Handle the 'initiate' action for StreamNegotiation."""
        negotiation_id = getattr(request, "negotiation_id", "")
        application_name = getattr(request, "application_name", "")
        load_id = getattr(request, "load_id", "")
        user_id = getattr(request, "user_id", "")

        logger.info(
            f"[_handle_initiate_negotiation] Initializing negotiation_id={negotiation_id}, app={application_name}, load_id={load_id}, user_id={user_id}"
        )

        # Import the test_agent function
        from test_agent.TestAgent import test_agent

        # Prepare initiation data
        initiation_data = {
            "negotiation_id": negotiation_id,
            "application_name": application_name,
            "load_id": load_id,
            "user_id": user_id,
        }

        try:
            # Run test_agent to get structured event list
            now = datetime.datetime.utcnow()
            base_id = f"msg_{int(now.timestamp() * 1000)}"
            agent_events = await test_agent(initiation_data)
            for ev in agent_events:
                logger.info(f"[TestAgent] Initiate event: {ev}")
                yield agents_serivce_pb2.NegotiationResponse(
                    response_type="initiate",
                    negotiation_id=negotiation_id,
                    success=True,
                    timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                    message_id=f"{ev['type']}_{base_id}",
                    content=ev["content"],
                    agent_state=ev["type"],
                )
        except Exception as e:
            logger.error(f"[TestAgent] Error during initiation: {str(e)}")
            yield agents_serivce_pb2.NegotiationResponse(
                response_type="initiate",
                negotiation_id=negotiation_id,
                success=False,
                error_message=str(e),
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                content="Agent failed to initialize negotiation.",
                agent_state="error",
            )

    async def _handle_negotiation_message(self, request):
        """Handle the 'message' action for StreamNegotiation with streaming responses."""
        negotiation_id = getattr(request, "negotiation_id", "")
        content = getattr(request, "content", "")
        user_id = getattr(request, "user_id", "user")
        application_name = getattr(request, "application_name", "")
        load_id = getattr(request, "load_id", "")

        logger.info(
            f"[_handle_negotiation_message] Processing message for negotiation_id={negotiation_id}, app={application_name}, load_id={load_id}"
        )

        # Generate a message ID
        now = datetime.datetime.utcnow()
        message_id = f"msg_{int(now.timestamp() * 1000)}"

        # Run test_agent to get structured event list
        base_id = message_id
        agent_events = await test_agent(
            initiation_data={
                "negotiation_id": negotiation_id,
                "application_name": application_name,
                "load_id": load_id,
                "user_id": user_id,
                "content": content,
            }
        )
        for ev in agent_events:
            logger.info(f"[TestAgent] Message event: {ev}")
            yield agents_serivce_pb2.NegotiationResponse(
                response_type="message",
                negotiation_id=negotiation_id,
                success=True,
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                message_id=f"{ev['type']}_{base_id}",
                content=ev["content"],
                agent_state=ev["type"],
            )

        logger.info(
            f"[_handle_negotiation_message] Completed streaming responses for negotiation_id={negotiation_id}"
        )

    async def _handle_get_negotiation_history(self, request):
        """Handle the 'history' action for StreamNegotiation."""
        negotiation_id = getattr(request, "negotiation_id", "")
        application_name = getattr(request, "application_name", "")

        logger.info(
            f"[_handle_get_negotiation_history] Retrieving history for negotiation_id={negotiation_id}, app={application_name}"
        )

        # In a real implementation, you would fetch messages from a database asynchronously
        # Since we're stateless, we return an empty list
        return agents_serivce_pb2.NegotiationResponse(
            response_type="history",
            negotiation_id=negotiation_id,
            success=True,
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            messages=[],
        )

    async def ProcessRatecon(self, request, context):
        """Process a rate confirmation document from a GCS URL."""
        try:
            logger.info(f"Processing rate confirmation from URL: {request.document_url}")

            # Process the rate confirmation using the dedicated module
            response = await process_ratecon(request, process_ratecon_response_pb2)
            return response

        except Exception as e:
            logger.error(f"Error processing rate confirmation: {str(e)}")
            return process_ratecon_response_pb2.ProcessRateconResponse(
                success=False,
                error_message=f"Error processing rate confirmation: {str(e)}",
                is_rate_confirmation=False
            )


async def serve():
    """Start the async gRPC server."""
    try:
        # Create an AsyncIO gRPC server
        server = grpc.aio.server(
            options=[
                ('grpc.max_session_memory', 2147483648 * 5) # 10GB
            ]
        )

        # Add the servicer to the server
        agents_service_pb2_grpc.add_EmailProcessingServiceServicer_to_server(
            EmailProcessingServiceServicer(), server
        )

        # Listen on port 50051
        server.add_insecure_port("[::]:50051")

        # Start the server
        await server.start()
        logger.info("AsyncIO Server successfully started on port 50051")

        # Wait for the server to stop
        await server.wait_for_termination()

    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        raise


if __name__ == "__main__":
    # Run the async server using asyncio
    asyncio.run(serve())
