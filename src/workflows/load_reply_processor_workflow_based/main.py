from typing import Dict, Any, List
import html2md
from .utils.is_load_processable import is_load_processable
from .utils.extract_reply_content import extract_reply_content
from .utils.get_current_offering_rate_for_load import get_current_offering_rate
from .utils.get_missing_fields import get_missing_fields
from .plugins.reply_email_type_checker.const import PROCESSABLE_EMAIL_TYPES
from .plugins.reply_email_type_checker.index import reply_email_type_checker_plugin
from .plugins.cancellation_checker.index import cancellation_checker_plugin
from .plugins.negotiation_status_checker.index import negotiation_status_checker_plugin
from .plugins.info_extractor.index import info_extractor_plugin
from .plugins.requirements_checker.index import requirements_checker_plugin
from .plugins.question_extractor.index import questions_extractor_plugin
from .plugins.answer_generator.index import answer_generator_plugin
from .plugins.email_generator.index import email_generator_plugin
from datetime import datetime

class NegotiationStep:
    MAX_BID = 0
    FIRST_BID = 1
    SECOND_BID = 2
    MIN_BID = 3
    SUCCEEDED = 4

class RateOfferer:
    BROKER = "broker"
    DISPATCHER = "dispatcher"

async def process_reply(
    company_details: Dict[str, Any],
    our_emails: List[str],
    truck: Dict[str, Any],
    load: Dict[str, Any],
    emails: List[Dict[str, Any]],
    response_callback: callable
) -> None:
    """Process a reply email and determine next actions.

    Args:
        company_details (Dict[str, Any]): Company details
        our_emails (List[str]): List of our email addresses
        truck (Dict[str, Any]): Truck details
        load (Dict[str, Any]): Load details
        emails: List of email objects in the thread
        response_callback (Callable): Callback function to stream responses

    The response_callback will be called with a dict containing:
        - email_to_send (Optional[str]): Generated email content if any
        - field_updates (Optional[Dict[str, str]]): Dict of field paths and their new values
        - plugin_response (Optional[Dict]): Response from plugins including:
            - plugin_name: Name of the plugin
            - response: Full OpenAI response if applicable
            - extracted_data: Plugin-specific data
            - tokens_spent: Number of tokens used if applicable
    """
    # Dict to track changes
    field_updates: Dict[str, Any] = {}

    # Check if load is processable
    if not is_load_processable(load):
        return {
            "message": "Load is found as not processable",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "status": load.get('status'),
                "warnings": load.get('warnings', []),
                "negotiation_step": load.get('emailHistory', {}).get('negotitationStep')
            }
        }

    latest_email = emails[-1]
    latest_email_content = (
        f"Subject: {latest_email['subject']}\n\n"
        f"{html2md.convert(extract_reply_content(latest_email['body']))}"
    )

    # Check email type
    email_type = await reply_email_type_checker_plugin(latest_email_content, response_callback)
    if not email_type or email_type not in PROCESSABLE_EMAIL_TYPES:
        return {
            "field_updates": field_updates,
            "message": "Reply email detected as suspicious",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "email_type": email_type
            }
        }

    # Check for cancellation
    is_cancelled = await cancellation_checker_plugin(latest_email_content, response_callback)
    if is_cancelled:
        field_updates["status"] = "cancelled"
        return {
            "field_updates": field_updates,
            "message": "Reply found as indicating the load is gone",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "is_cancelled": is_cancelled
            }
        }

    # Update negotiation step if needed
    if (load.get("rateInfo", {}).get("minimumRate") and
        load.get("rateInfo", {}).get("maximumRate") and
        company_details.get("rateNegotiation", {}).get("firstBidThreshold") and
        company_details.get("rateNegotiation", {}).get("secondBidThreshold") and
        company_details.get("rateNegotiation", {}).get("rounding")):

        current_step = load.get("emailHistory", {}).get("negotitationStep")
        if not isinstance(current_step, int):
            new_step = NegotiationStep.FIRST_BID if load.get("isBidRequestSent") else NegotiationStep.MAX_BID
        else:
            new_step = current_step + 1
        field_updates["emailHistory.negotitationStep"] = new_step
        await response_callback({"field_updates": field_updates, "message": f"Updated negotiation step: {new_step}","metadata": {"timestamp": datetime.now().isoformat()}})

    # Check negotiation status
    current_step = load.get("emailHistory", {}).get("negotitationStep")
    if current_step in [
        NegotiationStep.MAX_BID,
        NegotiationStep.FIRST_BID,
        NegotiationStep.SECOND_BID,
        NegotiationStep.MIN_BID
    ]:
        await response_callback({
            "message": "Checking if broker approved our rate",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "current_negotiation_step": current_step
            }
        })

        is_approved = await negotiation_status_checker_plugin(emails, our_emails, response_callback)
        if is_approved:
            field_updates["emailHistory.negotitationStep"] = NegotiationStep.SUCCEEDED
            return {
                "field_updates": field_updates,
                "message": "Broker approved our rate request",
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "current_negotiation_step": current_step,
                    "is_approved": is_approved
                }
            }

        await response_callback({
            "message": "Broker didn't approve our rate request",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "current_negotiation_step": current_step,
                "is_approved": is_approved
            }
        })
    else:
        await response_callback({
            "message": "Cannot check broker rate approval - not in active negotiation step",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "current_negotiation_step": current_step
            }
        })

    # Extract information
    info = await info_extractor_plugin(latest_email_content, response_callback) or {}

    # Update load details
    if info:
        # Initialize required nested structures if they don't exist
        if "emailHistory" not in load:
            load["emailHistory"] = {}
        if "details" not in load["emailHistory"]:
            load["emailHistory"]["details"] = {}
        if "rateInfo" not in load:
            load["rateInfo"] = {}

        if "equipmentType" in info:
            field_updates["equipmentType"] = info["equipmentType"]
            load["equipmentType"] = info["equipmentType"]

        if "commodity" in info:
            # Keep dot notation for field_updates as it's used by MongoDB
            field_updates["emailHistory.details.commodity"] = info["commodity"]
            # Update nested dict for load
            load["emailHistory"]["details"]["commodity"] = info["commodity"]

        if "weight" in info:
            field_updates["emailHistory.details.weight"] = info["weight"]
            load["emailHistory"]["details"]["weight"] = info["weight"]

        if "offeringRate" in info:
            field_updates["rateInfo.rateUsd"] = info["offeringRate"]
            field_updates["rateInfo.isAIIdentified"] = True
            load["rateInfo"]["rateUsd"] = info["offeringRate"]
            load["rateInfo"]["isAIIdentified"] = True

        if "deliveryDate" in info:
            field_updates["emailHistory.details.deliveryDateTime"] = info["deliveryDate"]
            load["emailHistory"]["details"]["deliveryDateTime"] = info["deliveryDate"]

        await response_callback({
            "field_updates": field_updates,
            "message": "Updated load details",
            "metadata": {
                "timestamp": datetime.now().isoformat()
            }
        })

    # Handle offering rate
    if "offeringRate" in info:
        await response_callback({
            "message": f"Detected broker offering a new rate: ${info.get('offeringRate')}",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
            }
        })

        if not load.get("emailHistory", {}).get("offeredRates"):
            field_updates["emailHistory.offeredRates"] = []

        now = datetime.now()
        formattedDate = now.strftime("%m/%d/%Y %H:%M")
        new_rate = {
            "rate": info.get("offeringRate"),
            "date": formattedDate,
            "owner": RateOfferer.BROKER
        }
        field_updates["emailHistory.offeredRates"].append(new_rate)

        current_offering_rate = get_current_offering_rate(load, company_details)
        if current_offering_rate and current_offering_rate < info.get("offeringRate"):
            field_updates["emailHistory.negotitationStep"] = NegotiationStep.SUCCEEDED
            return {
                "field_updates": field_updates,
                "message": "Broker offered more than our next bid, load negotiation completed",
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "current_offering_rate": current_offering_rate,
                    "offering_rate": info.get("offeringRate")
                }
            }

        await response_callback({
            "message": "Broker offered less than our next bid",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "current_offering_rate": current_offering_rate,
                "offering_rate": info.get("offeringRate")
            }
        })

    # Check requirements if no missing info
    missing_info = get_missing_fields(load)
    if not missing_info:
        await response_callback({
            "message": "Detected no more missing info left, checking requirements...",
            "metadata": {
                "timestamp": datetime.now().isoformat()
            }
        })

        abused_requirements = await requirements_checker_plugin(load, truck, response_callback)
        if abused_requirements:
            field_updates["warnings"] = abused_requirements
            return {"field_updates": field_updates, "message": "Requirements checked, abuses detected", "metadata": {"timestamp": datetime.now().isoformat(), "abused_requirements": abused_requirements}}

        await response_callback({
            "message": "Requirements checked, no abuses detected",
            "metadata": {
                "timestamp": datetime.now().isoformat()
            }
        })

    # Extract and answer questions
    questions = await questions_extractor_plugin(latest_email_content, response_callback)
    questions_and_answers = []
    if questions:
        await response_callback({
            "message": "Detected questions, generating answers...",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "questions": questions
            }
        })

        questions_and_answers = await answer_generator_plugin(
            questions,
            company_details,
            load.get("postersReferenceId"),
            response_callback
        )

        await response_callback({
            "message": "Generated answers",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "questions_and_answers": questions_and_answers
            }
        })

        if any(qa.get("couldNotAnswer") for qa in questions_and_answers):
            field_updates["emailHistory.criticalQuestions"] = [
                qa["question"] for qa in questions_and_answers if qa.get("couldNotAnswer")
            ]
            return {"field_updates": field_updates, "message": "Could not answer some questions, process stopped", "metadata": {"timestamp": datetime.now().isoformat(), "critical_questions": field_updates["emailHistory.criticalQuestions"]}}

    # Calculate offering rate
    offering_rate = None
    if (load.get("rateInfo", {}).get("minimumRate") and
        load.get("rateInfo", {}).get("maximumRate") and
        company_details.get("rateNegotiation", {}).get("firstBidThreshold") and
        company_details.get("rateNegotiation", {}).get("secondBidThreshold") and
        company_details.get("rateNegotiation", {}).get("rounding")):

        offering_rate = get_current_offering_rate(load, company_details)
        if offering_rate:
            formattedDate = datetime.now().strftime("%m/%d/%Y %H:%M")
            new_rate = {
                "rate": offering_rate,
                "date": formattedDate,
                "owner": RateOfferer.DISPATCHER
            }
            if "emailHistory.offeredRates" not in field_updates:
                field_updates["emailHistory.offeredRates"] = []
            field_updates["emailHistory.offeredRates"].append(new_rate)
            await response_callback({
                "field_updates": field_updates,
                "message": f"Defined offering rate: ${offering_rate}",
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "offering_rate": offering_rate,
                }
            })
        else:
            await response_callback({
                "message": "Couldn't define offering rate, even it's negotiation email",
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "negotiation_step": load.get("emailHistory", {}).get("negotitationStep"),
                }
            })
    else:
        await response_callback({
            "message": "Couldn't calculate offering rate, seems like it's just info request email",
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "minimum_rate": load.get("rateInfo", {}).get("minimumRate"),
                "maximum_rate": load.get("rateInfo", {}).get("maximumRate"),
                "first_bid_threshold": company_details.get("rateNegotiation", {}).get("firstBidThreshold"),
                "second_bid_threshold": company_details.get("rateNegotiation", {}).get("secondBidThreshold"),
                "rounding": company_details.get("rateNegotiation", {}).get("rounding")
            }
        })



    # Generate reply email if needed
    if not offering_rate and not questions_and_answers and not missing_info:
        return {"field_updates": field_updates, "message": "Couldn't define offering rate, questions to answer or missing info, process stopped", "metadata": {"timestamp": datetime.now().isoformat(), "offering_rate": offering_rate, "questions_and_answers": questions_and_answers, "missing_info": missing_info}}

    await response_callback({
        "message": "Generating reply email...",
        "metadata": {"timestamp": datetime.now().isoformat(), "offering_rate": offering_rate, "questions_and_answers": questions_and_answers, "missing_info": missing_info}
    })

    email_generator_params = {
        "questions_and_answers": questions_and_answers,
        "emails": emails,
        "our_emails": our_emails,
        "missing_info": missing_info,
        "offering_rate": offering_rate
    }
    email_to_send = await email_generator_plugin(email_generator_params, response_callback)

    return {
        "email_to_send": email_to_send,
        "field_updates": field_updates,
        "message": "Generated reply email, process completed!",
        "metadata": {"timestamp": datetime.now().isoformat()}
    }
