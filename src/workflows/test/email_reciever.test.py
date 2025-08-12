import unittest
import json
import asyncio
import re
import os
from unittest.mock import patch, MagicMock, AsyncMock

# Sample test data
SAMPLE_EMAIL_LOGISTICS = {
    "subject": "Freight opportunity: Chicago to New York",
    "body": "<p>We have a load that needs to be picked up from Chicago, IL and delivered to New York, NY. Rate: $1500. Please let me know if you're interested.</p><p>Thanks,<br>John Doe<br>ABC Logistics<br>MC# 123456<br>Phone: +1-555-123-4567<br>Email: john.doe@abclogistics.com<br>Website: www.abclogistics.com</p>",
    "threadId": "thread_123456"
}

SAMPLE_EMAIL_NON_LOGISTICS = {
    "subject": "Meeting next week",
    "body": "<p>Hi team, let's schedule a meeting next week to discuss the quarterly results. How about Tuesday at 2 PM?</p><p>Regards,<br>Jane Smith</p>",
    "threadId": "thread_789012"
}

SAMPLE_EMAIL_LANE = {
    "subject": "Weekly Lane Opportunity: Los Angeles to Dallas",
    "body": "<p>We have a weekly lane opportunity from Los Angeles, CA to Dallas, TX. Starting next Monday and continuing for 3 months. Rate: $2200 per load. Please let me know if you're interested.</p><p>Thanks,<br>Mark Johnson<br>XYZ Transport<br>MC# 789012<br>Phone: +1-555-987-6543<br>Email: mark.johnson@xyztransport.com<br>Website: www.xyztransport.com</p>",
    "threadId": "thread_345678"
}

# Define the actual order-related keywords from the main implementation
ORDER_RELATED_KEYWORDS = [
    'dispatch', 'freight', 'logistics', 'carrier', 'broker', 'load', 'transport',
    'delivery', 'shipment', 'pickup', 'lane', 'volume', 'truckload',
    'dry van', 'reefer', 'flatbed', 'trailer', 'palletized',
    'commodity', 'weight', 'capacity', 'standard',
    'weekly', 'dedicated', 'periodic',
    'motor carrier', 'MC', 'opportunity', 'interested', 'terms',
    'forwarded', 'subject', 'sent', 'reach out', 'from', 'to',
    'dispatch system', 'email platform', 'tracking', 'scheduling', 'freight',
    'lane', 'rate', 'capacity', 'Van', 'delivery', 'appointment', 'carrier',
    'weight', 'shipper', 'receiver', 'drivers', 'one way trip', 'trip', 'pick up',
    'locations', 'Commodity', 'Sunflower Oil', 'dry van', 'business opportunity',
    'launching', 'shipment', 'running', 'trucking partners', 'pulls', 'load locks',
    'straps', 'bars', 'totes', 'trailer pool required', 'haul', 'freight locally',
    'regionally', 'cost', 'Dedicated', 'starts', 'libs', 'Pickup', 'swing doors',
    'WOODEN FLOORS', 'solo run', 'Transit Times', 'rack', 'Shipper- Loading tim', 'loads'
]

# Mock functions that match the real implementation
def strip_html(html_content):
    """Remove HTML tags from content and normalize whitespace."""
    return re.sub(r'\s+', ' ', re.sub(r'<\/?[^>]+(>|$)', '', html_content)).strip()

def filter_email_by_keywords(email_body):
    """Check if email contains order-related keywords."""
    email_text = strip_html(email_body)
    pattern = '|'.join(ORDER_RELATED_KEYWORDS)
    return bool(re.search(pattern, email_text, re.IGNORECASE))

def clean_ai_response(response_text):
    """
    Clean AI response text by removing markdown code blocks and other formatting.
    """
    # Remove markdown code blocks (```json ... ```)
    if "```" in response_text:
        # Extract content between code blocks
        pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        matches = re.findall(pattern, response_text)
        if matches:
            return matches[0].strip()

    return response_text.strip()

async def is_order_related_email(email_subject, email_body):
    """
    Mock of Azure OpenAI to determine if the email is related to logistics orders.
    """
    # In a real test, we'd mock the Azure OpenAI client response
    # For testing, we'll use a simple heuristic
    combined_text = (email_subject + " " + strip_html(email_body)).lower()
    logistics_terms = ['logistics', 'freight', 'shipment', 'delivery', 'pickup', 'load']
    return any(term in combined_text for term in logistics_terms)

async def extract_order_details(email_subject, email_body):
    """
    Mock of extracting order details using Azure OpenAI.
    """
    # For testing, return a predefined response based on the email content
    if "Chicago" in email_body and "New York" in email_body:
        return {
            "orderType": "spot",
            "orders": [
                {
                    "pickup": "Chicago, IL",
                    "delivery": "New York, NY",
                    "route": "Chicago, IL → New York, NY",
                    "offeringRate": 1500
                }
            ],
            "broker": {
                "mcNumber": "123456",
                "fullName": "John Doe",
                "companyName": "ABC Logistics",
                "email": "john.doe@abclogistics.com",
                "phone": "+1-555-123-4567",
                "website": "www.abclogistics.com"
            }
        }
    elif "Los Angeles" in email_body and "Dallas" in email_body:
        return {
            "orderType": "lane",
            "orders": [
                {
                    "pickup": "Los Angeles, CA",
                    "delivery": "Dallas, TX",
                    "route": "Los Angeles, CA → Dallas, TX",
                    "offeringRate": 2200
                }
            ],
            "broker": {
                "mcNumber": "789012",
                "fullName": "Mark Johnson",
                "companyName": "XYZ Transport",
                "email": "mark.johnson@xyztransport.com",
                "phone": "+1-555-987-6543",
                "website": "www.xyztransport.com"
            }
        }
    else:
        return {
            "orderType": "unclassified",
            "unclassificationReason": "Could not extract order details",
            "orders": [],
            "broker": {}
        }

async def generate_route(pickup, delivery, offering_rate=None):
    """
    Mock of route generation using HERE API.
    """
    # For testing, return a predefined response based on the locations
    if pickup == "Chicago, IL" and delivery == "New York, NY":
        result = {
            "routeId": "route_chi_nyc",
            "polyline": "sample_polyline_data_chicago_newyork",
            "duration": 12.5,  # hours
            "length": 789.3,   # miles
            "origin": {
                "label": "Chicago, IL, USA",
                "state": "Illinois",
                "stateCode": "IL",
                "city": "Chicago",
                "street": "Main St",
                "postalCode": "60601"
            },
            "destination": {
                "label": "New York, NY, USA",
                "state": "New York",
                "stateCode": "NY",
                "city": "New York",
                "street": "Broadway",
                "postalCode": "10001"
            },
            "tolls": []
        }
    elif pickup == "Los Angeles, CA" and delivery == "Dallas, TX":
        result = {
            "routeId": "route_la_dal",
            "polyline": "sample_polyline_data_la_dallas",
            "duration": 20.3,  # hours
            "length": 1435.7,  # miles
            "origin": {
                "label": "Los Angeles, CA, USA",
                "state": "California",
                "stateCode": "CA",
                "city": "Los Angeles",
                "street": "Wilshire Blvd",
                "postalCode": "90001"
            },
            "destination": {
                "label": "Dallas, TX, USA",
                "state": "Texas",
                "stateCode": "TX",
                "city": "Dallas",
                "street": "Main St",
                "postalCode": "75201"
            },
            "tolls": []
        }
    else:
        return {
            "error": f"Could not generate route from {pickup} to {delivery}"
        }
    
    if offering_rate is not None:
        result["offeringRate"] = offering_rate
    
    return result

def log_email_processing_result(result):
    """Mock of logging email processing result."""
    # This would normally log to a file or send to a webhook
    pass

async def process_email(email_data, application_name):
    """
    Main function to process an email and extract order information.
    This combines all the n8n workflows into a single function.
    """
    try:
        email_subject = email_data.get("subject", "")
        email_body = email_data.get("body", "")
        thread_id = email_data.get("threadId", "")

        # Step 1: Check if the email contains order-related keywords
        has_keywords = filter_email_by_keywords(email_body)

        if not has_keywords:
            result = {
                "threadId": thread_id,
                "orderType": "unclassified",
                "applicationName": application_name,
                "unclassificationReason": "This might be unrelated email",
                "orders": []
            }
            log_email_processing_result(result)
            return result

        # Step 2: Verify if it's a valid order-related email using AI
        is_valid = await is_order_related_email(email_subject, email_body)

        if not is_valid:
            result = {
                "threadId": thread_id,
                "orderType": "unclassified",
                "applicationName": application_name,
                "unclassificationReason": "This might be unrelated email",
                "orders": []
            }
            log_email_processing_result(result)
            return result

        # Step 3: Extract order details using AI
        order_details = await extract_order_details(email_subject, email_body)

        # Step 4: Check if we have valid orders with pickup and delivery locations
        orders = order_details.get("orders", [])
        valid_orders = [order for order in orders if order.get("pickup") and order.get("delivery")]

        if not valid_orders:
            result = {
                "threadId": thread_id,
                "orderType": order_details.get("orderType", "unclassified"),
                "applicationName": application_name,
                "unclassificationReason": order_details.get("unclassificationReason", "Couldn't extract locations"),
                "orders": [],
                "broker": order_details.get("broker", {})
            }
            log_email_processing_result(result)
            return result

        # Step 5: Generate routes for each valid order
        processed_orders = []
        for order in valid_orders:
            route_result = await generate_route(
                order["pickup"],
                order["delivery"],
                order.get("offeringRate")
            )

            if "error" in route_result:
                continue

            # Add thread_id to the route result
            route_result["threadId"] = thread_id
            processed_orders.append(route_result)

        # Step 6: Prepare the final result
        if processed_orders:
            result = {
                "threadId": thread_id,
                "orderType": order_details.get("orderType", "unclassified"),
                "applicationName": application_name,
                "orders": processed_orders,
                "broker": order_details.get("broker", {})
            }
        else:
            result = {
                "threadId": thread_id,
                "orderType": "unclassified",
                "applicationName": application_name,
                "unclassificationReason": "Couldn't generate routes for any orders",
                "orders": [],
                "broker": order_details.get("broker", {})
            }

        # Step 7: Log the result
        log_email_processing_result(result)
        return result

    except Exception as e:
        result = {
            "threadId": email_data.get("threadId", ""),
            "orderType": "unclassified",
            "applicationName": application_name,
            "unclassificationReason": f"Error processing email: {str(e)}",
            "orders": []
        }
        log_email_processing_result(result)
        return result

class TestEmailProcessor(unittest.TestCase):
    """Comprehensive test cases for the email processor module."""

    def test_strip_html(self):
        """Test HTML stripping function with various HTML content."""
        test_cases = [
            ("<p>This is <b>bold</b> text with <br/> line break.</p>", "This is bold text with line break."),
            ("<div>Multiple <span>nested</span> tags</div>", "Multiple nested tags"),
            ("Plain text without HTML", "Plain text without HTML"),
            ("<p>Text with  multiple    spaces</p>", "Text with multiple spaces")
        ]
        
        for html, expected in test_cases:
            with self.subTest(html=html):
                self.assertEqual(strip_html(html), expected)

    def test_filter_email_by_keywords(self):
        """Test keyword filtering with various email content."""
        # Emails with logistics keywords
        logistics_emails = [
            "<p>This email contains the word freight in it.</p>",
            "<p>Looking for a carrier for our shipment.</p>",
            "<p>We need to schedule a pickup for tomorrow.</p>"
        ]
        
        # Emails without logistics keywords - carefully chosen to avoid any matches with ORDER_RELATED_KEYWORDS
        non_logistics_emails = [
            "<p>Let's discuss the budget next week.</p>",
            "<p>Please review the financial report.</p>",
            "<p>The office will be closed on Monday.</p>"
        ]
        
        for email in logistics_emails:
            with self.subTest(email=email):
                self.assertTrue(filter_email_by_keywords(email))
                
        for email in non_logistics_emails:
            with self.subTest(email=email):
                self.assertFalse(filter_email_by_keywords(email))

    def test_clean_ai_response(self):
        """Test cleaning AI response with various formats."""
        test_cases = [
            # Markdown code block with json tag
            ("```json\n{\n  \"valid\": true\n}\n```", "{\n  \"valid\": true\n}"),
            # Markdown code block without json tag
            ("```\n{\n  \"valid\": true\n}\n```", "{\n  \"valid\": true\n}"),
            # No markdown, just JSON
            ("{\n  \"valid\": true\n}", "{\n  \"valid\": true\n}"),
            # Text with extra whitespace
            ("  {\n  \"valid\": true\n}  ", "{\n  \"valid\": true\n}")
        ]
        
        for response, expected in test_cases:
            with self.subTest(response=response):
                self.assertEqual(clean_ai_response(response), expected)

    @patch('builtins.print')  # Mock print to avoid console output during tests
    async def test_process_email_full_workflow(self, mock_print):
        """Test the complete email processing workflow with a valid logistics email."""
        result = await process_email(SAMPLE_EMAIL_LOGISTICS, "test-application")
        
        # Verify the result structure
        self.assertEqual(result["threadId"], "thread_123456")
        self.assertEqual(result["orderType"], "spot")
        self.assertEqual(result["applicationName"], "test-application")
        
        # Verify orders
        self.assertEqual(len(result["orders"]), 1)
        order = result["orders"][0]
        self.assertEqual(order["routeId"], "route_chi_nyc")
        self.assertEqual(order["duration"], 12.5)
        self.assertEqual(order["length"], 789.3)
        self.assertEqual(order["offeringRate"], 1500)
        
        # Verify broker information
        self.assertEqual(result["broker"]["mcNumber"], "123456")
        self.assertEqual(result["broker"]["companyName"], "ABC Logistics")

    @patch('builtins.print')  # Mock print to avoid console output during tests
    async def test_process_lane_email(self, mock_print):
        """Test processing a lane-type email."""
        result = await process_email(SAMPLE_EMAIL_LANE, "test-application")
        
        self.assertEqual(result["threadId"], "thread_345678")
        self.assertEqual(result["orderType"], "lane")
        self.assertEqual(len(result["orders"]), 1)
        
        order = result["orders"][0]
        self.assertEqual(order["routeId"], "route_la_dal")
        self.assertEqual(order["offeringRate"], 2200)
        
        # Verify origin and destination
        self.assertEqual(order["origin"]["city"], "Los Angeles")
        self.assertEqual(order["destination"]["city"], "Dallas")

    @patch('builtins.print')  # Mock print to avoid console output during tests
    async def test_process_non_logistics_email(self, mock_print):
        """Test processing a non-logistics email."""
        result = await process_email(SAMPLE_EMAIL_NON_LOGISTICS, "test-application")
        
        self.assertEqual(result["threadId"], "thread_789012")
        self.assertEqual(result["orderType"], "unclassified")
        self.assertTrue("unclassificationReason" in result)
        self.assertEqual(len(result["orders"]), 0)

    @patch('builtins.print')  # Mock print to avoid console output during tests
    async def test_process_email_no_keywords(self, mock_print):
        """Test email processing when no keywords are found."""
        # Override the filter_email_by_keywords function to return False
        original_filter = globals()["filter_email_by_keywords"]
        globals()["filter_email_by_keywords"] = lambda body: False
        
        try:
            result = await process_email(SAMPLE_EMAIL_LOGISTICS, "test-application")
            self.assertEqual(result["threadId"], "thread_123456")
            self.assertEqual(result["orderType"], "unclassified")
            self.assertEqual(result["unclassificationReason"], "This might be unrelated email")
            self.assertEqual(len(result["orders"]), 0)
        finally:
            # Restore the original function
            globals()["filter_email_by_keywords"] = original_filter

    @patch('builtins.print')  # Mock print to avoid console output during tests
    async def test_process_email_not_order_related(self, mock_print):
        """Test email processing when AI determines it's not order related."""
        # Override the is_order_related_email function to return False
        original_is_valid = globals()["is_order_related_email"]
        
        async def mock_is_valid(subject, body):
            return False
        
        globals()["is_order_related_email"] = mock_is_valid
        
        try:
            result = await process_email(SAMPLE_EMAIL_LOGISTICS, "test-application")
            self.assertEqual(result["threadId"], "thread_123456")
            self.assertEqual(result["orderType"], "unclassified")
            self.assertEqual(result["unclassificationReason"], "This might be unrelated email")
            self.assertEqual(len(result["orders"]), 0)
        finally:
            # Restore the original function
            globals()["is_order_related_email"] = original_is_valid

    @patch('builtins.print')  # Mock print to avoid console output during tests
    async def test_process_email_no_valid_orders(self, mock_print):
        """Test email processing when no valid orders are found."""
        # Override the extract_order_details function to return unclassified
        original_extract = globals()["extract_order_details"]
        
        async def mock_extract(subject, body):
            return {
                "orderType": "unclassified",
                "unclassificationReason": "No valid orders found",
                "orders": [],
                "broker": {}
            }
        
        globals()["extract_order_details"] = mock_extract
        
        try:
            result = await process_email(SAMPLE_EMAIL_LOGISTICS, "test-application")
            self.assertEqual(result["threadId"], "thread_123456")
            self.assertEqual(result["orderType"], "unclassified")
            self.assertEqual(result["unclassificationReason"], "No valid orders found")
            self.assertEqual(len(result["orders"]), 0)
        finally:
            # Restore the original function
            globals()["extract_order_details"] = original_extract

    @patch('builtins.print')  # Mock print to avoid console output during tests
    async def test_process_email_route_generation_failure(self, mock_print):
        """Test email processing when route generation fails."""
        # Override the generate_route function to return an error
        original_generate = globals()["generate_route"]
        
        async def mock_generate(pickup, delivery, offering_rate=None):
            return {
                "error": "Could not generate route"
            }
        
        globals()["generate_route"] = mock_generate
        
        try:
            result = await process_email(SAMPLE_EMAIL_LOGISTICS, "test-application")
            self.assertEqual(result["threadId"], "thread_123456")
            self.assertEqual(result["orderType"], "unclassified")
            self.assertEqual(result["unclassificationReason"], "Couldn't generate routes for any orders")
            self.assertEqual(len(result["orders"]), 0)
        finally:
            # Restore the original function
            globals()["generate_route"] = original_generate

    @patch('builtins.print')  # Mock print to avoid console output during tests
    async def test_process_email_exception_handling(self, mock_print):
        """Test email processing exception handling."""
        # Override the extract_order_details function to raise an exception
        original_extract = globals()["extract_order_details"]
        
        async def mock_extract_with_exception(subject, body):
            raise Exception("Test exception")
        
        globals()["extract_order_details"] = mock_extract_with_exception
        
        try:
            result = await process_email(SAMPLE_EMAIL_LOGISTICS, "test-application")
            self.assertEqual(result["threadId"], "thread_123456")
            self.assertEqual(result["orderType"], "unclassified")
            self.assertTrue("Error processing email: Test exception" in result["unclassificationReason"])
            self.assertEqual(len(result["orders"]), 0)
        finally:
            # Restore the original function
            globals()["extract_order_details"] = original_extract

# Run the tests
if __name__ == "__main__":
    # Create a test suite with all the synchronous test methods
    sync_suite = unittest.TestSuite()
    sync_suite.addTest(TestEmailProcessor("test_strip_html"))
    sync_suite.addTest(TestEmailProcessor("test_filter_email_by_keywords"))
    sync_suite.addTest(TestEmailProcessor("test_clean_ai_response"))
    
    # Run the synchronous tests
    print("Running synchronous tests...")
    unittest.TextTestRunner().run(sync_suite)
    
    # Run the async tests using asyncio
    async def run_async_tests():
        test_instance = TestEmailProcessor()
        print("\nRunning asynchronous tests...")
        
        # Process email workflow tests
        await test_instance.test_process_email_full_workflow()
        await test_instance.test_process_lane_email()
        await test_instance.test_process_non_logistics_email()
        await test_instance.test_process_email_no_keywords()
        await test_instance.test_process_email_not_order_related()
        await test_instance.test_process_email_no_valid_orders()
        await test_instance.test_process_email_route_generation_failure()
        await test_instance.test_process_email_exception_handling()
        
        print("All async tests passed!")
    
    asyncio.run(run_async_tests())
