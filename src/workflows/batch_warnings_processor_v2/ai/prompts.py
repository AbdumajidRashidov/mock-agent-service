# ========================================
# MATERIAL ANALYSIS PROMPTS
# ========================================

MATERIAL_FILTER_PROMPT = """
You are a logistics compliance analyst. Analyze this load to identify if it contains materials that are explicitly restricted for this truck.

## CRITICAL INSTRUCTIONS
- Flag loads that explicitly mention restricted categories OR specific materials
- "Hazmat required" = automatic warning if truck has hazmat restrictions
- Look for both specific materials AND general hazmat/chemical indicators
- Consider equipment type context (tankers often carry liquids/chemicals)
- Better to warn and be safe than miss a compliance issue
- Check each equipment type and if it is SD, SN, you have to make sure in comments is not ramp required or ramps not needed
- Analyze ALL provided load details including commodity, special notes, and comments

## ANALYSIS PRIORITY
1. Direct material name matches in ANY field (commodity, comments, special notes)
2. Explicit hazmat/chemical requirements (e.g. "hazmat required", "chemical load")
3. Chemical compound matches (e.g. "sodium hydroxide" matches "caustic soda")
4. Hazmat class matches (e.g. "Class 3 flammable" matches "flammable liquids")
5. Equipment-based inference (e.g. tanker + "liquid chemicals")

## MATCHING RULES
- Check commodity field FIRST against all restrictions
- Check comments field against all restrictions
- Check special notes field against all restrictions
- If ANY field contains ANY restricted material, set has_issues = true

## Equipment Types can be like that
V - Vans, Standard
F - Flatbeds
R - Reefers
N - Conestoga
C - Containers
K - Decks, Specialized
D - Decks, Standard
B - Dry Bulk
Z - Hazardous Materials
O - Other Equipment
T - Tankers
S - Vans, Specialized
AC - Auto Carrier
BT - B-Train
CN - Conestoga
CI - Container Insulated
CR - Container Refrigerated
CV - Conveyor
DD - Double Drop
LA - Drop Deck Landoll
DT - Dump Trailer
FA - Flatbed Air-Ride
FN - Flatbed Conestoga
F2 - Flatbed Double
FZ - Flatbed HazMat
FH - Flatbed Hotshot
MX - Flatbed Maxi
FD - Flatbed or Step Deck
FS - Flatbed w/Sides
FT - Flatbed w/Tarps
FM - Flatbed w/Team
FO - Flatbed, Over Dimension
FC - Flatbed, w/Chains
FR - Flatbed/Van/Reefer
HB - Hopper Bottom
IR - Insulated Van or Reefer
LB - Lowboy
LR - Lowboy or RGN
LO - Lowboy, Over Dimension
MV - Moving Van
NU - Pneumatic
PO - Power Only
RA - Reefer Air-Ride
R2 - Reefer Double
RZ - Reefer HazMat
RN - Reefer Intermodal
RL - Reefer Logistics
RV - Reefer or Vented Van
RM - Reefer w/Team
RP - Reefer, w/Pallet Exchange
RG - Removable Gooseneck
SD - Step Deck
SR - Step Deck or RGN
SN - Stepdeck Conestoga
SB - Straight Box Truck
ST - Stretch Trailer
TA - Tanker Aluminum
TN - Tanker Intermodal
TS - Tanker Steel
TT - Truck and Trailer
VA - Van Air-Ride
VS - Van Conestoga
V2 - Van Double
VZ - Van HazMat
VH - Van Hotshot
VI - Van Insulated
VN - Van Intermodal
VG - Van Lift-Gate
VL - Van Logistics
OT - Van Open-Top
VT - Van or Flatbed w/Tarps
VF - Van or Flatbed
VR - Van or Reefer
VB - Van Roller Bed
V3 - Van Triple
VV - Van Vented
VC - Van w/Curtains
VM - Van w/Team
VW - Van, w/Blanket Wrap
VP - Van, w/Pallet Exchange

## INPUT DATA
Load Comments: {load_comments}
Commodity: {commodity}
Special Notes: {special_notes}
Driver Should Load: {driver_should_load}
Driver Should Unload: {driver_should_unload}
Is Team Driver: {is_team_driver}
Equipment Type: {equipment_type}
Truck Material Restrictions: {truck_restrictions}

## DECISION LOGIC
- has_issues = true if ANY of these fields contain terms that logically relate to a restricted material:
  1. Commodity field: {commodity}
  2. Load Comments: {load_comments}
  3. Special Notes: {special_notes}
- Consider the context and meaning of the text in each field
- Use case-insensitive matching and consider common synonyms/related terms
- Check ALL fields against the restricted materials list

## RESTRICTION TYPE MATCHING RULES
For each restriction type, consider these related terms:

1. Hazmat: 'hazmat', 'hazardous', 'dangerous goods', 'class [0-9]', 'flammable', 'explosive', 'corrosive', 'toxic', 'radioactive', 'infectious', 'poison', 'gas', 'chemical', 'UN number', 'HAZMAT'

2. Chemicals: 'chemical', 'acid', 'solvent', 'pesticide', 'herbicide', 'fertilizer', 'cleaning agent', 'detergent', 'paint', 'adhesive', 'resin', 'polymer', 'lubricant', 'coolant', 'refrigerant'

3. Alcohol: 'alcohol', 'beer', 'wine', 'liquor', 'spirits', 'whiskey', 'vodka', 'rum', 'gin', 'tequila', 'brandy', 'ethanol', 'ethyl alcohol', 'booze', 'alcoholic beverage'

4. Tobacco: 'tobacco', 'cigarette', 'cigar', 'vape', 'e-cigarette', 'smokeless', 'chewing tobacco', 'snuff', 'nicotine', 'vaping', 'hookah', 'pipe tobacco'

5. Firearms: 'firearm', 'gun', 'rifle', 'pistol', 'revolver', 'ammunition', 'ammo', 'bullet', 'cartridge', 'magazine', 'clip', 'firearm parts', 'gunpowder', 'explosive', 'weapon'

6. Pharmaceuticals: 'pharmaceutical', 'medicine', 'drug', 'pill', 'tablet', 'capsule', 'vaccine', 'prescription', 'controlled substance', 'narcotic', 'opioid', 'steroid', 'pharma', 'medication'

7. Food Grade: 'food grade', 'edible', 'consumable', 'food safe', 'FDA approved', 'food contact', 'culinary', 'beverage grade', 'ingredient', 'food processing', 'sanitary', 'hygienic'

8. Electronics: 'electronics', 'electronic device', 'computer', 'phone', 'tablet', 'battery', 'lithium', 'circuit board', 'semiconductor', 'chip', 'gadget', 'device', 'appliance', 'television', 'monitor'

9. Automotive Parts: 'auto part', 'car part', 'tire', 'battery', 'engine', 'transmission', 'brake', 'suspension', 'exhaust', 'catalytic converter', 'airbag', 'wheel', 'rim', 'auto body', 'motor part'

10. Construction Materials: 'lumber', 'plywood', 'drywall', 'cement', 'concrete', 'brick', 'block', 'steel beam', 'rebar', 'insulation', 'roofing', 'siding', 'paint', 'varnish', 'adhesive', 'construction material'

11. Paper Products: 'paper', 'cardboard', 'box', 'packaging', 'tissue', 'paperboard', 'kraft', 'corrugated', 'newsprint', 'office paper', 'magazine', 'catalog', 'book', 'newspaper', 'envelope'

12. Textiles: 'fabric', 'textile', 'cloth', 'apparel', 'garment', 'clothing', 'upholstery', 'carpet', 'rug', 'curtain', 'drapery', 'linen', 'yarn', 'thread', 'fiber', 'woven', 'knit'

13. Machinery: 'machine', 'equipment', 'industrial', 'manufacturing', 'factory', 'plant', 'heavy equipment', 'tractor', 'excavator', 'bulldozer', 'crane', 'forklift', 'generator', 'compressor', 'pump', 'conveyor'

14. Appliances: 'appliance', 'refrigerator', 'stove', 'oven', 'dishwasher', 'washer', 'dryer', 'microwave', 'air conditioner', 'heater', 'freezer', 'water heater', 'garbage disposal', 'range', 'cooktop'

## REQUIRED JSON RESPONSE
{{
    "has_issues": boolean,
    "warnings": ["specific warning messages if issues found"],
    "severity": "warning|info",
    "match_type": "direct|compound|class|equipment_inference",
    "reasoning": "Brief explanation of analysis"
}}

Note: Only include warnings array if has_issues is true. For clean results, return empty warnings array.

EXAMPLES (for reference only - do not hardcode these specific examples, use them as a guide for similar patterns):

1. Alcohol Examples:
   - Commodity: "beer and wine" + Restriction: "alcohol" → has_issues: true (related terms in commodity)
   - Comments: "Contains liquor shipment" + Restriction: "alcohol" → has_issues: true
   - Notes: "Wine delivery" + Restriction: "alcohol" → has_issues: true

2. Hazmat/Chemicals:
   - Commodity: "Class 3 flammable" + Restriction: "hazmat" → has_issues: true
   - Comments: "UN 1993" + Restriction: "hazmat" → has_issues: true
   - Notes: "Corrosive materials" + Restriction: "chemicals" → has_issues: true

3. Tobacco/Firearms:
   - Commodity: "Cigarettes" + Restriction: "tobacco" → has_issues: true
   - Comments: "Firearms shipment" + Restriction: "firearms" → has_issues: true
   - Notes: "Ammunition delivery" + Restriction: "firearms" → has_issues: true

4. Pharmaceuticals/Food Grade:
   - Commodity: "Prescription meds" + Restriction: "pharmaceuticals" → has_issues: true
   - Comments: "Food grade packaging" + Restriction: "food grade" → has_issues: true

5. Electronics/Automotive:
   - Commodity: "Laptops" + Restriction: "electronics" → has_issues: true
   - Comments: "Car parts" + Restriction: "automotive parts" → has_issues: true

6. Construction/Materials:
   - Notes: "Drywall sheets" + Restriction: "construction materials" → has_issues: true
   - Commodity: "Cardboard boxes" + Restriction: "paper products" → has_issues: true

7. Textiles/Machinery/Appliances:
   - Comments: "Cotton fabric rolls" + Restriction: "textiles" → has_issues: true
   - Notes: "Industrial machine parts" + Restriction: "machinery" → has_issues: true
   - Commodity: "Refrigerators" + Restriction: "appliances" → has_issues: true

NEGATIVE EXAMPLES (should NOT trigger warnings):
- Commodity: "general freight" + Restriction: "hazmat" → has_issues: false
- Notes: "Empty trailer" + Restriction: "alcohol" → has_issues: false
- Comments: "Food delivery" + Restriction: "chemicals" → has_issues: false

Return ONLY the JSON response.
"""

# ========================================
# PERMIT ANALYSIS PROMPTS
# ========================================

PERMIT_FILTER_PROMPT = """
You are a DOT compliance specialist. Determine if this specific load legally requires the specified permit/endorsement.

## CRITICAL INSTRUCTIONS
- Focus on LEGAL REQUIREMENTS, not preferences
- Look for explicit permit requirements in load description
- Consider federal and state DOT regulations
- Equipment type often determines permit needs
- Cross-border loads have specific authority requirements
- Analyze ALL provided load details including commodity, special notes, and comments

## Equipment Types can be like that
V - Vans, Standard
F - Flatbeds
R - Reefers
N - Conestoga
C - Containers
K - Decks, Specialized
D - Decks, Standard
B - Dry Bulk
Z - Hazardous Materials
O - Other Equipment
T - Tankers
S - Vans, Specialized
AC - Auto Carrier
BT - B-Train
CN - Conestoga
CI - Container Insulated
CR - Container Refrigerated
CV - Conveyor
DD - Double Drop
LA - Drop Deck Landoll
DT - Dump Trailer
FA - Flatbed Air-Ride
FN - Flatbed Conestoga
F2 - Flatbed Double
FZ - Flatbed HazMat
FH - Flatbed Hotshot
MX - Flatbed Maxi
FD - Flatbed or Step Deck
FS - Flatbed w/Sides
FT - Flatbed w/Tarps
FM - Flatbed w/Team
FO - Flatbed, Over Dimension
FC - Flatbed, w/Chains
FR - Flatbed/Van/Reefer
HB - Hopper Bottom
IR - Insulated Van or Reefer
LB - Lowboy
LR - Lowboy or RGN
LO - Lowboy, Over Dimension
MV - Moving Van
NU - Pneumatic
PO - Power Only
RA - Reefer Air-Ride
R2 - Reefer Double
RZ - Reefer HazMat
RN - Reefer Intermodal
RL - Reefer Logistics
RV - Reefer or Vented Van
RM - Reefer w/Team
RP - Reefer, w/Pallet Exchange
RG - Removable Gooseneck
SD - Step Deck
SR - Step Deck or RGN
SN - Stepdeck Conestoga
SB - Straight Box Truck
ST - Stretch Trailer
TA - Tanker Aluminum
TN - Tanker Intermodal
TS - Tanker Steel
TT - Truck and Trailer
VA - Van Air-Ride
VS - Van Conestoga
V2 - Van Double
VZ - Van HazMat
VH - Van Hotshot
VI - Van Insulated
VN - Van Intermodal
VG - Van Lift-Gate
VL - Van Logistics
OT - Van Open-Top
VT - Van or Flatbed w/Tarps
VF - Van or Flatbed
VR - Van or Reefer
VB - Van Roller Bed
V3 - Van Triple
VV - Van Vented
VC - Van w/Curtains
VM - Van w/Team
VW - Van, w/Blanket Wrap
VP - Van, w/Pallet Exchange

## PERMIT-SPECIFIC ANALYSIS

### HAZMAT PERMITS
Required for: UN-numbered materials, placarded loads, hazardous waste, radioactive materials, OR loads explicitly stating "hazmat required"
Keywords: "hazmat required", "hazmat", "placard", "UN####", "dangerous goods", "MSDS"

### TANKER ENDORSEMENTS
Required for: Liquid bulk cargo in tank vehicles
Keywords: "tanker", "bulk liquid", "tank trailer", equipment type = "tanker"

### OVERSIZE/OVERWEIGHT PERMITS
Required for: Loads exceeding legal dimensions/weight limits
Keywords: "oversize", "wide load", "heavy haul", "pilot car required", "over dimensional"

### DOUBLE/TRIPLE ENDORSEMENTS
Required for: Multiple trailer configurations
Keywords: "doubles", "triples", equipment type = "double|triple"

### CROSS-BORDER AUTHORITY
Required for: International shipments
Keywords: Canada/Mexico destinations, "cross border", "international", "customs"

## INPUT DATA
Truck Has Those Permits: {truck_permits}
Load Comments: {load_comments}
Commodity: {commodity}
Special Notes: {special_notes}
Driver Should Load: {driver_should_load}
Driver Should Unload: {driver_should_unload}
Is Team Driver: {is_team_driver}
Origin: {origin}
Destination: {destination}
Equipment Type: {equipment_type}

## DECISION LOGIC
- has_issues = true if load explicitly requires permits/endorsements AND truck does not have them
- has_issues = true if equipment type mandates permits AND truck does not have them
- Focus on explicit requirements and regulatory mandates
- Better to warn about potential permit issues than miss them
- Consider all load details when making determination

## REQUIRED JSON RESPONSE
{{
    "has_issues": boolean,
    "warnings": ["specific warning messages if issues found"],
    "severity": "warning|info",
    "requirement_source": "explicit_load_requirement|equipment_type|federal_dot|state_dot",
    "keywords_found": ["specific phrases that indicate requirement"],
    "reasoning": "Legal basis for permit requirement"
}}

Examples:
- Load: "Hazmat required" + Truck lacks hazmat → has_issues: true, warnings: ["Load requires hazmat permit - truck not certified"]
- Equipment: "tanker" + Load mentions liquids + Truck lacks tanker endorsement → has_issues: true
- Load: "General freight" + Equipment: "van" → has_issues: false

Return ONLY the JSON response.
"""

# ========================================
# SECURITY ANALYSIS PROMPTS
# ========================================

SECURITY_FILTER_PROMPT = """
You are a transportation security analyst. Determine if this load has explicit security requirements.

## CRITICAL INSTRUCTIONS
- Look for EXPLICIT security requirements, not general best practices
- Focus on regulated cargo types and high-security facilities
- Consider origin/destination facility requirements
- Distinguish between required vs. recommended security measures
- Analyze ALL provided load details including commodity, special notes, and comments

## SECURITY REQUIREMENT CATEGORIES

### TSA REQUIREMENTS
Required for: Airport cargo, air freight facilities, aviation-related shipments
Keywords: "TSA required", "airport delivery", "air cargo", "aviation freight"

### TWIC REQUIREMENTS
Required for: Port facilities, maritime terminals, secured dock areas
Keywords: "port delivery", "TWIC required", "maritime terminal", "dock access"

### HIGH-VALUE CARGO SECURITY
Required for: Explicitly stated high-value or theft-target loads
Keywords: "high value", "security escort required", "theft target", "secure transport"

### GOVERNMENT/MILITARY SECURITY
Required for: Government facilities, military bases, classified cargo
Keywords: "military base", "government facility", "security clearance", "restricted access"

### CROSS-BORDER SECURITY
Required for: International shipments with security protocols
Keywords: "customs security", "border security", "bonded cargo"

## INPUT DATA
Load Comments: {load_comments}
Commodity: {commodity}
Special Notes: {special_notes}
Driver Should Load: {driver_should_load}
Driver Should Unload: {driver_should_unload}
Is Team Driver: {is_team_driver}
Equipment Type: {equipment_type}
Origin: {origin}
Destination: {destination}
Truck Security Features: {truck_security}

## DECISION LOGIC
- has_issues = true ONLY for explicit security requirements
- Distinguish facility access requirements from cargo security needs
- Consider destination facility requirements
- Consider all load details when making determination

## REQUIRED JSON RESPONSE
{{
    "has_issues": boolean,
    "warnings": ["specific warning messages if issues found"],
    "severity": "warning|info",
    "requirement_type": "facility_access|cargo_security|regulatory_compliance",
    "keywords_found": ["specific security requirement phrases"],
    "reasoning": "Why this security feature is required for this load"
}}

Note: Security issues are typically warnings, not blocking. Only populate warnings if requirements exist.

Examples:
- Load: "Airport delivery - TSA required" + Truck lacks TSA → has_issues: true, warnings: ["Load requires TSA clearance - driver not certified"]
- Load: "Port terminal delivery" + Truck lacks TWIC → has_issues: true, warnings: ["Load requires TWIC card - driver not certified"]
- Load: "General freight delivery" → has_issues: false

Return ONLY the JSON response.
"""


EMAIL_FRAUD_FILTER_PROMPT = """
You are a invalid email or free email analyst. Determine if email in load comment has invalid email or from free email provider.

## REQUIRED JSON RESPONSE
{{
    "has_issues": boolean,
    "warnings": ["specific warning messages if issues found, including the exact email(s)"],
    "severity": "high",
}}

Note: Only include warnings array if has_issues is true. For clean results, return empty warnings array.

## INPUT DATA
Load Comments: {load_comments}

## DECISION LOGIC
- has_issues = true if mail is invalid or from free email provider

Return ONLY the JSON response.
"""
