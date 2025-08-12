#!/usr/bin/env python3
"""
Example gRPC client for the EmailProcessingService.

This script demonstrates how to create a gRPC client that connects to the
EmailProcessingService and makes both ProcessNewEmail and ProcessLoadReply requests.

Usage:
    python example_client.py [--env {local|prod}] [--host HOST] [--port PORT] [--secure]

Options:
    --env ENV      Environment to connect to: 'local' or 'prod' [default: local]
    --host HOST    Server hostname or IP address [default: localhost for local, agents-service-buv6rhpwpq-uc.a.run.app for prod]
    --port PORT    Server port [default: 50051 for local, 443 for prod]
    --secure       Use secure channel (TLS) [default: False for local, True for prod]
"""

import argparse
import grpc
import os
import sys
from google.protobuf.json_format import MessageToJson
import datetime
from google.protobuf.timestamp_pb2 import Timestamp

# Add the generated proto files to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "proto/generated"))

# Import the generated proto classes
from generated import agents_serivce_pb2
from generated import agents_serivce_pb2_grpc


def create_sample_email(input_text=None):
    """Create a sample Email message for testing.

    Args:
        input_text (str, optional): Text containing rate and commodity information.
            If None, default values will be used.

    Returns:
        agents_serivce_pb2.Email: A sample email message.
    """
    # Default email body
    default_body = """
Rate: $1700
Commodity: This is beer
Thanks,
Robert
"""

    # Use provided input text or default
    body = input_text if input_text else default_body

    # Make sure the body has proper newlines
    if '\n' not in body:
        # Replace escaped newlines with actual newlines
        body = body.replace('\\n', '\n')

    print(f"Email body (raw):\n{repr(body)}")

    # Extract rate and commodity from the body if possible
    rate = None
    commodity = None

    for line in body.split('\n'):
        line = line.strip()
        if line.startswith('Rate:'):
            rate = line
            print(f"Found rate: {rate}")
        elif line.startswith('Commodity:'):
            commodity = line
            print(f"Found commodity: {commodity}")

    # If we found both rate and commodity, print them
    if rate and commodity:
        print(f"Successfully extracted rate and commodity information")
    else:
        print(f"Warning: Could not extract all information. Rate: {rate is not None}, Commodity: {commodity is not None}")

    # Create timestamp for the email
    timestamp = Timestamp()
    timestamp.GetCurrentTime()

    return agents_serivce_pb2.Email(
        subject="Test Email Subject",
        body=body,
        thread_id="test_thread_123",
        publish_time=timestamp
    )


def create_sample_truck():
    """Create a sample Truck message for testing."""
    return agents_serivce_pb2.Truck(
        id="truck_123",
        truck_id="T-123456",
        main_info="53' Dry Van",
        first_driver=agents_serivce_pb2.Truck.Driver(
            name="John Doe",
            phone="555-123-4567",
            is_us_citizen=True,
            hometown="Chicago, IL"
        ),
        second_driver=agents_serivce_pb2.Truck.Driver(
            name="Jane Smith",
            phone="555-765-4321",
            is_us_citizen=True,
            hometown="Detroit, MI"
        ),
        equipment=agents_serivce_pb2.Truck.Equipment(
            type="DRY_VAN",
            values=["53'", "Air Ride"]
        ),
        restrictions=["alcohol", "baled_paper", "scrap"],
        is_permitted=agents_serivce_pb2.Truck.Permits(
            hazmat=True,
            tanker=False,
            double_triple_trailers=False,
            combination_endorsements=True,
            canada_operating_authority=True,
            mexico_operating_authority=False,
            oversize_overweight=False,
            hazardous_waste_radiological=False
        ),
        security=agents_serivce_pb2.Truck.Security(
            tsa=True,
            twic=False,
            heavy_duty_lock=True,
            escort_driving_ok=False,
            cross_border_loads=True
        ),
        length=53,
        weight=45000,
        deadhead_origin="Chicago, IL",
        deadhead_destination="Detroit, MI",
        team_solo="SOLO",
        weekly_gross_target=8000,
        max_travel_distance=800,
        min_travel_distance=200,
        full_partial="FULL",
        excluded_states=["NY", "NJ"],
        avoid_winter_roads=True,
        eld_integration=True,
        created_at="2025-03-01T00:00:00Z",
        updated_at="2025-03-28T00:00:00Z"
    )


def create_sample_load():
    """Create a sample Load message for testing."""
    return agents_serivce_pb2.Load(
        id="load_4562",
        type="DAT",
        external_id="DAT-789",
        equipment_type="DRY_VAN",
        posted_at="2025-03-25T10:00:00Z",
        earliest_availability="2025-03-26T08:00:00Z",
        latest_availability="2025-03-26T16:00:00Z",
        created_at="2025-03-25T09:00:00Z",
        updated_at="2025-03-25T09:30:00Z",
        status="ACTIVE",
        is_factorable=True,
        booking_url="https://example.com/booking/789",
        posters_reference_id="REF-123",
        route_id="ROUTE-456",
        duration=720,  # 12 hours in minutes
        length=500,  # miles
        polyline="encoded_polyline_string_here",
        trip_length=500,
        origin=agents_serivce_pb2.Load.LocationInfo(
            type="Point",
            coordinates=[87.6298, 41.8781],  # [lng, lat] for Chicago
            city="Chicago",
            state_prov="IL"
        ),
        destination=agents_serivce_pb2.Load.LocationInfo(
            type="Point",
            coordinates=[93.2650, 44.9778],  # [lng, lat] for Minneapolis
            city="Minneapolis",
            state_prov="MN"
        ),
        rate_info=agents_serivce_pb2.Load.RateInfo(
            basis="FLAT",
            rate_usd=1500.0,
            minimum_rate=2000.0,
            maximum_rate=3000.0
        ),
        poster_info=agents_serivce_pb2.Load.PosterInfo(
            contact=agents_serivce_pb2.Load.Contact(
                email="broker@example.com",
                phone_number="555-987-6543"
            ),
            credit=agents_serivce_pb2.Load.Credit(
                as_of="2025-03-20T00:00:00Z",
                credit_score=85,
                days_to_pay=30
            ),
            carrier_home_state="IL",
            city="Chicago",
            company_name="Example Logistics",
            preferred_contact_method="email",
            mc_number="MC-123456"
        ),
        shipment_details=agents_serivce_pb2.Load.ShipmentDetails(
            type="DRY_VAN",
            full_partial="FULL",
            maximum_length_feet=53,
            maximum_weight_pounds=45000
        )
    )


def create_company_details():
    """Create a sample CompanyDetails message for testing."""
    return agents_serivce_pb2.CompanyDetails(
        name="Example Trucking Company",
        mc_number="MC-987654",
        details="A reliable trucking company with a strong safety record.",
        rate_negotiation=agents_serivce_pb2.RateNegotiation(
            first_bid_threshold=1200,
            second_bid_threshold=1400,
            min_gap=50
        )
    )


def create_sample_load_reply():
    """Create a sample LoadReplyRequest message for testing."""
    # Create a timestamp
    timestamp = Timestamp()
    timestamp.FromDatetime(datetime.datetime.now())

    return agents_serivce_pb2.LoadReplyRequest(
        reply_email=create_sample_email(),
        origin_email=create_sample_email(),
        application_name="test_app",
        company_details=create_company_details(),
        load_id="dffdfdfdf",
        thread_id="dfdfdfdf",
        email_id="email_789",
        load=create_sample_load(),
        truck_id="truck_123",
        truck=create_sample_truck(),
        publish_time=timestamp
    )


def process_new_email(stub, application_name="test_app", input_text=None):
    """Send a ProcessNewEmail request to the server.

    Args:
        stub: The gRPC stub to use for the call.
        application_name: The application name to include in the request.
        input_text (str, optional): Text containing rate and commodity information.

    Returns:
        The response from the server.
    """
    # Create a sample email with the provided input text
    email = create_sample_email(input_text)

    # Create the request
    request = agents_serivce_pb2.NewEmailRequest(
        application_name=application_name,
        email=email
    )

    print("\n--- Testing ProcessNewEmail ---")
    print(f"Sending request: {MessageToJson(request)}")

    # Call the service
    try:
        response = stub.ProcessNewEmail(request)
        print(f"Response received: {MessageToJson(response)}")
        return response
    except grpc.RpcError as e:
        print(f"Error during gRPC call: {e.details()}")
        return None


def process_load_reply(stub, application_name="test_app"):
    """Send a ProcessLoadReply request to the server."""
    print("\n--- Testing ProcessLoadReply ---")

    # Create the request
    request = create_sample_load_reply()

    # Call the service
    try:
        response = stub.ProcessLoadReply(request)
        print(f"Response received: {MessageToJson(response)}")
        return response
    except grpc.RpcError as e:
        print(f"Error during gRPC call: {e.details()}")
        return None


def process_batch_warnings(stub, application_name="test_app"):
    """Send a ProcessBatchWarnings request to the server.

    Args:
        stub: The gRPC stub to use for the call.
        application_name: The application name to include in the request.

    Returns:
        The response from the server.
    """
    try:
        # Create a sample truck
        truck = create_sample_truck()

        # Create a couple of sample loads
        load1 = create_sample_load()
        load1.id = "load_123"
        load1.equipment_type = "53' Dry Van"
        load1.comments = "This is beer"

        load2 = create_sample_load()
        load2.id = "load_456"
        load2.equipment_type = "Flatbed"
        load2.comments = "This is construction materials"
        if hasattr(load2, 'shipment_details') and load2.shipment_details:
            load2.shipment_details.maximum_weight_pounds = 45000

        # Create the request
        request = agents_serivce_pb2.BatchWarningsRequest(
            application_name=application_name,
            truck=truck,
            loads=[load1, load2]
        )

        # print("\n--- Testing ProcessBatchWarnings ---")
        # print(f"Sending request: {MessageToJson(request)}")

        # Call the service
        response = stub.ProcessBatchWarnings(request)

        print(f"Response received: {MessageToJson(response)}")

        return response
    except grpc.RpcError as e:
        print(f"RPC error: {e.code()}: {e.details()}")
        return None

def main():
    """Main function to run the client."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="gRPC client for EmailProcessingService")
    parser.add_argument("--env", choices=["local", "prod"], default="local",
                        help="Environment to connect to: 'local' or 'prod'")
    parser.add_argument("--host", help="Server hostname or IP (overrides --env)")
    parser.add_argument("--port", help="Server port (overrides --env)")
    parser.add_argument("--secure", action="store_true", help="Force secure channel (TLS)")
    parser.add_argument("--input", help="Input text containing rate and commodity information")
    parser.add_argument("--rate", help="Rate value (e.g. $5000)")
    parser.add_argument("--commodity", help="Commodity description")
    args = parser.parse_args()

    # Set default values based on environment
    if args.env == "prod":
        host = "agents-service-466440794038.us-central1.run.app"
        port = "443"
        use_secure = True
    else:  # local
        host = "localhost"
        port = "50051"
        use_secure = False

    # Override with explicit arguments if provided
    if args.host:
        host = args.host
    if args.port:
        port = args.port
    if args.secure:
        use_secure = True

    # Create the server address
    server_address = f"{host}:{port}"
    print(f"Connecting to server at {server_address} {'(secure)' if use_secure else '(insecure)'}")

    # Create a gRPC channel (secure or insecure)
    if use_secure:
        # For production Cloud Run services, use secure channel
        channel = grpc.secure_channel(
            server_address,
            grpc.ssl_channel_credentials()
        )
    else:
        # For local development, use insecure channel
        channel = grpc.insecure_channel(server_address)

    # Create a stub (client)
    stub = agents_serivce_pb2_grpc.EmailProcessingServiceStub(channel)

    try:
        # Test the ProcessLoadReply RPC
        # process_load_reply(stub)

        # Uncomment to test ProcessNewEmail RPC
        process_new_email(stub)

            # Uncomment to test ProcessBatchWarnings RPC
            # process_batch_warnings(stub)
    except Exception as e:
        print(f"Error during gRPC call: {str(e)}")
    finally:
        # Close the channel
        channel.close()
        print("Channel closed")
# https://agents-service-466440794038.us-central1.run.app

if __name__ == "__main__":
    main()


# python example_client.py --env local
