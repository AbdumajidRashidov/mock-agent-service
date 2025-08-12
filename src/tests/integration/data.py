
from generated import agents_serivce_pb2

# --- Helper functions to create protobuf messages ---

def create_email(subject="Test Email Subject", body="What is your MC number?", thread_id="test_thread_123"):
    """Create an Email message for testing."""
    return agents_serivce_pb2.Email(
        subject=subject,
        body=body,
        thread_id=thread_id
    )

def create_truck(truck_id="T-123456", equipment_type="DRY_VAN", restrictions=None, hazmat=True):
    """Create a Truck message with customizable parameters."""
    if restrictions is None:
        restrictions = ["alcohol", "baled_paper"]

    return agents_serivce_pb2.Truck(
        id=f"truck_{truck_id}",
        truck_id=truck_id,
        main_info=f"{equipment_type}",
        first_driver=agents_serivce_pb2.Truck.Driver(
            name="John Doe",
            phone="555-123-4567",
            is_us_citizen=True,
            hometown="Chicago, IL"
        ),
        equipment=agents_serivce_pb2.Truck.Equipment(
            type=equipment_type,
            values=["53'", "Air Ride"] if equipment_type == "DRY_VAN" else ["48'", "Temp Control"]
        ),
        restrictions=restrictions,
        is_permitted=agents_serivce_pb2.Truck.Permits(
            hazmat=hazmat,
            tanker=False if equipment_type == "DRY_VAN" else True,
            canada_operating_authority=True,
            mexico_operating_authority=False
        ),
        security=agents_serivce_pb2.Truck.Security(
            tsa=True,
            twic=False,
            heavy_duty_lock=True,
            escort_driving_ok=False,
            cross_border_loads=True
        ),
        length=53 if equipment_type == "DRY_VAN" else 48,
        weight=45000,
        team_solo="SOLO"
    )

def create_load(load_id="load_456", origin_city="Chicago", origin_state="IL",
               dest_city="Minneapolis", dest_state="MN", rate=1500.0,
               equipment_type="DRY_VAN", commodity="General Freight", weight=45000):
    """Create a Load message with customizable parameters."""
    # Create the base Load object
    load = agents_serivce_pb2.Load(
        id=load_id,
        equipment_type=equipment_type,
        origin=agents_serivce_pb2.Load.LocationInfo(
            city=origin_city,
            state_prov=origin_state
        ),
        destination=agents_serivce_pb2.Load.LocationInfo(
            city=dest_city,
            state_prov=dest_state
        ),
        rate_info=agents_serivce_pb2.Load.RateInfo(
            basis="FLAT",
            rate_usd=rate
        ),
        shipment_details=agents_serivce_pb2.Load.ShipmentDetails(
            type=equipment_type,
            full_partial="FULL",
            maximum_length_feet=53 if equipment_type == "DRY_VAN" else 48,
            maximum_weight_pounds=weight
            # Removed commodity field as it doesn't exist in the protobuf definition
        )
    )

    # Add commodity information to a field that exists in the protobuf definition
    # This is a workaround since we can't use the commodity field directly
    # You might need to adjust this based on the actual protobuf definition
    if hasattr(load, 'commodity'):
        load.commodity = commodity
    elif hasattr(load, 'description'):
        load.description = f"Commodity: {commodity}"

    return load

def create_company_details(name="Numeo Trucking", mc_number="MC-123456"):
    """Create a CompanyDetails message with customizable parameters."""
    return agents_serivce_pb2.CompanyDetails(
        name=name,
        mc_number=mc_number,
        details="A reliable trucking company with a strong safety record.",
        rate_negotiation=agents_serivce_pb2.RateNegotiation(
            first_bid_threshold=70,  # Using integer percentage (70%) instead of float (0.7)
            second_bid_threshold=40,  # Using integer percentage (40%) instead of float (0.4)
            min_gap=0
            # Removed rounding field as it doesn't exist in the protobuf definition
        )
    )

# --- Test Data List ---

# Create a list of LoadReplyRequest objects for various test scenarios
# Create standard test emails for different scenarios
emails = [
    # Scenario 1: Basic MC number inquiry
    agents_serivce_pb2.LoadReplyRequest(
        reply_email=create_email(
            subject="RE: Load Chicago, IL to Minneapolis, MN",
            body="<p>What is your MC number?</p>",
            thread_id="thread_1"
        ),
        origin_email=create_email(
            subject="Load Chicago, IL to Minneapolis, MN",
            body="<p>Need details for this load</p>",
            thread_id="thread_1"
        ),
        application_name="test_integration_app",
        company_details=create_company_details(name="Numeo Trucking", mc_number="123456"),
        load_id="load_1",
        thread_id="thread_1",
        email_id="email_1",
        load=create_load(load_id="load_1"),
        truck_id="truck_1",
        truck=create_truck(truck_id="T-123456")
    ),

    # Scenario 2: Rate negotiation inquiry
    agents_serivce_pb2.LoadReplyRequest(
        reply_email=create_email(
            subject="RE: Load New York to Boston",
            body="<p>Rate: $2,000, Commodity: General Freight, Weight: 45,000 lbs, Equipment: DRY_VAN, Pickup Location: New York, NY, Delivery Location: Boston, MA</p>",
            thread_id="thread_1"
        ),
        origin_email=create_email(
            subject="Load New York to Boston",
            body="<p>Looking for a carrier for this load</p>",
            thread_id="thread_1"
        ),
        application_name="test_integration_app",
        company_details=create_company_details(name="East Coast Logistics", mc_number="MC-789012"),
        load_id="load_1",
        thread_id="thread_1",
        email_id="email_1",
        load=create_load(
            load_id="load_1",
            origin_city="New York",
            origin_state="NY",
            dest_city="Boston",
            dest_state="MA",
            rate=2000.0
        ),
        truck_id="truck_1",
        truck=create_truck(truck_id="T-123456")
    ),

    # Scenario 3: Hazmat load with restricted commodity
    agents_serivce_pb2.LoadReplyRequest(
        reply_email=create_email(
            subject="RE: Hazmat Load Dallas to Houston",
            body="<p>Can you handle this alcohol shipment? It requires hazmat certification.</p>",
            thread_id="thread_1"
        ),
        origin_email=create_email(
            subject="Hazmat Load Dallas to Houston",
            body="<p>Need a carrier for hazmat load</p>",
            thread_id="thread_1"
        ),
        application_name="test_integration_app",
        company_details=create_company_details(name="Texas Transport", mc_number="MC-345678"),
        load_id="load_1",
        thread_id="thread_1",
        email_id="email_1",
        load=create_load(
            load_id="load_1",
            origin_city="Dallas",
            origin_state="TX",
            dest_city="Houston",
            dest_state="TX",
            rate=1800.0,
            commodity="Alcohol"
        ),
        truck_id="truck_3",
        truck=create_truck(
            truck_id="T-345678",
            restrictions=["explosives", "radioactive"],  # Note: alcohol not in restrictions
            hazmat=True
        )
    ),

    # Scenario 4: Reefer load with temperature requirements
    agents_serivce_pb2.LoadReplyRequest(
        reply_email=create_email(
            subject="RE: Reefer Load Miami to Orlando",
            body="<p>This is a refrigerated load of produce that needs to be kept at 34°F. Can you handle it?</p>",
            thread_id="thread_1"
        ),
        origin_email=create_email(
            subject="Reefer Load Miami to Orlando",
            body="<p>Looking for a reefer for this produce load</p>",
            thread_id="thread_1"
        ),
        application_name="test_integration_app",
        company_details=create_company_details(name="Florida Fresh Logistics", mc_number="MC-567890"),
        load_id="load_1",
        thread_id="thread_1",
        email_id="email_1",
        load=create_load(
            load_id="load_1",
            origin_city="Miami",
            origin_state="FL",
            dest_city="Orlando",
            dest_state="FL",
            rate=1200.0,
            equipment_type="REEFER",
            commodity="Fresh Produce",
            weight=38000
        ),
        truck_id="truck_1",
        truck=create_truck(
            truck_id="T-123456",
            equipment_type="REEFER"
        )
    ),

    # Scenario 5: Insurance information request
    agents_serivce_pb2.LoadReplyRequest(
        reply_email=create_email(
            subject="RE: Load Seattle to Portland",
            body="<p>Can you provide your insurance information and policy number?</p>",
            thread_id="thread_1"
        ),
        origin_email=create_email(
            subject="Load Seattle to Portland",
            body="<p>Need carrier for this short haul</p>",
            thread_id="thread_1"
        ),
        application_name="test_integration_app",
        company_details=create_company_details(name="Pacific Northwest Transport", mc_number="MC-901234"),
        load_id="load_1",
        thread_id="thread_1",
        email_id="email_1",
        load=create_load(
            load_id="load_1",
            origin_city="Seattle",
            origin_state="WA",
            dest_city="Portland",
            dest_state="OR",
            rate=950.0
        ),
        truck_id="truck_1",
        truck=create_truck(truck_id="T-123456")
    )
]

# Create specialized test emails for specific agent tests

# Custom test email for warnings_ai test
warnings_test_email = agents_serivce_pb2.LoadReplyRequest(
    reply_email=create_email(
        subject="RE: Hazmat Load Request",
        body="<p>Can you handle this alcohol shipment? It requires hazmat certification.</p>",
        thread_id="thread_warnings"
    ),
    origin_email=create_email(
        subject="Hazmat Load Request",
        body="<p>Need carrier for hazmat load</p>",
        thread_id="thread_warnings"
    ),
    application_name="test_integration_app",
    company_details=create_company_details(name="Warnings Test Transport", mc_number="MC-WARNINGS"),
    load_id="load_warnings",
    thread_id="thread_warnings",
    email_id="email_warnings",
    load=create_load(
        load_id="load_warnings",
        origin_city="Denver",
        origin_state="CO",
        dest_city="Salt Lake City",
        dest_state="UT",
        rate=1200.0
    ),
    truck_id="truck_warnings",
    truck=create_truck(truck_id="T-WARNINGS", restrictions=["alcohol", "tobacco"], hazmat=True)
)

# Custom test email for load_scan test
load_scan_test_email = agents_serivce_pb2.LoadReplyRequest(
    reply_email=create_email(
        subject="RE: Load Details Request",
        body="<p>Rate: $2,000, Commodity: General Freight, Weight: 45,000 lbs, Equipment: DRY_VAN, Pickup Location: New York, NY, Delivery Location: Boston, MA</p>",
        thread_id="thread_load_scan"
    ),
    origin_email=create_email(
        subject="Load Details Request",
        body="<p>Need details for this load</p>",
        thread_id="thread_load_scan"
    ),
    application_name="test_integration_app",
    company_details=create_company_details(name="Load Scan Transport", mc_number="MC-LOADSCAN"),
    load_id="load_scan",
    thread_id="thread_load_scan",
    email_id="email_load_scan",
    load=create_load(
        load_id="load_scan",
        origin_city="New York",
        origin_state="NY",
        dest_city="Boston",
        dest_state="MA",
        rate=2000.0
    ),
    truck_id="truck_load_scan",
    truck=create_truck(truck_id="T-LOADSCAN", equipment_type="DRY_VAN")
)

# Custom test email for rate_negotiator test
rate_negotiator_test_email = agents_serivce_pb2.LoadReplyRequest(
    reply_email=create_email(
        subject="RE: Rate Offer",
        body="<p>We can offer $4,000 for this load.</p>",
        thread_id="thread_rate"
    ),
    origin_email=create_email(
        subject="Rate Offer",
        body="<p>What's your best rate?</p>",
        thread_id="thread_rate"
    ),
    application_name="test_integration_app",
    company_details=create_company_details(
        name="Rate Negotiator Transport",
        mc_number="MC-RATE"
    ),
    load_id="load_rate",
    thread_id="thread_rate",
    email_id="email_rate",
    load=create_load(
        load_id="load_rate",
        origin_city="Chicago",
        origin_state="IL",
        dest_city="Detroit",
        dest_state="MI",
        rate=5000.0
    ),
    truck_id="truck_rate",
    truck=create_truck(truck_id="T-RATE")
)
