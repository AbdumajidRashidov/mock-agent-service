from langchain_core.messages import SystemMessage, HumanMessage
from langchain.chat_models import init_chat_model
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
from ..nodes.missing_load_info_checker import get_load_missing_fields
from ..const import EmailHistoryStatus
from ..utils.convert_emails_to_messages import get_conversation_context

class ReplyExtractorAgentResponse(BaseModel):
    commodity: Optional[str] = ""
    weight: Optional[int] = None
    length: Optional[int] = None
    height: Optional[int] = None
    width: Optional[int] = None
    pickupDateTime: Optional[str] = ""
    deliveryDateTime: Optional[str] = ""
    offeringRate: Optional[int] = None
    otherDetails: Optional[str] = ""
    specialNotes: Optional[str] = ""
    detentionPolicy: Optional[str] = ""
    accessorialCharges: Optional[str] = ""
    loadingMethod: Optional[str] = ""
    appointmentRequirements: Optional[str] = ""
    referenceNumber: Optional[str] = ""
    isTeamDriver: Optional[bool] = None
    driverShouldLoad: Optional[bool] = None
    driverShouldUnload: Optional[bool] = None

REPLY_EXTRACTOR_PROMPT = """
You are a truck industry expert that analyzes replies received from brokers and understands all the industry jargon.

Extract the exact field names and formats:

1. Commodity: - REQUIRED when specified
   - Extract the type of goods being shipped (e.g., "furniture", "electronics", "freight")
   - If the commodity is "freight of all kinds" or "FAK", extract as "freight of all kinds"
   - If the commodity is "general" or not specified, leave empty
   - Include quantities and packaging with the commodity (e.g., "13CASES", "20 pallets")
   - For the specific case of "13CASES", extract exactly as shown (case-sensitive)
   - Do not extract just pallet/package counts as the commodity (e.g., don't extract just "20 pallets")
   - If not mentioned, leave empty (do not make assumptions)

2. Weight: Numeric value in pounds (e.g., 40000) - REQUIRED
   - Weight is typically mentioned with units (lbs, kg, kilos, pounds) or context about the load
   - Common weight indicators: "weight:", "wt", "#", "lb", "kg", "lbs", "kgs", "pounds", "kilos"
   - Typical weight ranges: 1000-48000 lbs for standard loads
   - Convert formats:
     * "40k" or "40K" → 40000
     * "1,050 kg" → 2314.85 → 2315 (convert kg to lbs and round)
     * "45,000#" → 45000
   - If weight is mentioned without units but is in a reasonable weight range (1000-100,000) and not clearly a rate, assume it's weight
   - If not mentioned, leave empty

3. Rate: Numeric value as integer (e.g., 800 for "$800" or "800.00") - REQUIRED
   - Rate is typically mentioned with currency indicators ($, USD) or in context of payment
   - Common rate indicators: "rate:", "$X", "USD", "pay", "offer", "price", "rate is", "paying"
   - Typical rate ranges: $100-$10,000 for standard loads
   - Extract and clean:
     * Remove all non-numeric characters and decimal point
     * Round to nearest whole number
     * Examples:
       - "$1,500.00" → 1500
       - "rate is 2k" → 2000
       - "paying 1.25/mile" → round(1.25*mile) (if per mile rate)
   - If a number could be either weight or rate, prefer rate if:
     * It's prefixed with $ or other currency symbol
     * It's in a sentence about payment or cost
     * It's followed by "per mile", "flat", "total", "all in"
   - If not mentioned, leave empty


4. Pickup Date/Time: - REQUIRED when specified
   - Look for pickup time indicators: "pickup", "available", "ready", "loads", "pick up", "loading"
   - For the specific case of "3-5pm fcfs for delivery", the pickup time is "3-5pm FCFS"
   - For time ranges with @ symbol like "@08:00 (0800-1000)", extract as "08:00-10:00"
   - For FCFS with time range like "fcfs (0800-2200)", extract as "FCFS (08:00-22:00)"
   - Combine date and time if they appear on separate lines (e.g., "Pickup Date: 6/18/2025" and "Pickup Time: FCFS 08:00 to 16:00" → "6/18/2025 FCFS 08:00 to 16:00")
   - For relative times (e.g., "today", "tomorrow", "Friday 9 am"): preserve as-is
   - For ambiguous cases, check the context carefully:
     * If the time is near "pickup", "loads", "pick up", or "loading", it's likely pickup time
     * If the time is near "delivery", "drop", "unload", or "deliver", it's likely delivery time
     * If both pickup and delivery times are mentioned, they usually appear in chronological order
   - Include all relevant time indicators:
     * FCFS (First Come, First Served)
     * Appt (appointment required)
     * Time windows (e.g., "8-4PM")
     * Specific times (e.g., "15:00")
   - For relative times (e.g., "tomorrow", "Friday 9 am"), keep them as-is without converting to dates
   - If only a time is given without a date, use just the time (e.g., "8-4PM")
   - Format examples:
     * "9 am To 4 pm" (warehouse hours) → "09:00-16:00"
      * "Friday 9 am" (relative time) → "Friday 09:00"
     * "6/18/2025 FCFS 08:00 to 16:00" (exact date with FCFS time) → "06/18/2025 FCFS 08:00-16:00"
     * "8-4PM" (time only) → "08:00-16:00"
     * "06/19 1500" (military time) → "06/19 15:00"
     * "3-5pm FCFS" (time with FCFS indicator) → "15:00-17:00 FCFS"
     * "@08:00 (0800-1000)" → "08:00-10:00"
     * "@fcfs (0800-2200)" → "FCFS (08:00-22:00)"
      * "04/07 9 AM – 1 PM" → "04/07 09:00-13:00" (preserve MM/DD format for dates)
   - Do not add dates that aren't in the original message
   - If no pickup time is mentioned, leave empty

5. Delivery Date/Time: - REQUIRED when explicitly specified
   - ONLY extract a delivery time if it is explicitly mentioned with clear indicators
   - Look for delivery time indicators: "delivery by", "delivery on", "delivery time", "drop by", "unload by", "must deliver by"
   - For the specific case of "3-5pm fcfs for delivery fcfs big window", the delivery time is "any time FCFS"
   - For time ranges with @ symbol like "@08:00 (0800-1000)", extract as "08:00-10:00"
   - For FCFS with time range like "@fcfs (0800-2200)", extract as "FCFS (08:00-22:00)"
   - For ambiguous cases, check the context carefully:
     * If the time is near "delivery", "drop", "unload", or "deliver", it's likely delivery time
     * If the time is near "pickup" or "loads", it's likely pickup time
     * If both pickup and delivery times are mentioned, they usually appear in chronological order
   - Include all relevant time indicators:
     * Appt (when explicitly mentioned for delivery)
     * Time windows (e.g., "delivery between 8-5PM")
     * Specific times (e.g., "must deliver by 23:59")
     * FCFS (only if explicitly mentioned for delivery)
   - For relative times (e.g., "delivery by Friday 9 am"), keep them as-is without converting to dates

   - Format examples:
     * "Delivery by 6/18/2025 Appt 23:59" → "06/18/2025 Appt 23:59"
     * "Drop off appt required 8-5PM" → deliveryDateTime: "Appt 08:00-17:00"
     * "pickup tomorrow by 11:00" → pickupDateTime: "tomorrow 11:00"
     * "Must deliver by Friday 5pm" → "deliveryDateTime": "Friday 17:00"
     * "Delivery window 1-3pm" → "deliveryDateTime": "13:00-15:00"
   - If only a time is given without clear delivery context, do NOT extract it as delivery time
      * "Delivery window 06/20-20 08:00" → "06/20-20 08:00"
      * "@08:00 (0800-1000)" → "08:00-10:00 (0800-1000)"
      * "@fcfs (0800-2200)" → "FCFS (08:00-22:00)"
      * "04/08" → "04/08" (preserve as MM/DD date, not HH:MM time)
   - DO NOT extract a delivery time if:
     * The time is only mentioned for pickup
     * The time is mentioned without clear delivery context
     * You're not 100 percent certain it's a delivery time
   - If no delivery time is explicitly mentioned, leave the field empty

6. Special Notes: - OPTIONAL
   - Only include requirements that would make the load undeliverable if not met
   - Include details like:
     * Tarp requirements (e.g., "needs 8ft tarps", "with tarps")
     * Special equipment (e.g., "liftgate required", "pallet jack needed")
     * Loading/unloading constraints (e.g., "no loading docks", "appointment required")
     * Multiple stops (e.g., "multi-stop load", "2 pickups")
     * Special instructions (e.g., "must call 2 hours before delivery")
     * Payment methods (e.g., "Paid with 3rd party apps")
     * Trailer requirements (e.g., "Food Grade trailer")
     * Accessorial charges (e.g., "Lumper fee")
     * Clearance requirements (e.g., "need door clearance")
   - For tarp requirements, use the exact phrasing (e.g., "needs 8ft tarps" not "8ft tarps required")
   - Separate multiple notes with semicolons (e.g., "with tarps; liftgate required")
   - If no special requirements are mentioned, leave empty

7. Team Driver: - OPTIONAL
    - Look for indicators: "team driver", "team drivers required", "team driver needed"
    - If no team driver is mentioned, leave empty

8. Driver Should Load: - OPTIONAL
    - Look for indicators: "driver should load", "driver should unload"
    - If no driver should load is mentioned, leave empty

9. Driver Should Unload: - OPTIONAL
    - Look for indicators: "driver should unload", "driver should load"
    - If no driver should unload is mentioned, leave empty

IMPORTANT RULES:
1. NEVER invent or assume values for required fields - leave them empty if not explicitly stated
2. Special notes are ONLY for requirements that would make the load undeliverable if not met
3. For specialNotes:
   - If the broker explicitly states there are no special requirements (e.g., "no", "none", "not needed", "n/a", "no special handling"), set specialNotes to "No special handling"
   - If the broker says "everything needed is below" or similar phrases it means there are no special requirements, set specialNotes to "No special handling"
   - If special requirements are mentioned, include them exactly as stated
   - If no information is given about special requirements, leave specialNotes empty
4. "Warehouse hours" or "business hours" should be extracted as pickup time when no other pickup time is specified
5. "Freight of all kinds" should be extracted as "freight"
6. DO NOT extract any fields when the message indicates no reply is needed or no information is available
7. Only extract dimensions (length/width/height) when they are explicitly mentioned for the load itself, not the truck/trailer
8. If the message is just a confirmation or acknowledgment with no extractable fields, return an empty object
9. For time extraction, pay close attention to context words near the time (e.g., "loads at 3-5pm" vs "delivery by 3-5pm")
10. When both pickup and delivery times are mentioned in the same sentence, assign them based on the closest context word
11. For the specific phrase "3-5pm fcfs for delivery fcfs big window", extract:
    - pickupDateTime: "3-5pm FCFS"
    - deliveryDateTime: "fcfs big window"
13. For special notes about tarps, use the exact phrasing (e.g., "needs 8ft tarps" not "8ft tarps required")
15. "1-1" means "one pick one drop" - do not extract as a reference number
16. For dates in format "MM/DD", always interpret as month/day, never as hours:minutes
   - Example: "04/08" is April 8th, not 04:08

Examples of Weight vs Rate Disambiguation:
- "Weight is 2k" → weight: 2000 (has weight context)
- "Rate is 2k" → rate: 2000 (has rate context)
- "2k lbs" → weight: 2000 (has weight unit)
- "$2k" → rate: 2000 (has currency symbol)
- "Paying 2k" → rate: 2000 (payment context)
- "Load is 2k" → weight: 2000 (load description context)
- "2k all in" → rate: 2000 (payment context)
- "2k for weight" → weight: 2000 (explicit weight context)

Special Cases:
- "No special handling" → specialNotes: "No special handling"
- "9k freight of all kinds" → commodity: "freight", weight: 9000
- "10 pallets" → DO NOT include in special notes
- "Dims: 48x42x92" → length: 48, width: 42, height: 92
- "Warehouse hours 9am-5pm" → leave pickup time empty
- "Goods ready to pick up" → NOT a specific time, leave pickup time empty
- "FCFS" in pickup time → Keep it as part of the time field
- "Appt" in delivery time → Keep it as part of the time field

Return ONLY the information explicitly stated in the email. If a field is not mentioned, leave it empty.
"""

def has_value(obj, field):
    """Check if the field exists in the object and has a meaningful value.
    Returns False for: None, empty string, empty list, empty dict, etc.
    """
    if not hasattr(obj, field):
        return False

    value = getattr(obj, field)

    if value is None:
        return False

    if isinstance(value, (str, int, float, bool)) and not value:
        return False

    return True

def create_reply_extractor_llm():
    llm = init_chat_model(
        "azure_openai:gpt-4o",
        temperature=0.3,
    )
    return llm.with_structured_output(ReplyExtractorAgentResponse)

def reply_extractor(state, llm):
    """Extract structured information from the broker's reply using conversation context."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Get conversation context to help interpret short replies
    conversation_context = get_conversation_context(state)

    # Format the prompt with current time and conversation context
    prompt = f"""Current time: {current_time}

{REPLY_EXTRACTOR_PROMPT}

CONVERSATION CONTEXT (for reference only - focus on the latest reply below):
{conversation_context}

LATEST BROKER REPLY TO ANALYZE:
"""

    # llm_response = llm.invoke([
    #     SystemMessage(content=prompt),
    #     HumanMessage(content=state["reply"])
    # ])

    llm_response = {
        "commodity": "Furniture",
        "weight": 100,
        "length": 100,
        "height": 100,
        "width": 100,
        "pickupDateTime": "tomorrow",
        "deliveryDateTime": "tomorrow",
        "offeringRate": 100,
        "otherDetails": "needs 8ft tarps",
        "specialNotes": "trap needed",
        "detentionPolicy": "",
        "accessorialCharges": "",
        "loadingMethod": "",
        "appointmentRequirements": "",
    }

    load_missing_fields = get_load_missing_fields(state["load_info"])

    if llm_response.commodity:
        state["updated_load_fields"]["emailHistory.details.commodity"] = llm_response.commodity
    if llm_response.weight:
        state["updated_load_fields"]["emailHistory.details.weight"] = llm_response.weight
    if llm_response.length:
        state["updated_load_fields"]["emailHistory.details.length"] = llm_response.length
    if llm_response.height:
        state["updated_load_fields"]["emailHistory.details.height"] = llm_response.height
    if llm_response.width:
        state["updated_load_fields"]["emailHistory.details.width"] = llm_response.width
    if has_value(llm_response, "pickupDateTime"):
        state["updated_load_fields"]["emailHistory.details.pickupDateTime"] = llm_response.pickupDateTime
    if has_value(llm_response, "deliveryDateTime"):
        state["updated_load_fields"]["emailHistory.details.deliveryDateTime"] = llm_response.deliveryDateTime
    if llm_response.offeringRate:
        state["updated_load_fields"]["rateInfo.rateUsd"] = llm_response.offeringRate
        state["updated_load_fields"]["rateInfo.isAIIdentified"] = True
    if llm_response.otherDetails:
        state["updated_load_fields"]["emailHistory.details.otherDetails"] = llm_response.otherDetails
    if llm_response.specialNotes:
        state["updated_load_fields"]["emailHistory.details.specialNotes"] = llm_response.specialNotes
    if llm_response.detentionPolicy:
        state["updated_load_fields"]["emailHistory.details.detentionPolicy"] = llm_response.detentionPolicy
    if llm_response.accessorialCharges:
        state["updated_load_fields"]["emailHistory.details.accessorialCharges"] = llm_response.accessorialCharges
    if llm_response.loadingMethod:
        state["updated_load_fields"]["emailHistory.details.loadingMethod"] = llm_response.loadingMethod
    if llm_response.appointmentRequirements:
        state["updated_load_fields"]["emailHistory.details.appointmentRequirements"] = llm_response.appointmentRequirements
    if llm_response.referenceNumber:
        state["updated_load_fields"]["emailHistory.details.referenceNumber"] = llm_response.referenceNumber
    if llm_response.isTeamDriver:
        state["updated_load_fields"]["emailHistory.details.isTeamDriver"] = llm_response.isTeamDriver
    if llm_response.driverShouldLoad:
        state["updated_load_fields"]["emailHistory.details.driverShouldLoad"] = llm_response.driverShouldLoad
    if llm_response.driverShouldUnload:
        state["updated_load_fields"]["emailHistory.details.driverShouldUnload"] = llm_response.driverShouldUnload

    state["missing_fields"] = [
        field for field in load_missing_fields
        if field and not has_value(llm_response, field)
    ]

    if len(state.get("missing_fields", [])) == 0:
        if state.get("load_info", {}).get("emailHistory", {}).get("status") == EmailHistoryStatus.get("GATHERING_INFO"):
            state["updated_load_fields"]["emailHistory.status"] = EmailHistoryStatus.get("COLLECTED_INFO")

        if not state.get("load_info", {}).get("emailHistory", {}).get("isInfoRequestFinished", False):
            state["updated_load_fields"]["emailHistory.isInfoRequestFinished"] = True

    return state
