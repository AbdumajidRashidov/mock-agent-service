#!/usr/bin/env python3
"""
Enhanced Demo Script - Pydantic AI Freight Processor
Comprehensive demonstration of all freight negotiation scenarios
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from workflows.load_reply_processor_pydantic_ai.main import process_reply


class EnhancedFreightProcessorDemo:
    """Enhanced demo class showcasing comprehensive freight processor capabilities"""

    def __init__(self):
        self.demo_count = 0

    def print_header(self, title: str, scenario: str):
        """Print formatted header"""
        print(f"\n{'='*80}")
        print(f"🚛 FREIGHT PROCESSOR DEMO #{self.demo_count + 1}")
        print(f"📋 SCENARIO: {title}")
        print(f"📄 DESCRIPTION: {scenario}")
        print(f"{'='*80}")
        self.demo_count += 1

    def print_section(self, title: str):
        """Print section header"""
        print(f"\n🔸 {title}")
        print("-" * 50)

    async def response_callback(self, response):
        """Callback to show real-time processing"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = response.get('message', 'Processing...')
        print(f"[{timestamp}] ⚡ {message}")

        # Show plugin responses
        if 'plugin_response' in response:
            plugin = response['plugin_response']
            print(f"    🔧 Plugin: {plugin['plugin_name']} - {'✅ Success' if plugin['success'] else '❌ Failed'}")

        # Show field updates
        if 'field_updates' in response and response['field_updates']:
            print(f"    📝 Field updates: {len(response['field_updates'])} changes")

    def show_input_data(self, company, truck, load, emails):
        """Display input data in a readable format"""
        self.print_section("INPUT DATA")

        print(f"🏢 Company: {company['name']} (MC: {company['mcNumber']})")
        print(f"🚚 Truck: Max {truck['maxWeight']:,} lbs, {truck['maxLength']}ft")
        print(f"📦 Load: {load['origin']['city']}, {load['origin']['stateProv']} → {load['destination']['city']}, {load['destination']['stateProv']}")
        print(f"💰 Rate Range: ${load['rateInfo']['minimumRate']:,} - ${load['rateInfo']['maximumRate']:,}")
        print(f"📧 Email Thread: {len(emails)} messages")

        print(f"\n📨 EMAIL CONVERSATION:")
        for i, email in enumerate(emails, 1):
            sender = email['from'][0]['email']
            is_our_email = sender in ["dispatch@loadmodellc.com"]
            sender_type = "🔵 Us" if is_our_email else "🔴 Broker"
            print(f"  {i}. {sender_type}: {email['subject']}")
            body_preview = email['body'].replace('<br>', ' ').replace('\n', ' ')[:60]
            print(f"     💬 \"{body_preview}{'...' if len(body_preview) == 60 else ''}\"")

    def show_result(self, result):
        """Display processing results"""
        self.print_section("PROCESSING RESULT")

        print(f"📋 Status: {result['message']}")

        if result.get('email_to_send'):
            print(f"📧 Generated Email: ✅ YES")
            print(f"📝 Email Preview:")
            email_lines = result['email_to_send'].split('\n')[:5]
            for line in email_lines:
                print(f"    {line}")
            if len(result['email_to_send'].split('\n')) > 5:
                print("    [... truncated ...]")
        else:
            print(f"📧 Generated Email: ❌ NO")

        if result.get('field_updates'):
            print(f"📊 Database Updates: {len(result['field_updates'])} fields")
            for field, value in list(result['field_updates'].items())[:3]:
                print(f"    • {field}: {value}")
            if len(result['field_updates']) > 3:
                print(f"    • ... and {len(result['field_updates']) - 3} more")
        else:
            print(f"📊 Database Updates: None")

    # Original demos (keeping all 4)
    async def run_demo_1_info_request(self):
        """Demo 1: Basic information request"""
        self.print_header(
            "Basic Information Request",
            "Broker responds with load details, we ask for missing info"
        )

        # Realistic test data
        company_details = {
            "name": "Load Model LLC",
            "mcNumber": "1242119",
            "phone": "(555) 123-4567",
            "address": "123 Freight St, Dallas, TX 75001"
        }

        our_emails = ["dispatch@loadmodellc.com"]

        truck = {
            "maxWeight": 80000,
            "maxLength": 53,
            "restrictions": ["hazmat"],
            "isPermitted": {
                "refrigerated": True,
                "hazmat": False
            },
            "security": {
                "gpsTracking": True,
                "cargoInsurance": True
            }
        }

        load = {
            "id": "DEMO-001",
            "status": "active",
            "origin": {"city": "Los Angeles", "stateProv": "CA"},
            "destination": {"city": "Chicago", "stateProv": "IL"},
            "rateInfo": {
                "minimumRate": 3000,
                "maximumRate": 4000
            },
            "emailHistory": {
                "details": {},
                "negotitationStep": 0,
            },
            "warnings": []
        }

        emails = [
            {
                "id": "1",
                "subject": "LA to Chicago Load - Need Info",
                "body": "Hello, need more details on this load please. MC 1242119",
                "from": [{"email": "dispatch@loadmodellc.com", "name": "Dispatch Team"}]
            },
            {
                "id": "2",
                "subject": "Re: LA to Chicago Load - Need Info",
                "body": "It's a van load, 45,000 lbs of electronics. Pick up tomorrow 8AM-5PM, delivery Wednesday by 6PM. What's your rate?",
                "from": [{"email": "broker@electronics.com", "name": "John Broker"}]
            }
        ]

        self.show_input_data(company_details, truck, load, emails)

        self.print_section("PROCESSING FLOW")
        result = await process_reply(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            response_callback=self.response_callback
        )

        self.show_result(result)

        print(f"\n✨ EXPECTED OUTCOME: System should extract commodity (electronics), weight (45000), "
              f"and ask broker about delivery date specifics and rate expectations.")

    async def run_demo_2_rate_negotiation(self):
        """Demo 2: Rate negotiation scenario"""
        self.print_header(
            "Rate Negotiation",
            "Broker offers a rate, we counter-negotiate based on our range"
        )

        company_details = {
            "name": "Load Model LLC",
            "mcNumber": "1242119",
            "rateNegotiation": {
                "firstBidThreshold": 75,
                "secondBidThreshold": 50,
                "rounding": 25
            }
        }

        our_emails = ["dispatch@loadmodellc.com"]

        truck = {"maxWeight": 80000, "maxLength": 53, "restrictions": []}

        load = {
            "id": "DEMO-002",
            "status": "active",
            "origin": {"city": "Houston", "stateProv": "TX"},
            "destination": {"city": "Miami", "stateProv": "FL"},
            "equipmentType": "v",
            "rateInfo": {
                "minimumRate": 2000,
                "maximumRate": 3000
            },
            "emailHistory": {
                "details": {
                    "commodity": "auto parts",
                    "weight": "38000"
                },
                "negotitationStep": 1,
            }
        }

        emails = [
            {
                "id": "1",
                "subject": "Houston to Miami - Rate Request",
                "body": "What's your best rate for this Houston to Miami load?",
                "from": [{"email": "dispatch@loadmodellc.com", "name": "Load Model"}]
            },
            {
                "id": "2",
                "subject": "Re: Houston to Miami - Rate Request",
                "body": "Van load, 38k lbs auto parts. I can do $2300 for this. Let me know if you want it.",
                "from": [{"email": "sarah@autofreight.com", "name": "Sarah Johnson"}]
            }
        ]

        self.show_input_data(company_details, truck, load, emails)

        self.print_section("PROCESSING FLOW")
        result = await process_reply(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            response_callback=self.response_callback
        )

        self.show_result(result)

        rate_range = 3000 - 2000
        first_bid = 2000 + (rate_range * 0.75)
        expected_rate = round(first_bid / 25) * 25

        print(f"\n✨ EXPECTED OUTCOME: System should detect broker's $2300 offer is below our "
              f"calculated counter-offer of ~${expected_rate}, so we should negotiate higher.")

    async def run_demo_3_questions_and_answers(self):
        """Demo 3: Question answering scenario"""
        self.print_header(
            "Question & Answer",
            "Broker asks multiple questions, we provide answers from company data"
        )

        company_details = {
            "name": "Load Model LLC",
            "mcNumber": "1242119",
            "phone": "(555) 123-4567",
            "address": "123 Freight Street, Dallas, TX 75001",
            "details": "DOT compliant carrier with 5+ years experience, GPS tracking on all vehicles"
        }

        our_emails = ["dispatch@loadmodellc.com"]

        truck = {
            "maxWeight": 80000,
            "maxLength": 53,
            "isPermitted": {"hazmat": False, "refrigerated": True},
            "security": {"gpsTracking": True, "cargoInsurance": True}
        }

        load = {
            "id": "DEMO-003",
            "status": "active",
            "origin": {"city": "Seattle", "stateProv": "WA"},
            "destination": {"city": "Portland", "stateProv": "OR"},
            "rateInfo": {
                "minimumRate": 800,
                "maximumRate": 1200
            },
            "emailHistory": {
                "details": {},
                "negotitationStep": 0,
            },
            "warnings": []
        }

        emails = [
            {
                "id": "1",
                "subject": "Seattle to Portland Load Inquiry",
                "body": "Hi, interested in this short haul load. Can you send details?",
                "from": [{"email": "dispatch@loadmodellc.com", "name": "Load Model"}]
            },
            {
                "id": "2",
                "subject": "Re: Seattle to Portland Load Inquiry",
                "body": "Before I give details, I need: What's your MC number? What's the load reference ID? Do you have GPS tracking? What's your company phone number?",
                "from": [{"email": "quick@northwest.com", "name": "NW Quick Freight"}]
            }
        ]

        self.show_input_data(company_details, truck, load, emails)

        self.print_section("PROCESSING FLOW")
        result = await process_reply(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            response_callback=self.response_callback
        )

        self.show_result(result)

        print(f"\n✨ EXPECTED OUTCOME: System should answer all questions with: MC 1242119, "
              f"Load ID DEMO-003, GPS tracking: Yes, Phone: (555) 123-4567")

    async def run_demo_4_cancellation(self):
        """Demo 4: Load cancellation detection"""
        self.print_header(
            "Load Cancellation",
            "Broker cancels the load, system should detect and update status"
        )

        company_details = {"name": "Load Model LLC", "mcNumber": "1242119"}
        our_emails = ["dispatch@loadmodellc.com"]
        truck = {"maxWeight": 80000, "maxLength": 53, "restrictions": []}

        load = {
            "id": "DEMO-004",
            "status": "active",
            "origin": {"city": "Phoenix", "stateProv": "AZ"},
            "destination": {"city": "Denver", "stateProv": "CO"},
            "rateInfo": {
                "minimumRate": 2000,
                "maximumRate": 2800
            },
            "emailHistory": {
                "details": {},
                "negotitationStep": 0,
            },
            "warnings": []
        }

        emails = [
            {
                "id": "1",
                "subject": "Phoenix to Denver - Can you do $2400?",
                "body": "Hi, can you handle this Phoenix to Denver load for $2400?",
                "from": [{"email": "dispatch@loadmodellc.com", "name": "Load Model"}]
            },
            {
                "id": "2",
                "subject": "Re: Phoenix to Denver - Can you do $2400?",
                "body": "Sorry, this load is gone. It was already covered by another carrier this morning. Thanks for your interest though.",
                "from": [{"email": "mountain@freight.com", "name": "Mountain Freight"}]
            }
        ]

        self.show_input_data(company_details, truck, load, emails)

        self.print_section("PROCESSING FLOW")
        result = await process_reply(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            response_callback=self.response_callback
        )

        self.show_result(result)

        print(f"\n✨ EXPECTED OUTCOME: System should detect cancellation keywords ('load is gone', "
              f"'already covered') and mark load status as 'cancelled'")

    # NEW ENHANCED DEMOS
    async def run_demo_5_requirements_violation(self):
        """Demo 5: Requirements violation detection"""
        self.print_header(
            "Requirements Violation",
            "Load requires hazmat permit but truck is not certified"
        )

        company_details = {
            "name": "Load Model LLC",
            "mcNumber": "1242119",
            "phone": "(555) 123-4567"
        }

        our_emails = ["dispatch@loadmodellc.com"]

        truck = {
            "maxWeight": 80000,
            "maxLength": 53,
            "restrictions": ["hazmat", "chemicals"],
            "isPermitted": {
                "hazmat": False,  # NOT hazmat certified
                "refrigerated": True
            },
            "security": {
                "gpsTracking": True,
                "cargoInsurance": True
            }
        }

        load = {
            "id": "DEMO-005",
            "status": "active",
            "origin": {"city": "Houston", "stateProv": "TX"},
            "destination": {"city": "New Orleans", "stateProv": "LA"},
            "equipmentType": "v",
            "rateInfo": {
                "minimumRate": 2500,
                "maximumRate": 3500
            },
            "emailHistory": {
                "details": {
                    "commodity": "industrial chemicals",
                    "weight": "42000"
                },
                "negotitationStep": 0,
            },
            "warnings": []
        }

        emails = [
            {
                "id": "1",
                "subject": "Hazmat Load Houston to New Orleans",
                "body": "Need a van for industrial chemicals, 42k lbs. Hazmat required. Rate $3200.",
                "from": [{"email": "broker@chemfreight.com", "name": "Chemical Freight"}]
            }
        ]

        self.show_input_data(company_details, truck, load, emails)

        self.print_section("PROCESSING FLOW")
        result = await process_reply(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            response_callback=self.response_callback
        )

        self.show_result(result)

        print(f"\n✨ EXPECTED OUTCOME: System should detect hazmat requirement violation - "
              f"load needs hazmat permit but truck doesn't have it")

    async def run_demo_6_weight_overload(self):
        """Demo 6: Weight capacity violation"""
        self.print_header(
            "Weight Capacity Violation",
            "Load weight exceeds truck's maximum capacity"
        )

        company_details = {
            "name": "Load Model LLC",
            "mcNumber": "1242119"
        }

        our_emails = ["dispatch@loadmodellc.com"]

        truck = {
            "maxWeight": 45000,  # Smaller truck
            "maxLength": 40,
            "restrictions": [],
            "isPermitted": {"hazmat": False, "refrigerated": False}
        }

        load = {
            "id": "DEMO-006",
            "status": "active",
            "origin": {"city": "Detroit", "stateProv": "MI"},
            "destination": {"city": "Atlanta", "stateProv": "GA"},
            "equipmentType": "v",
            "rateInfo": {
                "minimumRate": 1800,
                "maximumRate": 2400
            },
            "emailHistory": {
                "details": {
                    "commodity": "steel parts",
                    "weight": "52000"  # Exceeds truck capacity
                },
                "negotitationStep": 0,
            },
            "warnings": []
        }

        emails = [
            {
                "id": "1",
                "subject": "Heavy Steel Load Detroit to Atlanta",
                "body": "Van load, 52,000 lbs of steel automotive parts. Can you handle this?",
                "from": [{"email": "steel@manufacturing.com", "name": "Steel Manufacturing"}]
            }
        ]

        self.show_input_data(company_details, truck, load, emails)

        self.print_section("PROCESSING FLOW")
        result = await process_reply(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            response_callback=self.response_callback
        )

        self.show_result(result)

        print(f"\n✨ EXPECTED OUTCOME: System should detect weight violation - "
              f"52,000 lbs load exceeds truck's 45,000 lbs capacity")

    async def run_demo_7_successful_negotiation(self):
        """Demo 7: Successful rate negotiation acceptance"""
        self.print_header(
            "Successful Negotiation",
            "Broker accepts our counter-offer rate"
        )

        company_details = {
            "name": "Load Model LLC",
            "mcNumber": "1242119",
            "rateNegotiation": {
                "firstBidThreshold": 70,
                "secondBidThreshold": 45,
                "rounding": 50
            }
        }

        our_emails = ["dispatch@loadmodellc.com"]

        truck = {"maxWeight": 80000, "maxLength": 53}

        load = {
            "id": "DEMO-007",
            "status": "active",
            "origin": {"city": "Portland", "stateProv": "OR"},
            "destination": {"city": "Las Vegas", "stateProv": "NV"},
            "equipmentType": "v",
            "rateInfo": {
                "minimumRate": 2200,
                "maximumRate": 3200
            },
            "emailHistory": {
                "details": {
                    "commodity": "furniture",
                    "weight": "35000"
                },
                "negotitationStep": 1,
            }
        }

        emails = [
            {
                "id": "1",
                "subject": "Portland to Vegas Furniture Load",
                "body": "How about $2900 for this furniture load?",
                "from": [{"email": "dispatch@loadmodellc.com", "name": "Load Model"}]
            },
            {
                "id": "2",
                "subject": "Re: Portland to Vegas Furniture Load",
                "body": "That works! $2900 is approved. Please send your driver info and pickup time. Load is confirmed.",
                "from": [{"email": "furniture@logistics.com", "name": "Furniture Logistics"}]
            }
        ]

        self.show_input_data(company_details, truck, load, emails)

        self.print_section("PROCESSING FLOW")
        result = await process_reply(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            response_callback=self.response_callback
        )

        self.show_result(result)

        print(f"\n✨ EXPECTED OUTCOME: System should detect broker approval of our $2900 rate "
              f"and mark negotiation as successful")

    async def run_demo_8_equipment_mismatch(self):
        """Demo 8: Equipment type mismatch"""
        self.print_header(
            "Equipment Mismatch",
            "Load requires reefer but truck is dry van"
        )

        company_details = {
            "name": "Load Model LLC",
            "mcNumber": "1242119"
        }

        our_emails = ["dispatch@loadmodellc.com"]

        truck = {
            "maxWeight": 80000,
            "maxLength": 53,
            "equipmentType": "v",  # Dry van
            "isPermitted": {
                "refrigerated": False,  # Not refrigerated
                "hazmat": False
            }
        }

        load = {
            "id": "DEMO-008",
            "status": "active",
            "origin": {"city": "Fresno", "stateProv": "CA"},
            "destination": {"city": "Dallas", "stateProv": "TX"},
            "equipmentType": "r",  # Requires reefer
            "rateInfo": {
                "minimumRate": 3200,
                "maximumRate": 4200
            },
            "emailHistory": {
                "details": {
                    "commodity": "frozen foods",
                    "weight": "38000"
                },
                "negotitationStep": 0,
            }
        }

        emails = [
            {
                "id": "1",
                "subject": "Reefer Load Fresno to Dallas",
                "body": "Reefer load, 38k lbs frozen foods. Temperature controlled -10°F. Need pickup tomorrow.",
                "from": [{"email": "frozen@foods.com", "name": "Frozen Foods Inc"}]
            }
        ]

        self.show_input_data(company_details, truck, load, emails)

        self.print_section("PROCESSING FLOW")
        result = await process_reply(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            response_callback=self.response_callback
        )

        self.show_result(result)

        print(f"\n✨ EXPECTED OUTCOME: System should detect equipment mismatch - "
              f"load needs reefer but truck is dry van")

    async def run_demo_9_complex_multi_question(self):
        """Demo 9: Complex multi-question scenario"""
        self.print_header(
            "Complex Multi-Question Email",
            "Broker asks many detailed questions about capabilities"
        )

        company_details = {
            "name": "Elite Transport Solutions",
            "mcNumber": "987654",
            "phone": "(800) 555-FREIGHT",
            "address": "456 Logistics Blvd, Memphis, TN 38118",
            "details": "Full-service carrier specializing in time-sensitive deliveries. 24/7 dispatch, real-time tracking, $2M cargo insurance"
        }

        our_emails = ["dispatch@elitetransport.com"]

        truck = {
            "maxWeight": 80000,
            "maxLength": 53,
            "equipmentType": "v",
            "isPermitted": {
                "hazmat": True,
                "refrigerated": False,
                "oversize": True
            },
            "security": {
                "gpsTracking": True,
                "cargoInsurance": True,
                "securitySeal": True,
                "driverBackgroundCheck": True
            }
        }

        load = {
            "id": "DEMO-009",
            "postersReferenceId": "ETS-2024-1215-001",
            "status": "active",
            "origin": {"city": "Memphis", "stateProv": "TN"},
            "destination": {"city": "Phoenix", "stateProv": "AZ"},
            "rateInfo": {
                "minimumRate": 2800,
                "maximumRate": 3800
            },
            "emailHistory": {
                "details": {},
                "negotitationStep": 0,
            }
        }

        emails = [
            {
                "id": "1",
                "subject": "Detailed Carrier Qualification - Memphis to Phoenix",
                "body": """I have a high-value load that requires a qualified carrier. Please provide:

1. What's your MC number and company name?
2. Do you have GPS tracking on all vehicles?
3. What's your cargo insurance coverage amount?
4. Do you have hazmat certification?
5. Can you provide driver background check confirmation?
6. What's your load reference number for tracking?
7. Do you have security seals on your trailers?
8. What's your 24/7 dispatch contact number?
9. How many years has your company been in operation?
10. Do you have oversize permits if needed?

This is a time-sensitive pharmaceutical shipment requiring full compliance.""",
                "from": [{"email": "logistics@pharmaship.com", "name": "PharmaShip Logistics"}]
            }
        ]

        self.show_input_data(company_details, truck, load, emails)

        self.print_section("PROCESSING FLOW")
        result = await process_reply(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            response_callback=self.response_callback
        )

        self.show_result(result)

        print(f"\n✨ EXPECTED OUTCOME: System should answer all 10 questions comprehensively "
              f"using company and truck data")

    async def run_demo_10_rate_too_low_rejection(self):
        """Demo 10: Broker offers rate below our minimum"""
        self.print_header(
            "Rate Below Minimum",
            "Broker offers rate below our minimum acceptable rate"
        )

        company_details = {
            "name": "Load Model LLC",
            "mcNumber": "1242119",
            "rateNegotiation": {
                "firstBidThreshold": 80,
                "secondBidThreshold": 60,
                "rounding": 25
            }
        }

        our_emails = ["dispatch@loadmodellc.com"]

        truck = {"maxWeight": 80000, "maxLength": 53}

        load = {
            "id": "DEMO-010",
            "status": "active",
            "origin": {"city": "Miami", "stateProv": "FL"},
            "destination": {"city": "Seattle", "stateProv": "WA"},
            "equipmentType": "v",
            "rateInfo": {
                "minimumRate": 4500,  # High minimum for long haul
                "maximumRate": 6000
            },
            "emailHistory": {
                "details": {
                    "commodity": "electronics",
                    "weight": "35000"
                },
                "negotitationStep": 0,
            }
        }

        emails = [
            {
                "id": "1",
                "subject": "Cross Country Electronics Load",
                "body": "Van load, 35k lbs electronics from Miami to Seattle. I can offer $3800 for this load. Need pickup ASAP.",
                "from": [{"email": "cheaprates@budget.com", "name": "Budget Freight"}]
            }
        ]

        self.show_input_data(company_details, truck, load, emails)

        self.print_section("PROCESSING FLOW")
        result = await process_reply(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            )

        self.show_result(result)

        print(f"\n✨ EXPECTED OUTCOME: System should detect broker's $3800 offer is below "
              f"our minimum $4500 and counter with higher rate (~$5700)")

    async def run_demo_11_missing_critical_info(self):
        """Demo 11: Missing critical information we cannot provide"""
        self.print_header(
            "Missing Critical Information",
            "Broker asks questions we cannot answer from available data"
        )

        company_details = {
            "name": "Load Model LLC",
            "mcNumber": "1242119",
            # Intentionally missing phone and other details
        }

        our_emails = ["dispatch@loadmodellc.com"]

        truck = {
            "maxWeight": 80000,
            "maxLength": 53,
            # Missing permit info
        }

        load = {
            "id": "DEMO-011",
            "status": "active",
            "origin": {"city": "Chicago", "stateProv": "IL"},
            "destination": {"city": "Atlanta", "stateProv": "GA"},
            "rateInfo": {
                "minimumRate": 2000,
                "maximumRate": 2800
            },
            "emailHistory": {
                "details": {},
                "negotitationStep": 0,
            }
        }

        emails = [
            {
                "id": "1",
                "subject": "Chicago to Atlanta - Need Full Details",
                "body": """Before I can provide load details, I need:

1. Your company's DOT number (not MC number)
2. Your insurance certificate number
3. Driver's CDL number and expiration date
4. Last 3 safety inspection reports
5. Your bonding company information
6. TWIC card verification for driver

Please provide all information before we can proceed.""",
                "from": [{"email": "security@strictfreight.com", "name": "Strict Freight Security"}]
            }
        ]

        self.show_input_data(company_details, truck, load, emails)

        self.print_section("PROCESSING FLOW")
        result = await process_reply(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            response_callback=self.response_callback
        )

        self.show_result(result)

        print(f"\n✨ EXPECTED OUTCOME: System should identify critical questions it cannot answer "
              f"and flag for human review")

    async def run_demo_12_temperature_controlled_load(self):
        """Demo 12: Temperature-controlled load with specific requirements"""
        self.print_header(
            "Temperature-Controlled Load",
            "Reefer load with specific temperature requirements"
        )

        company_details = {
            "name": "Cold Chain Express",
            "mcNumber": "555123",
            "phone": "(888) 555-COLD",
            "details": "Specialized in temperature-controlled transportation with HACCP certification"
        }

        our_emails = ["dispatch@coldchain.com"]

        truck = {
            "maxWeight": 80000,
            "maxLength": 53,
            "equipmentType": "r",  # Reefer truck
            "isPermitted": {
                "refrigerated": True,
                "hazmat": False
            },
            "security": {
                "gpsTracking": True,
                "cargoInsurance": True
            }
        }

        load = {
            "id": "DEMO-012",
            "status": "active",
            "origin": {"city": "Salinas", "stateProv": "CA"},
            "destination": {"city": "Boston", "stateProv": "MA"},
            "equipmentType": "r",
            "rateInfo": {
                "minimumRate": 4500,
                "maximumRate": 5500
            },
            "emailHistory": {
                "details": {},
                "negotitationStep": 0,
            }
        }

        emails = [
            {
                "id": "1",
                "subject": "Urgent Reefer Load - Salinas to Boston",
                "body": """Reefer load, 44,000 lbs fresh produce (lettuce, spinach).

Temperature requirements:
- Maintain 34-36°F throughout transit
- Continuous monitoring required
- Must have temperature recording capability
- HACCP certified carrier preferred

Pickup: Tomorrow 6AM
Delivery: 72 hours max transit time

Can you handle this? What's your rate?""",
                "from": [{"email": "produce@freshveg.com", "name": "Fresh Vegetables Inc"}]
            }
        ]

        self.show_input_data(company_details, truck, load, emails)

        self.print_section("PROCESSING FLOW")
        result = await process_reply(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            response_callback=self.response_callback
        )

        self.show_result(result)

        print(f"\n✨ EXPECTED OUTCOME: System should extract reefer requirements, "
              f"confirm equipment compatibility, and ask for specific delivery time")

    async def run_demo_13_high_value_security_load(self):
        """Demo 13: High-value load requiring security measures"""
        self.print_header(
            "High-Value Security Load",
            "Electronics load requiring enhanced security protocols"
        )

        company_details = {
            "name": "SecureHaul Logistics",
            "mcNumber": "888999",
            "phone": "(555) SECURE-1",
            "details": "High-value cargo specialist with $5M insurance and security protocols"
        }

        our_emails = ["dispatch@securehaul.com"]

        truck = {
            "maxWeight": 80000,
            "maxLength": 53,
            "equipmentType": "v",
            "security": {
                "gpsTracking": True,
                "cargoInsurance": True,
                "securitySeal": True,
                "driverBackgroundCheck": True
            }
        }

        load = {
            "id": "DEMO-013",
            "status": "active",
            "origin": {"city": "San Jose", "stateProv": "CA"},
            "destination": {"city": "Austin", "stateProv": "TX"},
            "rateInfo": {
                "minimumRate": 3500,
                "maximumRate": 4500
            },
            "emailHistory": {
                "details": {},
                "negotitationStep": 0,
            }
        }

        emails = [
            {
                "id": "1",
                "subject": "HIGH VALUE ELECTRONICS - Enhanced Security Required",
                "body": """CONFIDENTIAL: High-value electronics shipment

Cargo: 25,000 lbs computer servers ($2.5M value)
Requirements:
- GPS tracking mandatory
- Security seals required
- Background-checked drivers only
- Minimum $5M cargo insurance
- No stops except fuel (company fuel cards provided)
- Real-time location updates every 30 minutes
- Delivery appointment required

Do you meet all security requirements? Rate $4200 if qualified.""",
                "from": [{"email": "security@techcorp.com", "name": "TechCorp Security"}]
            }
        ]

        self.show_input_data(company_details, truck, load, emails)

        self.print_section("PROCESSING FLOW")
        result = await process_reply(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            response_callback=self.response_callback
        )

        self.show_result(result)

        print(f"\n✨ EXPECTED OUTCOME: System should confirm security capabilities "
              f"and evaluate the $4200 rate offer")

    async def run_demo_14_last_minute_changes(self):
        """Demo 14: Broker makes last-minute changes to load details"""
        self.print_header(
            "Last-Minute Load Changes",
            "Broker changes pickup location and adds extra stops"
        )

        company_details = {
            "name": "Load Model LLC",
            "mcNumber": "1242119",
            "rateNegotiation": {
                "firstBidThreshold": 70,
                "secondBidThreshold": 50,
                "rounding": 25
            }
        }

        our_emails = ["dispatch@loadmodellc.com"]

        truck = {"maxWeight": 80000, "maxLength": 53}

        load = {
            "id": "DEMO-014",
            "status": "active",
            "origin": {"city": "Denver", "stateProv": "CO"},
            "destination": {"city": "Kansas City", "stateProv": "MO"},
            "rateInfo": {
                "minimumRate": 1800,
                "maximumRate": 2400
            },
            "emailHistory": {
                "details": {
                    "commodity": "furniture",
                    "weight": "40000"
                },
                "negotitationStep": 1,
            }
        }

        emails = [
            {
                "id": "1",
                "subject": "Denver to Kansas City Furniture",
                "body": "Can you do $2100 for Denver to Kansas City furniture load?",
                "from": [{"email": "dispatch@loadmodellc.com", "name": "Load Model"}]
            },
            {
                "id": "2",
                "subject": "Re: Denver to Kansas City Furniture - CHANGES",
                "body": """Sorry, need to make some changes to this load:

1. Pickup location changed to Colorado Springs (not Denver)
2. Need to add a stop in Topeka, KS before final delivery
3. Weight is actually 45,000 lbs (not 40k)
4. Need pickup tomorrow morning instead of Monday

Can you still do $2100 with these changes? Let me know ASAP.""",
                "from": [{"email": "changes@furniture.com", "name": "Furniture Broker"}]
            }
        ]

        self.show_input_data(company_details, truck, load, emails)

        self.print_section("PROCESSING FLOW")
        result = await process_reply(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            response_callback=self.response_callback
        )

        self.show_result(result)

        print(f"\n✨ EXPECTED OUTCOME: System should detect route changes and weight increase, "
              f"negotiate higher rate due to added complexity")

    async def run_demo_15_multi_stop_delivery(self):
        """Demo 15: Load with multiple delivery stops"""
        self.print_header(
            "Multi-Stop Delivery Load",
            "Single pickup with deliveries to multiple locations"
        )

        company_details = {
            "name": "Load Model LLC",
            "mcNumber": "1242119",
            "rateNegotiation": {
                "firstBidThreshold": 75,
                "secondBidThreshold": 55,
                "rounding": 50
            }
        }

        our_emails = ["dispatch@loadmodellc.com"]

        truck = {"maxWeight": 80000, "maxLength": 53}

        load = {
            "id": "DEMO-015",
            "status": "active",
            "origin": {"city": "Atlanta", "stateProv": "GA"},
            "destination": {"city": "Orlando", "stateProv": "FL"},  # Primary destination
            "rateInfo": {
                "minimumRate": 2200,
                "maximumRate": 3200
            },
            "emailHistory": {
                "details": {},
                "negotitationStep": 0,
            }
        }

        emails = [
            {
                "id": "1",
                "subject": "Multi-Stop Florida Delivery",
                "body": """Van load from Atlanta distribution center:

Pickup: Atlanta, GA - 48,000 lbs retail goods
Stops:
1. Jacksonville, FL - drop 12,000 lbs
2. Tampa, FL - drop 18,000 lbs
3. Orlando, FL - drop remaining 18,000 lbs

Total miles: ~850
All stops have dock access, no appointments needed
Each stop estimated 2-3 hours

Rate $2800 for complete multi-stop delivery. Interested?""",
                "from": [{"email": "multistop@retail.com", "name": "Retail Distribution"}]
            }
        ]

        self.show_input_data(company_details, truck, load, emails)

        self.print_section("PROCESSING FLOW")
        result = await process_reply(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            response_callback=self.response_callback
        )

        self.show_result(result)

        print(f"\n✨ EXPECTED OUTCOME: System should extract multi-stop information "
              f"and evaluate $2800 rate against our range ($2200-$3200)")

    async def run_all_demos(self):
        """Run all demo scenarios"""
        print(f"🚀 STARTING COMPREHENSIVE FREIGHT PROCESSOR DEMO")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Total Scenarios: 15 comprehensive demos")

        # Check environment
        if not os.getenv("AZURE_OPENAI_API_KEY"):
            print("❌ Missing AZURE_OPENAI_API_KEY environment variable")
            print("Please set your Azure OpenAI credentials to run the demo.")
            return

        demos = [
            # Original demos
            ("Basic Info Request", self.run_demo_1_info_request),
            ("Rate Negotiation", self.run_demo_2_rate_negotiation),
            ("Questions & Answers", self.run_demo_3_questions_and_answers),
            ("Load Cancellation", self.run_demo_4_cancellation),

            # Enhanced demos
            ("Requirements Violation", self.run_demo_5_requirements_violation),
            ("Weight Overload", self.run_demo_6_weight_overload),
            ("Successful Negotiation", self.run_demo_7_successful_negotiation),
            ("Equipment Mismatch", self.run_demo_8_equipment_mismatch),
            ("Complex Multi-Question", self.run_demo_9_complex_multi_question),
            ("Rate Too Low", self.run_demo_10_rate_too_low_rejection),
            ("Missing Critical Info", self.run_demo_11_missing_critical_info),
            ("Temperature Controlled", self.run_demo_12_temperature_controlled_load),
            ("High-Value Security", self.run_demo_13_high_value_security_load),
            ("Last-Minute Changes", self.run_demo_14_last_minute_changes),
            ("Multi-Stop Delivery", self.run_demo_15_multi_stop_delivery)
        ]

        for i, (demo_name, demo_func) in enumerate(demos, 1):
            try:
                print(f"\n{'='*20} DEMO {i}/15: {demo_name.upper()} {'='*20}")
                await demo_func()

                if i < len(demos):
                    print(f"\n⏸️  Press Enter to continue to next demo...")
                    input()

            except Exception as e:
                print(f"❌ Demo {i} ({demo_name}) failed: {type(e).__name__}: {e}")
                print(f"🔄 Continuing with next demo...")

                # Print stack trace for debugging
                import traceback
                print("🐛 Stack trace:")
                traceback.print_exc()

        print(f"\n🎉 ALL 15 DEMOS COMPLETED!")
        print(f"✅ You've seen the complete Pydantic AI Freight Processor in action!")
        print(f"\n📊 Demo Coverage Summary:")
        print(f"   • ✅ Basic email processing and info extraction")
        print(f"   • ✅ Rate negotiation strategies")
        print(f"   • ✅ Question answering capabilities")
        print(f"   • ✅ Load cancellation detection")
        print(f"   • ✅ Requirements and compatibility checking")
        print(f"   • ✅ Equipment type validation")
        print(f"   • ✅ Weight and capacity constraints")
        print(f"   • ✅ Security and permit requirements")
        print(f"   • ✅ Complex multi-question scenarios")
        print(f"   • ✅ Temperature-controlled loads")
        print(f"   • ✅ High-value cargo protocols")
        print(f"   • ✅ Load modifications and changes")
        print(f"   • ✅ Multi-stop delivery coordination")
        print(f"   • ✅ Critical information handling")
        print(f"   • ✅ Successful negotiation completion")

    async def run_quick_demo(self):
        """Run a quick subset of most interesting demos"""
        print(f"⚡ QUICK DEMO - 5 Most Interesting Scenarios")

        quick_demos = [
            ("Basic Negotiation", self.run_demo_2_rate_negotiation),
            ("Complex Questions", self.run_demo_9_complex_multi_question),
            ("Requirements Violation", self.run_demo_5_requirements_violation),
            ("Successful Deal", self.run_demo_7_successful_negotiation),
            ("High-Value Security", self.run_demo_13_high_value_security_load)
        ]

        for i, (demo_name, demo_func) in enumerate(quick_demos, 1):
            try:
                print(f"\n{'='*15} QUICK DEMO {i}/5: {demo_name.upper()} {'='*15}")
                await demo_func()

                if i < len(quick_demos):
                    print(f"\n⏸️  Press Enter for next quick demo...")
                    input()

            except Exception as e:
                print(f"❌ Quick demo {i} failed: {e}")

        print(f"\n⚡ QUICK DEMO COMPLETED!")

    async def run_custom_demo(self):
        """Allow user to create a custom demo scenario"""
        self.print_header(
            "Custom Demo Builder",
            "Create your own freight processing scenario"
        )

        print("🛠️  Let's build a custom demo scenario!")

        # Get user input for custom scenario
        print("\n1. Company Setup:")
        company_name = input("   Company name (default: Custom Freight LLC): ") or "Custom Freight LLC"
        mc_number = input("   MC number (default: 123456): ") or "123456"

        print("\n2. Load Setup:")
        origin_city = input("   Origin city (default: Chicago): ") or "Chicago"
        origin_state = input("   Origin state (default: IL): ") or "IL"
        dest_city = input("   Destination city (default: Atlanta): ") or "Atlanta"
        dest_state = input("   Destination state (default: GA): ") or "GA"

        min_rate = float(input("   Minimum rate (default: 2000): ") or "2000")
        max_rate = float(input("   Maximum rate (default: 3000): ") or "3000")

        print("\n3. Email Scenario:")
        print("   Choose email type:")
        print("   1. Info request")
        print("   2. Rate negotiation")
        print("   3. Questions from broker")
        print("   4. Load cancellation")
        email_type = input("   Select (1-4, default: 2): ") or "2"

        # Build custom scenario
        company_details = {
            "name": company_name,
            "mcNumber": mc_number,
            "phone": "(555) 123-DEMO",
            "rateNegotiation": {
                "firstBidThreshold": 75,
                "secondBidThreshold": 50,
                "rounding": 25
            }
        }

        our_emails = ["dispatch@customfreight.com"]

        truck = {"maxWeight": 80000, "maxLength": 53, "restrictions": []}

        load = {
            "id": "CUSTOM-001",
            "status": "active",
            "origin": {"city": origin_city, "stateProv": origin_state},
            "destination": {"city": dest_city, "stateProv": dest_state},
            "rateInfo": {
                "minimumRate": min_rate,
                "maximumRate": max_rate
            },
            "emailHistory": {
                "details": {},
                "negotitationStep": 0,
            }
        }

        # Create email based on type
        email_bodies = {
            "1": f"Hi, interested in your {origin_city} to {dest_city} load. Can you provide details?",
            "2": f"Van load {origin_city} to {dest_city}, 40k lbs. Can you do ${min_rate + 200}?",
            "3": f"Before proceeding, what's your MC number, phone, and do you have GPS tracking?",
            "4": f"Sorry, the {origin_city} to {dest_city} load is no longer available. Already covered."
        }

        emails = [
            {
                "id": "1",
                "subject": f"Custom Demo - {origin_city} to {dest_city}",
                "body": email_bodies.get(email_type, email_bodies["2"]),
                "from": [{"email": "broker@customdemo.com", "name": "Demo Broker"}]
            }
        ]

        self.show_input_data(company_details, truck, load, emails)

        self.print_section("PROCESSING CUSTOM SCENARIO")
        result = await process_reply(
            company_details=company_details,
            our_emails=our_emails,
            truck=truck,
            load=load,
            emails=emails,
            response_callback=self.response_callback
        )

        self.show_result(result)

        print(f"\n🎯 Your custom scenario completed successfully!")


async def main():
    """Main demo runner with menu options"""
    demo = EnhancedFreightProcessorDemo()

    print("🎬 Welcome to the Enhanced Pydantic AI Freight Processor Demo!")
    print("This comprehensive demo showcases 15+ realistic freight negotiation scenarios.")

    while True:
        print(f"\n{'='*60}")
        print("📋 DEMO MENU - Choose your experience:")
        print("1. 🚀 Full Demo Suite (15 scenarios) - Complete experience")
        print("2. ⚡ Quick Demo (5 scenarios) - Highlights only")
        print("3. 🛠️  Custom Demo - Build your own scenario")
        print("4. 📖 Scenario List - See all available demos")
        print("5. 🔧 Test Azure Connection")
        print("6. ❌ Exit")
        print("='*60}")

        choice = input("Select option (1-6): ").strip()

        if choice == "1":
            print("\n🚀 Starting Full Demo Suite...")
            await demo.run_all_demos()

        elif choice == "2":
            print("\n⚡ Starting Quick Demo...")
            await demo.run_quick_demo()

        elif choice == "3":
            print("\n🛠️  Starting Custom Demo Builder...")
            await demo.run_custom_demo()

        elif choice == "4":
            print("\n📖 Available Demo Scenarios:")
            scenarios = [
                "1. Basic Info Request - Extract load details",
                "2. Rate Negotiation - Counter-offer strategies",
                "3. Questions & Answers - Handle broker inquiries",
                "4. Load Cancellation - Detect cancelled loads",
                "5. Requirements Violation - Hazmat/permit issues",
                "6. Weight Overload - Capacity constraint detection",
                "7. Successful Negotiation - Rate acceptance",
                "8. Equipment Mismatch - Reefer vs van conflicts",
                "9. Complex Multi-Question - Handle detailed inquiries",
                "10. Rate Too Low - Reject below-minimum offers",
                "11. Missing Critical Info - Flag unanswerable questions",
                "12. Temperature Controlled - Reefer load requirements",
                "13. High-Value Security - Enhanced security protocols",
                "14. Last-Minute Changes - Handle load modifications",
                "15. Multi-Stop Delivery - Complex routing scenarios"
            ]
            for scenario in scenarios:
                print(f"   {scenario}")

        elif choice == "5":
            print("\n🔧 Testing Azure OpenAI Connection...")
            if os.getenv("AZURE_OPENAI_API_KEY"):
                print("✅ Environment variable found")
                print("🔗 Connection test would be performed here")
            else:
                print("❌ AZURE_OPENAI_API_KEY not found")
                print("💡 Set environment variable to test connection")

        elif choice == "6":
            print("\n👋 Thanks for exploring the Pydantic AI Freight Processor!")
            break

        else:
            print("❌ Invalid option. Please select 1-6.")


if __name__ == "__main__":
    asyncio.run(main())
