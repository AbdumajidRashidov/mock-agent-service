"""Modular freight processing agent - Each step as separate function"""

from typing import Dict, Any, List, Callable, Optional, Tuple
from datetime import datetime
import logging

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider

from ..models.load import LoadInfo
from ..models.company import CompanyDetails, TruckInfo
from ..models.negotiation import RateOfferer
from ..models.responses import ProcessingResult
from ..models.email import EmailThread

from ..tools import (
    classify_email_type, is_processable_email_type,
    extract_load_info, merge_extracted_info_with_load,
    extract_questions, generate_answers,
    check_cancellation,
    calculate_offering_rate,
    check_requirements,
    extract_rate_context,
    generate_email_response,
    parse_rate_from_text,
)

from ..utils.constants import NegotiationStep as ConstNegotiationStep
from ..utils.email_parser import parse_email_messages
from ..utils.validation import validate_load_processable
from ..utils.rate_calculator import evaluate_broker_offer
from ..config.prompts import FREIGHT_AGENT_SYSTEM_PROMPT
from ..config.settings import get_model_config

logger = logging.getLogger(__name__)


def get_azure_openai_model():
    """Get configured Azure OpenAI model"""
    config = get_model_config()
    return OpenAIModel(
        config['model'],
        provider=AzureProvider(
            azure_endpoint=config['endpoint'],
            api_version='2024-06-01',
            api_key=config['api_key'],
        ),
    )


# Main freight processing agent
freight_agent = Agent(
    get_azure_openai_model(),
    system_prompt=FREIGHT_AGENT_SYSTEM_PROMPT,
    result_type=ProcessingResult,
)


# ================================
# STEP 0: INITIALIZATION FUNCTIONS
# ================================

def ensure_rate_range(load_data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure load has rate range for negotiation with smart defaults"""

    if not load_data.get("rateInfo"):
        load_data["rateInfo"] = {}

    rate_info = load_data["rateInfo"]

    if not rate_info.get("minimumRate") or not rate_info.get("maximumRate"):
        # Default ranges by route type
        default_ranges = {
            "short": {"min": 800, "max": 1500},    # < 500 miles
            "medium": {"min": 1500, "max": 3000},  # 500-1000 miles
            "long": {"min": 2500, "max": 4500},    # 1000+ miles
        }

        route_type = "medium"  # Default
        rate_info["minimumRate"] = default_ranges[route_type]["min"]
        rate_info["maximumRate"] = default_ranges[route_type]["max"]

        logger.info(f"🔧 Added default rate range: ${rate_info['minimumRate']} - ${rate_info['maximumRate']}")

    return load_data


def clean_field_updates(field_updates: Dict[str, Any]) -> Dict[str, Any]:
    """Clean field updates to remove enum objects and ensure serializable values"""
    cleaned = {}

    for field_path, value in field_updates.items():
        if hasattr(value, 'value'):  # Handle enum objects
            cleaned[field_path] = value.value
        elif isinstance(value, list):
            cleaned_list = []
            for item in value:
                if hasattr(item, 'value'):
                    cleaned_list.append(item.value)
                elif isinstance(item, dict) and 'owner' in item:
                    cleaned_item = item.copy()
                    if hasattr(item['owner'], 'value'):
                        cleaned_item['owner'] = item['owner'].value
                    cleaned_list.append(cleaned_item)
                else:
                    cleaned_list.append(item)
            cleaned[field_path] = cleaned_list
        else:
            cleaned[field_path] = value

    return cleaned


async def initialize_processing(
    company_details: Dict[str, Any],
    our_emails: List[str],
    truck: Dict[str, Any],
    load: Dict[str, Any],
    emails: List[Dict[str, Any]],
    response_callback: Callable
) -> Tuple[CompanyDetails, TruckInfo, LoadInfo, EmailThread, ProcessingResult]:
    """Initialize and validate all inputs for processing"""

    # Ensure rate range exists
    load = ensure_rate_range(load)

    # Parse inputs
    company = CompanyDetails(**company_details)
    truck_info = TruckInfo(**truck)
    load_info = LoadInfo(**load)
    email_thread = parse_email_messages(emails, our_emails)

    await response_callback({
        "message": "🚀 Pydantic AI freight agent initialized",
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "agent_version": "freight_agent_v3.0_modular",
            "email_count": len(email_thread.messages),
            "load_id": load_info.id,
            "rate_range": f"${load.get('rateInfo', {}).get('minimumRate', 0)}-${load.get('rateInfo', {}).get('maximumRate', 0)}"
        }
    })

    # Initialize result
    result = ProcessingResult(
        message="Processing started",
        metadata={"timestamp": datetime.now().isoformat()}
    )

    return company, truck_info, load_info, email_thread, result


def validate_processability(load_info: LoadInfo, email_thread: EmailThread) -> Tuple[bool, str]:
    """Validate if load and emails can be processed"""

    if not validate_load_processable(load_info):
        return False, "Load is not processable"

    latest_email = email_thread.get_latest_broker_message()
    if not latest_email:
        return False, "No broker email found in thread"

    return True, ""


# ================================
# STEP 1: EMAIL CLASSIFICATION
# ================================

async def step_classify_email(
    latest_email,
    result: ProcessingResult,
    response_callback: Callable
) -> Tuple[bool, str]:
    """Step 1: Classify the email type"""

    await response_callback({
        "message": "📧 Step 1: Classifying email type...",
        "metadata": {"timestamp": datetime.now().isoformat()}
    })

    try:
        classification_response = await classify_email_type(latest_email)
        result.add_plugin_response(classification_response)

        if not classification_response.success:
            error_msg = f"Failed to classify email type: {classification_response.error_message}"
            await response_callback({
                "message": f"❌ {error_msg}",
                "metadata": {"timestamp": datetime.now().isoformat()}
            })
            return False, error_msg

        email_type = latest_email.email_type

        await response_callback({
            "message": f"📊 Email classified as: {email_type}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        })

        if not is_processable_email_type(email_type):
            error_msg = f"Email type '{email_type}' not processable"
            await response_callback({
                "message": f"⚠️ {error_msg}",
                "metadata": {"timestamp": datetime.now().isoformat()}
            })
            return False, error_msg

        return True, f"Email classified as {email_type}"

    except Exception as e:
        logger.error(f"Email classification failed: {e}")
        error_msg = f"Email classification failed: {str(e)}"
        await response_callback({
            "message": f"❌ {error_msg}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        })
        return False, error_msg


# ================================
# STEP 2: CANCELLATION DETECTION
# ================================

async def step_check_cancellation(
    latest_email,
    result: ProcessingResult,
    response_callback: Callable
) -> Tuple[bool, bool]:  # (continue_processing, is_cancelled)
    """Step 2: Check for load cancellation"""

    await response_callback({
        "message": "🔍 Step 2: Checking for load cancellation...",
        "metadata": {"timestamp": datetime.now().isoformat()}
    })

    cancellation_response = await check_cancellation(latest_email)
    result.add_plugin_response(cancellation_response)

    if cancellation_response.success and cancellation_response.extracted_data:
        await response_callback({
            "message": "❌ Load cancellation detected!",
            "metadata": {"timestamp": datetime.now().isoformat()}
        })
        result.mark_load_cancelled("Broker cancelled the load")
        return False, True  # Stop processing, is cancelled

    await response_callback({
        "message": "✅ No cancellation detected",
        "metadata": {"timestamp": datetime.now().isoformat()}
    })
    return True, False  # Continue processing, not cancelled


# ================================
# STEP 3: INFORMATION EXTRACTION
# ================================

async def step_extract_information(
    latest_email,
    load: Dict[str, Any],
    result: ProcessingResult,
    response_callback: Callable
) -> Tuple[bool, bool, Optional[float]]:
    """Step 3: Extract load information with enhanced rate detection"""

    await response_callback({
        "message": "📦 Step 3: Extracting load information...",
        "metadata": {"timestamp": datetime.now().isoformat()}
    })

    info_response = await extract_load_info(latest_email)
    result.add_plugin_response(info_response)

    broker_made_offer = False
    broker_rate = None

    if info_response.success and info_response.extracted_data:
        field_updates = merge_extracted_info_with_load(
            info_response.extracted_data,
            load.copy()
        )

        for field_path, value in field_updates.items():
            result.add_field_update(field_path, value)

        await response_callback({
            "message": f"📝 Extracted: {list(info_response.extracted_data.keys())}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        })

        # Check for broker rate offer from AI
        if "offeringRate" in info_response.extracted_data:
            broker_rate = info_response.extracted_data["offeringRate"]

        # CRITICAL: Fallback rate detection using enhanced parser
        if not broker_rate:
            email_text = latest_email.get_plain_content()
            broker_rate = parse_rate_from_text(email_text)  # Use enhanced version!

            if broker_rate:
                await response_callback({
                    "message": f"🔍 Enhanced fallback detected rate: ${broker_rate}",
                    "metadata": {"timestamp": datetime.now().isoformat()}
                })

                # Add to field updates
                result.add_field_update("rateInfo.rateUsd", broker_rate)
                result.add_field_update("rateInfo.isAIIdentified", True)

        if broker_rate:
            result.detected_broker_rate = broker_rate
            broker_made_offer = True

            await response_callback({
                "message": f"💰 Detected broker rate: ${broker_rate}",
                "metadata": {"timestamp": datetime.now().isoformat()}
            })

            # Add broker rate to history
            now = datetime.now()
            broker_rate_entry = {
                "rate": broker_rate,
                "date": now.strftime("%m/%d/%Y %H:%M"),
                "owner": RateOfferer.BROKER.value
            }
            result.add_field_update("emailHistory.offeredRates", broker_rate_entry, "push")

    return True, broker_made_offer, broker_rate

# ================================
# STEP 4: RATE NEGOTIATION
# ================================

async def step_handle_rate_negotiation(
    broker_rate: float,
    load: Dict[str, Any],
    company: CompanyDetails,
    load_info: LoadInfo,
    result: ProcessingResult,
    response_callback: Callable
) -> Optional[float]:
    """Step 4: Handle rate negotiation with enhanced decision logic"""

    await response_callback({
        "message": "💼 Step 4: Processing rate negotiation...",
        "metadata": {"timestamp": datetime.now().isoformat()}
    })

    rate_info = load.get("rateInfo", {})
    min_rate = rate_info.get("minimumRate", 0)
    max_rate = rate_info.get("maximumRate", 0)

    if not (min_rate and max_rate and company.has_negotiation_settings()):
        await response_callback({
            "message": f"⚠️ Cannot negotiate - missing rate range or settings",
            "metadata": {"timestamp": datetime.now().isoformat()}
        })
        return None

    # Get latest email for context
    email_text = latest_email.get_plain_content() if 'latest_email' in locals() else ""
    rate_context = extract_rate_context(email_text)

    # Calculate our target rate
    current_step = load_info.email_history.negotiation_step or ConstNegotiationStep.FIRST_BID.value
    our_target = calculate_offering_rate(load.copy(), company, current_step)

    if not our_target:
        await response_callback({
            "message": "⚠️ Could not calculate target rate",
            "metadata": {"timestamp": datetime.now().isoformat()}
        })
        return None

    # Use enhanced evaluation logic
    decision = evaluate_broker_offer(
        broker_rate, our_target, min_rate, max_rate, current_step, rate_context
    )

    await response_callback({
        "message": f"🧮 Decision: {decision['action']} - {decision['reason']}",
        "metadata": {"timestamp": datetime.now().isoformat()}
    })

    now = datetime.now()

    if decision["action"] == "accept":
        # ACCEPT the broker's rate
        result.mark_load_booked(
            rate=broker_rate,
            reason=decision["reason"]
        )
        await response_callback({
            "message": f"✅ ACCEPTING: {decision['reason']}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        })
        return None  # No counter-offer needed

    elif decision["action"] == "counter" and decision.get("next_rate"):
        # COUNTER with calculated rate
        our_counter_rate = decision["next_rate"]
        result.calculated_offering_rate = our_counter_rate

        # Add our counter-offer to history
        our_rate_entry = {
            "rate": our_counter_rate,
            "date": now.strftime("%m/%d/%Y %H:%M"),
            "owner": RateOfferer.DISPATCHER.value
        }
        result.add_field_update("emailHistory.offeredRates", our_rate_entry, "push")

        # Update negotiation step
        result.add_field_update("emailHistory.negotitationStep", decision["next_step"])

        await response_callback({
            "message": f"🔄 COUNTER: {decision['reason']}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        })
        return our_counter_rate

    else:
        # REJECT the rate
        await response_callback({
            "message": f"❌ REJECT: {decision['reason']}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        })
        result.message = f"Rejected broker rate: {decision['reason']}"
        return None


# ================================
# STEP 5: REQUIREMENTS CHECKING
# ================================

async def step_check_requirements(
    load: Dict[str, Any],
    field_updates: Dict[str, Any],
    truck_info: TruckInfo,
    result: ProcessingResult,
    response_callback: Callable
) -> bool:  # Returns True to continue, False to stop
    """Step 5: Check load requirements compatibility"""

    await response_callback({
        "message": "🔧 Step 5: Checking load requirements compatibility...",
        "metadata": {"timestamp": datetime.now().isoformat()}
    })

    # Create updated load info with extracted data
    updated_load_data = load.copy()
    for field_path, value in field_updates.items():
        if field_path.startswith("emailHistory.details."):
            detail_field = field_path.replace("emailHistory.details.", "")
            if "emailHistory" not in updated_load_data:
                updated_load_data["emailHistory"] = {"details": {}}
            if "details" not in updated_load_data["emailHistory"]:
                updated_load_data["emailHistory"]["details"] = {}
            updated_load_data["emailHistory"]["details"][detail_field] = value
        elif field_path == "equipmentType":
            updated_load_data["equipmentType"] = value

    updated_load_info = LoadInfo(**updated_load_data)

    requirements_response = await check_requirements(updated_load_info, truck_info)
    result.add_plugin_response(requirements_response)

    if requirements_response.success and requirements_response.extracted_data:
        violations = requirements_response.extracted_data

        if violations:
            await response_callback({
                "message": f"⚠️ Found {len(violations)} requirement violations",
                "metadata": {"timestamp": datetime.now().isoformat()}
            })

            for violation in violations:
                result.add_abused_requirement(violation)

            # Add warnings to load
            warning_list = [req.abused_requirement for req in result.abused_requirements]
            result.add_field_update("warnings", warning_list)

            result.message = f"Load rejected due to requirements violations: {', '.join(warning_list)}"
            return False  # Stop processing

    await response_callback({
        "message": "✅ Requirements check passed",
        "metadata": {"timestamp": datetime.now().isoformat()}
    })
    return True  # Continue processing


# ================================
# STEP 6: QUESTION HANDLING
# ================================

async def step_handle_questions(
    latest_email,
    company: CompanyDetails,
    load_info: LoadInfo,
    load: Dict[str, Any],
    result: ProcessingResult,
    response_callback: Callable
) -> bool:  # Returns True if questions were processed
    """Step 6: Extract and answer questions"""

    await response_callback({
        "message": "❓ Step 6: Processing questions...",
        "metadata": {"timestamp": datetime.now().isoformat()}
    })

    questions_response = await extract_questions(latest_email)
    result.add_plugin_response(questions_response)

    if not (questions_response.success and questions_response.extracted_data):
        await response_callback({
            "message": "ℹ️ No questions found to process",
            "metadata": {"timestamp": datetime.now().isoformat()}
        })
        return False

    questions = questions_response.extracted_data
    if not questions:
        return False

    await response_callback({
        "message": f"❓ Found {len(questions)} questions to answer",
        "metadata": {"timestamp": datetime.now().isoformat()}
    })

    load_id = load_info.id or load_info.posters_reference_id or load.get("id")

    answers_response = await generate_answers(questions, company, load_id)
    result.add_plugin_response(answers_response)

    if answers_response.success and answers_response.extracted_data:
        for qa in answers_response.extracted_data:
            result.add_question_answer(qa)

        # Check for critical questions
        if result.has_critical_questions:
            critical_questions = [qa.question for qa in result.questions_and_answers if qa.could_not_answer]
            result.message = "Critical questions could not be answered"
            await response_callback({
                "message": f"⚠️ Critical questions could not be answered: {len(critical_questions)}",
                "metadata": {"timestamp": datetime.now().isoformat()}
            })
            return True

    await response_callback({
        "message": f"✅ Answered {len([qa for qa in result.questions_and_answers if qa.is_answered()])} questions",
        "metadata": {"timestamp": datetime.now().isoformat()}
    })
    return True


# ================================
# STEP 7: MISSING INFO DETECTION
# ================================

def step_detect_missing_info(
    latest_email,
    result: ProcessingResult,
    broker_made_offer: bool,
    our_counter_rate: Optional[float]
) -> List[str]:
    """Step 7: Detect missing critical information"""

    missing_info = []

    # Only check for missing info if NOT in rate acceptance mode
    if not (broker_made_offer and not our_counter_rate):
        email_body = latest_email.get_plain_content().lower()

        # Check if broker asked for our rate but we don't have all load details
        if "your rate" in email_body or "what's your rate" in email_body:
            current_commodity = result.field_updates.get("emailHistory.details.commodity")
            current_weight = result.field_updates.get("emailHistory.details.weight")
            current_equipment = result.field_updates.get("equipmentType")

            if not current_commodity:
                missing_info.append("commodity type")
            if not current_weight:
                missing_info.append("weight")
            if not current_equipment:
                missing_info.append("equipment type")

    return missing_info


# ================================
# STEP 8: EMAIL GENERATION
# ================================

async def step_generate_email_response(
    email_thread: EmailThread,
    company: CompanyDetails,
    missing_info: List[str],
    our_counter_rate: Optional[float],
    result: ProcessingResult,
    response_callback: Callable
) -> bool:  # Returns True if email was generated
    """Step 8: Generate email response if needed"""

    if not (our_counter_rate or result.questions_and_answers or missing_info):
        return False

    await response_callback({
        "message": "✍️ Step 8: Generating email response...",
        "metadata": {"timestamp": datetime.now().isoformat()}
    })

    email_response = await generate_email_response(
        email_thread=email_thread,
        company_details=company,
        missing_info=missing_info,
        questions_and_answers=result.questions_and_answers,
        offering_rate=our_counter_rate
    )

    result.add_plugin_response(email_response)

    if email_response.success and email_response.extracted_data:
        result.email_to_send = email_response.extracted_data

        if our_counter_rate:
            result.message = f"Email response generated - counter-offering rate ${our_counter_rate}"
        elif missing_info:
            result.message = f"Email response generated - requesting missing info: {', '.join(missing_info)}"
        else:
            result.message = "Email response generated - answered questions"

        await response_callback({
            "message": f"✅ Email generated successfully",
            "metadata": {"timestamp": datetime.now().isoformat()}
        })
        return True
    else:
        result.message = "Failed to generate email response"
        await response_callback({
            "message": "❌ Failed to generate email response",
            "metadata": {"timestamp": datetime.now().isoformat()}
        })
        return False


# ================================
# MAIN ORCHESTRATOR
# ================================

async def process_freight_email(
    company_details: Dict[str, Any],
    our_emails: List[str],
    truck: Dict[str, Any],
    load: Dict[str, Any],
    emails: List[Dict[str, Any]],
    response_callback: Callable
) -> Dict[str, Any]:
    """
    Main orchestrator function that calls each step in sequence.
    Each step is a separate, testable function.
    """
    try:
        # STEP 0: Initialize
        company, truck_info, load_info, email_thread, result = await initialize_processing(
            company_details, our_emails, truck, load, emails, response_callback
        )

        # Validate processability
        can_process, error_msg = validate_processability(load_info, email_thread)
        if not can_process:
            result.message = error_msg
            return result.to_legacy_format()

        latest_email = email_thread.get_latest_broker_message()

        # STEP 1: Classify Email
        success, msg = await step_classify_email(latest_email, result, response_callback)
        if not success:
            result.message = msg
            return result.to_legacy_format()

        # STEP 2: Check Cancellation
        continue_processing, is_cancelled = await step_check_cancellation(latest_email, result, response_callback)
        if not continue_processing:
            return result.to_legacy_format()

        # STEP 3: Extract Information
        continue_processing, broker_made_offer, broker_rate = await step_extract_information(
            latest_email, load, result, response_callback
        )

        # STEP 4: Handle Rate Negotiation (if broker made offer)
        our_counter_rate = None
        if broker_made_offer and broker_rate:
            our_counter_rate = await step_handle_rate_negotiation(
                broker_rate, load, company, load_info, result, response_callback
            )

        # STEP 5: Check Requirements
        if result.field_updates:  # Only if we extracted info
            requirements_ok = await step_check_requirements(
                load, result.field_updates, truck_info, result, response_callback
            )
            if not requirements_ok:
                return result.to_legacy_format()

        # STEP 6: Handle Questions (only if not accepting a rate)
        if not (broker_made_offer and not our_counter_rate):
            questions_ok = await step_handle_questions(
                latest_email, company, load_info, load, result, response_callback
            )
            if questions_ok is False and result.has_critical_questions:
                return result.to_legacy_format()

        # STEP 7: Detect Missing Info
        missing_info = step_detect_missing_info(latest_email, result, broker_made_offer, our_counter_rate)

        # STEP 8: Generate Email Response
        email_generated = await step_generate_email_response(
            email_thread, company, missing_info, our_counter_rate, result, response_callback
        )

        # Final message if no email was generated
        if not email_generated:
            if result.is_load_booked:
                result.message = f"Load booked at ${result.detected_broker_rate} - no response needed"
            else:
                result.message = "No action needed - all information complete"

        # Clean and finalize
        result.field_updates = clean_field_updates(result.field_updates)

        await response_callback({
            "message": f"✅ Processing complete: {result.message}",
            "metadata": {"timestamp": datetime.now().isoformat()}
        })

        return result.to_legacy_format()

    except Exception as e:
        logger.exception("Error in freight email processing")

        await response_callback({
            "message": f"❌ Processing failed: {str(e)}",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "error_type": type(e).__name__
            }
        })

        return {
            "field_updates": {},
            "message": f"Processing failed: {str(e)}",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        }
