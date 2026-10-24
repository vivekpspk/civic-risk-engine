"""
hazard_taxonomy.py
Comprehensive 24-category monsoon and heavy-rain civic hazard taxonomy
for the IMPACTX 2026 Explainable Civic Risk Scoring & Priority Engine.
Provides deterministic severity ratings, consequences, warning indicators,
initial actions, urgent review rules, and NLP/keyword inference.
"""

import re
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class HazardDefinition(BaseModel):
    category_id: str
    display_name: str
    severity: float = Field(..., ge=0.0, le=1.0)
    primary_department: str
    secondary_departments: List[str] = Field(default_factory=list)
    urgent_review_required: bool = False
    urgent_review_reason: Optional[str] = None
    keywords: List[str]
    consequences: List[str]
    warning_indicators: List[str]
    recommended_action: str
    sla_hours_critical: float = 1.0
    sla_hours_high: float = 2.0
    sla_hours_routine: float = 24.0


# Configurable 24-category heavy rain taxonomy matching Section 4 of Master Prompt
RAIN_HAZARD_TAXONOMY: Dict[str, HazardDefinition] = {
    "open_manhole": HazardDefinition(
        category_id="open_manhole",
        display_name="Open or Uncovered Manhole",
        severity=1.0,
        primary_department="Drainage & Sewerage Department",
        secondary_departments=["Roads & Bridges Department", "Traffic Police"],
        urgent_review_required=True,
        urgent_review_reason="Catastrophic fall/drowning hazard for pedestrians and two-wheelers in submerged water.",
        keywords=["manhole", "uncovered manhole", "open drain hole", "sewer pit", "chamber open", "manhole cover missing"],
        consequences=["Fatal fall into deep sewer shaft", "Vehicle axle collapse", "Pedestrian drowning in turbid water"],
        warning_indicators=["Swirling water vortex", "Missing lid on road/pavement", "Submerged open opening"],
        recommended_action="Dispatch emergency cordoning squad immediately; place retroreflective barricades and temporary safety mesh.",
        sla_hours_critical=1.0,
        sla_hours_high=2.0,
    ),
    "missing_drain_cover": HazardDefinition(
        category_id="missing_drain_cover",
        display_name="Missing or Displaced Drain Cover",
        severity=0.85,
        primary_department="Drainage & Sewerage Department",
        secondary_departments=["Roads & Bridges Department"],
        urgent_review_required=True,
        urgent_review_reason="Trip and fracture hazard; rapid suction of debris blocking stormwater conduits.",
        keywords=["drain cover", "grate missing", "displaced drain grating", "slab missing", "broken drain cover"],
        consequences=["Limb fracture", "Debris jamming stormwater network", "Two-wheeler skids"],
        warning_indicators=["Exposed concrete drain edges", "Displaced cast iron grating"],
        recommended_action="Install replacement modular concrete slab or iron grate; place warning cone.",
        sla_hours_critical=2.0,
        sla_hours_high=4.0,
    ),
    "flooded_road_deep": HazardDefinition(
        category_id="flooded_road_deep",
        display_name="Flooded Road (>2.5 ft Deep Water)",
        severity=0.90,
        primary_department="Stormwater & Flood Management",
        secondary_departments=["Traffic Police", "Disaster Response"],
        urgent_review_required=True,
        urgent_review_reason="High-depth inundation submerging car exhausts and sweeping away pedestrians.",
        keywords=["deep flood", "flooded road", "waist deep water", "severe waterlogging", "water above knee", "car submerged", "submerged street"],
        consequences=["Vehicle engine hydro-lock", "Pedestrian swept by currents", "Total arterial gridlock"],
        warning_indicators=["Water level above curb height", "Abandoned floating vehicles"],
        recommended_action="Deploy high-capacity mobile dewatering diesel pumps; divert incoming vehicular traffic.",
        sla_hours_critical=1.5,
        sla_hours_high=3.0,
    ),
    "waterlog_sensitive_site": HazardDefinition(
        category_id="waterlog_sensitive_site",
        display_name="Waterlogged Streets Near Schools, Hospitals, or Transit",
        severity=0.85,
        primary_department="Stormwater & Flood Management",
        secondary_departments=["Public Health Department", "Education Dept"],
        urgent_review_required=True,
        urgent_review_reason="Direct impediment to school children, ambulances, and transit access.",
        keywords=["school waterlogged", "hospital waterlogging", "bus station flooded", "metro flooded", "near school", "hospital gate water"],
        consequences=["Ambulance entry denial", "Children stranded at dismissal", "Mass commuter disruption"],
        warning_indicators=["Flooding within 100m of institutional entrance gate"],
        recommended_action="Clear road gullies; deploy submersible pumps and deploy ward safety marshals.",
        sla_hours_critical=1.0,
        sla_hours_high=2.5,
    ),
    "flash_flood_rapid_rise": HazardDefinition(
        category_id="flash_flood_rapid_rise",
        display_name="Flash Flooding or Rapidly Rising Water",
        severity=0.95,
        primary_department="Disaster Response & Emergency Operations",
        secondary_departments=["Stormwater & Flood Management", "Police"],
        urgent_review_required=True,
        urgent_review_reason="Imminent risk of drowning, structural washouts, and residential inundation.",
        keywords=["flash flood", "water rising fast", "torrential rush", "rapid water", "surging water", "cloudburst flood"],
        consequences=["Human casualties", "Vehicle washouts", "Basement entrapment"],
        warning_indicators=["Water rising >10cm every 15 minutes", "Strong muddy current in street"],
        recommended_action="Trigger city emergency flood warning; activate public address system and stage rescue boats.",
        sla_hours_critical=0.5,
        sla_hours_high=1.5,
    ),
    "overflowing_stormwater_drain": HazardDefinition(
        category_id="overflowing_stormwater_drain",
        display_name="Overflowing Stormwater Drain / Nullah",
        severity=0.75,
        primary_department="Drainage & Sewerage Department",
        secondary_departments=["Stormwater & Flood Management"],
        urgent_review_required=False,
        keywords=["nullah overflow", "stormwater overflowing", "drain bursting", "canal overflow", "drain spilling"],
        consequences=["Spillover into adjacent roads", "Deposition of sludge and debris"],
        warning_indicators=["Water level lapping top of retaining wall", "Back-pressure bubbling"],
        recommended_action="Dispatch excavator/backhoe to remove hydraulic bottlenecks at downstream culverts.",
        sla_hours_critical=2.0,
        sla_hours_high=4.0,
    ),
    "blocked_drainage_system": HazardDefinition(
        category_id="blocked_drainage_system",
        display_name="Blocked Drainage System / Choked Culvert",
        severity=0.60,
        primary_department="Drainage & Sewerage Department",
        secondary_departments=["Solid Waste Management"],
        urgent_review_required=False,
        keywords=["choked drain", "blocked culvert", "garbage in drain", "plastic choking drain", "clogged pipe"],
        consequences=["Localized ponding", "Mosquito vector breeding", "Water back-up into homes"],
        warning_indicators=["Ponding around catch-basin with zero drain intake"],
        recommended_action="Deploy super-sucker jetting machine and manual desilting gang.",
        sla_hours_critical=3.0,
        sla_hours_high=6.0,
    ),
    "drain_overflow_into_buildings": HazardDefinition(
        category_id="drain_overflow_into_buildings",
        display_name="Drain Overflow Into Houses or Public Buildings",
        severity=0.85,
        primary_department="Drainage & Sewerage Department",
        secondary_departments=["Public Health Department", "Disaster Response"],
        urgent_review_required=True,
        urgent_review_reason="Direct health hazard, property destruction, and electrical short-circuit risk indoors.",
        keywords=["water in house", "flooding inside home", "overflow into building", "water entered school", "water inside hospital"],
        consequences=["Extensive property damage", "Electrocution indoors", "Contamination of living quarters"],
        warning_indicators=["Water entering plinths and ground-floor residential units"],
        recommended_action="Deploy portable suction pumps; issue immediate power main cutoff advisory.",
        sla_hours_critical=1.5,
        sla_hours_high=3.0,
    ),
    "sewer_overflow_contaminated": HazardDefinition(
        category_id="sewer_overflow_contaminated",
        display_name="Sewer Overflow & Sewage-Contaminated Floodwater",
        severity=0.80,
        primary_department="Drainage & Sewerage Department",
        secondary_departments=["Public Health Department"],
        urgent_review_required=False,
        keywords=["sewage overflow", "black water", "foul smell flood", "sewer mixing", "toilet backflow", "septic overflow"],
        consequences=["Outbreak of cholera/waterborne diseases", "Groundwater aquifer contamination"],
        warning_indicators=["Black or turbid water with strong domestic sewage odor"],
        recommended_action="Isolate sewer line section; apply lime/bleaching powder sanitization post-drainage.",
        sla_hours_critical=2.0,
        sla_hours_high=4.0,
    ),
    "collapsed_road_sinkhole": HazardDefinition(
        category_id="collapsed_road_sinkhole",
        display_name="Collapsed Road, Hidden Potholes, or Sinkhole",
        severity=0.90,
        primary_department="Roads & Bridges Department",
        secondary_departments=["Traffic Police"],
        urgent_review_required=True,
        urgent_review_reason="Submerged sinkholes and road cave-ins cause immediate vehicle rollover and pedestrian injury.",
        keywords=["sinkhole", "road collapsed", "cave in", "huge pothole hidden", "pavement collapsed", "road caved"],
        consequences=["Bus or car falling into crater", "Rupture of underground utility mains"],
        warning_indicators=["Sudden depression in asphalt under floodwater", "Cracking circular pavement"],
        recommended_action="Cordon off 20m perimeter with hard barricades; divert buses and heavy vehicles.",
        sla_hours_critical=1.0,
        sla_hours_high=2.0,
    ),
    "damaged_bridge_unsafe_crossing": HazardDefinition(
        category_id="damaged_bridge_unsafe_crossing",
        display_name="Damaged Bridge, Culvert, or Unsafe Water Crossing",
        severity=0.95,
        primary_department="Roads & Bridges Department",
        secondary_departments=["Disaster Response", "Police"],
        urgent_review_required=True,
        urgent_review_reason="Structural failure under hydrodynamic scour threatening mass transit collapse.",
        keywords=["bridge damaged", "bridge crack", "culvert washed out", "bridge submerged", "unsafe crossing", "bridge shaking"],
        consequences=["Bridge structural collapse", "Loss of entire transit corridor"],
        warning_indicators=["Scour around bridge piers", "Visible deck misalignment or cracks"],
        recommended_action="Close bridge to all traffic immediately; request urgent structural engineering inspection.",
        sla_hours_critical=0.5,
        sla_hours_high=1.0,
    ),
    "landslide_mudslide_rockfall": HazardDefinition(
        category_id="landslide_mudslide_rockfall",
        display_name="Landslide, Mudslide, or Falling Rocks",
        severity=0.90,
        primary_department="Disaster Response & Emergency Operations",
        secondary_departments=["Roads & Bridges Department", "Forest Department"],
        urgent_review_required=True,
        urgent_review_reason="Kinetic earth movement capable of crushing dwellings and burying roadways.",
        keywords=["landslide", "mudslide", "falling rocks", "slope collapse", "hill slide", "mud on road"],
        consequences=["Burial of vehicles/homes", "Complete arterial blockade in hilly areas"],
        warning_indicators=["Mud slurry running down cutting", "Tilted utility poles on hillside"],
        recommended_action="Evacuate downhill residences; deploy earthmovers and clear rock debris.",
        sla_hours_critical=1.0,
        sla_hours_high=2.0,
    ),
    "fallen_tree_blocking_road": HazardDefinition(
        category_id="fallen_tree_blocking_road",
        display_name="Fallen Tree or Large Branch Blocking Road",
        severity=0.55,
        primary_department="Horticulture & Parks Department",
        secondary_departments=["Roads & Bridges Department", "Traffic Police"],
        urgent_review_required=False,
        keywords=["fallen tree", "tree on road", "branch fallen", "tree collapsed", "tree blocking"],
        consequences=["Traffic congestion", "Damage to parked vehicles and overhead cables"],
        warning_indicators=["Tree trunk spanning across carriageway"],
        recommended_action="Deploy chainsaw team to chop and clear timber to road verge.",
        sla_hours_critical=2.0,
        sla_hours_high=4.0,
    ),
    "fallen_electric_pole_live_wire": HazardDefinition(
        category_id="fallen_electric_pole_live_wire",
        display_name="Fallen Electric Pole / Exposed Live Wire in Floodwater",
        severity=1.0,
        primary_department="Electricity Distribution Utility",
        secondary_departments=["Disaster Response", "Police"],
        urgent_review_required=True,
        urgent_review_reason="High-voltage electrocution via electrified standing water; immediate lethal hazard.",
        keywords=["electric wire", "live wire", "fallen pole", "sparking in water", "electric shock", "transformer spark", "wire in water"],
        consequences=["Instant lethal electrocution", "Explosion of pole-mounted transformers"],
        warning_indicators=["Sparking/hissing in puddle", "Downed black/aluminum cables in standing water"],
        recommended_action="Contact power grid sub-station for IMMEDIATE line trip; cordon 30m radius.",
        sla_hours_critical=0.5,
        sla_hours_high=1.0,
    ),
    "water_entering_electrical_substation": HazardDefinition(
        category_id="water_entering_electrical_substation",
        display_name="Water Entering Electrical Substation or Critical Utility",
        severity=0.95,
        primary_department="Electricity Distribution Utility",
        secondary_departments=["Disaster Response", "Stormwater & Flood Management"],
        urgent_review_required=True,
        urgent_review_reason="Threat of city-wide blackout, explosion, and utility shutdown.",
        keywords=["substation flooded", "water in power house", "transformer flooded", "switching yard water"],
        consequences=["Widespread municipal blackout", "Massive transformer fires"],
        warning_indicators=["Water level approaching bus-bars or panel enclosures"],
        recommended_action="Coordinate controlled grid power shutdown; deploy high-volume sandbags and dewatering pumps.",
        sla_hours_critical=0.5,
        sla_hours_high=1.5,
    ),
    "structural_collapse_risk": HazardDefinition(
        category_id="structural_collapse_risk",
        display_name="Damaged Building, Retaining Wall, or Structural Collapse",
        severity=0.95,
        primary_department="Building Safety & Municipal Engineering",
        secondary_departments=["Disaster Response", "Police"],
        urgent_review_required=True,
        urgent_review_reason="Imminent structural failure of dilapidated masonry or compound walls onto public ways.",
        keywords=["building collapse", "wall collapsed", "cracking wall", "retaining wall falling", "compound wall fell", "house cracked"],
        consequences=["Crush injuries/fatalities to pedestrians", "Burial of adjacent structures"],
        warning_indicators=["Expanding vertical diagonal fissures", "Bulging retaining stone masonry"],
        recommended_action="Evacuate adjacent buildings immediately; establish 1.5x height safety exclusion zone.",
        sla_hours_critical=0.5,
        sla_hours_high=1.5,
    ),
    "flooding_near_healthcare_facility": HazardDefinition(
        category_id="flooding_near_healthcare_facility",
        display_name="Flooding Near Hospitals, Care Facilities, or Emergency Services",
        severity=0.90,
        primary_department="Stormwater & Flood Management",
        secondary_departments=["Public Health Department", "Traffic Police"],
        urgent_review_required=True,
        urgent_review_reason="Disruption to life-saving healthcare infrastructure and patient transport.",
        keywords=["hospital flooded", "clinic waterlogged", "ambulance route blocked", "health centre water", "maternity clinic flood"],
        consequences=["Delay in critical trauma/emergency response", "Failure of backup oxygen/power equipment"],
        warning_indicators=["Water accumulating across ambulance drop-off bays"],
        recommended_action="Deploy prioritized dewatering squad; erect modular flood barriers at hospital gates.",
        sla_hours_critical=1.0,
        sla_hours_high=2.0,
    ),
    "flooding_affecting_evacuation_routes": HazardDefinition(
        category_id="flooding_affecting_evacuation_routes",
        display_name="Flooding Affecting Evacuation Routes or Arterial Corridors",
        severity=0.85,
        primary_department="Traffic Police",
        secondary_departments=["Disaster Response", "Roads & Bridges Department"],
        urgent_review_required=True,
        urgent_review_reason="Severing designated relief corridors and trapping large populations in flood zones.",
        keywords=["evacuation route blocked", "arterial road cut off", "highway flooded", "bypass submerged", "main road cut off"],
        consequences=["Stranded emergency convoys", "Impossibility of mass evacuation"],
        warning_indicators=["Key designated national/state highway corridor blocked by water"],
        recommended_action="Broadcast emergency traffic routing; station tow-trucks and heavy recovery vehicles.",
        sla_hours_critical=1.0,
        sla_hours_high=2.0,
    ),
    "drinking_water_contamination": HazardDefinition(
        category_id="drinking_water_contamination",
        display_name="Drinking-Water Contamination or Damaged Water Supply",
        severity=0.85,
        primary_department="Water Supply & Pipeline Utility",
        secondary_departments=["Public Health Department"],
        urgent_review_required=True,
        urgent_review_reason="Ingress of sewage or mud into potable water pipes causing wide epidemic.",
        keywords=["muddy tap water", "drinking water contaminated", "pipe burst in flood", "sewage in drinking water", "smelly water from tap"],
        consequences=["Outbreak of acute gastroenteritis, hepatitis", "Lack of safe drinking water"],
        warning_indicators=["Discolored turbid municipal tap supply post-rain"],
        recommended_action="Halt pipeline valve distribution; collect samples for bacteriological testing; dispatch water tankers.",
        sla_hours_critical=1.5,
        sla_hours_high=3.0,
    ),
    "overflowing_waterways_canals": HazardDefinition(
        category_id="overflowing_waterways_canals",
        display_name="Overflowing Lakes, Canals, Reservoirs, or Rivers",
        severity=0.85,
        primary_department="Irrigation & Water Resources Department",
        secondary_departments=["Disaster Response", "Stormwater & Flood Management"],
        urgent_review_required=True,
        urgent_review_reason="Breach of lake bunds and canal dykes causing catastrophic inundation of downstream settlements.",
        keywords=["lake overflowing", "canal breach", "river bank overflow", "bund damaged", "lake bund leaking", "reservoir spill"],
        consequences=["Widespread catastrophic area flooding", "Breach of earthen embankments"],
        warning_indicators=["Water overflowing weir crest by >1 ft", "Seepage on downstream face of bund"],
        recommended_action="Open sluice gates under controlled discharge; reinforce bund with sandbags.",
        sla_hours_critical=1.0,
        sla_hours_high=2.5,
    ),
    "trapped_people_or_vehicles": HazardDefinition(
        category_id="trapped_people_or_vehicles",
        display_name="People or Vehicles Trapped by Floodwater",
        severity=1.0,
        primary_department="Disaster Response & Emergency Operations",
        secondary_departments=["Fire & Rescue Services", "Police"],
        urgent_review_required=True,
        urgent_review_reason="Immediate threat to human life; hypothermia, exhaustion, or drowning risk.",
        keywords=["people trapped", "car stuck in water", "children stranded", "people on roof", "passengers trapped", "elderly stranded", "cannot escape water"],
        consequences=["Loss of life", "Medical emergencies in marooned individuals"],
        warning_indicators=["Distress calls from marooned vehicles or low-lying houses"],
        recommended_action="Dispatch motorized inflatable rescue boats and emergency search-and-rescue team immediately.",
        sla_hours_critical=0.5,
        sla_hours_high=1.0,
    ),
    "missing_road_warning_signs": HazardDefinition(
        category_id="missing_road_warning_signs",
        display_name="Missing, Damaged, or Obscured Road Warning Signs / Barricades",
        severity=0.45,
        primary_department="Roads & Bridges Department",
        secondary_departments=["Traffic Police"],
        urgent_review_required=False,
        keywords=["missing sign", "barricade washed away", "no warning sign", "sign fallen", "caution board missing"],
        consequences=["Vehicles driving blindly into flood hazard", "Pedestrian disorientation"],
        warning_indicators=["Hazardous hazard site with zero visual reflective demarcation"],
        recommended_action="Re-install high-visibility reflective warning boards and solar flashing beacons.",
        sla_hours_critical=3.0,
        sla_hours_high=6.0,
    ),
    "dangerous_construction_excavation": HazardDefinition(
        category_id="dangerous_construction_excavation",
        display_name="Dangerous Construction Excavations Exposed to Rain",
        severity=0.85,
        primary_department="Building Safety & Municipal Engineering",
        secondary_departments=["Roads & Bridges Department"],
        urgent_review_required=True,
        urgent_review_reason="Water filling unprotected building foundation pits causing soil slippage and falls.",
        keywords=["construction pit flooded", "foundation pit water", "excavation full of water", "unfenced pit", "trench flooded"],
        consequences=["Drowning in murky construction pits", "Collapse of adjacent shoring and sidewalks"],
        warning_indicators=["Water-filled deep trench without continuous metal sheeting or fence"],
        recommended_action="Issue stop-work order; compel developer to erect solid 2m barricades and pump out pit.",
        sla_hours_critical=1.5,
        sla_hours_high=3.0,
    ),
    "shallow_waterlogging": HazardDefinition(
        category_id="shallow_waterlogging",
        display_name="Shallow Waterlogging (<1 ft Depth)",
        severity=0.40,
        primary_department="Stormwater & Flood Management",
        secondary_departments=["Roads & Bridges Department"],
        urgent_review_required=False,
        keywords=["shallow water", "puddle", "water accumulating", "water accumulation", "waterlogging on side", "minor waterlogging", "street water"],
        consequences=["Minor pedestrian inconvenience", "Slowed vehicular traffic"],
        warning_indicators=["Puddle depth <15 cm along curb"],
        recommended_action="Clear roadside drainage grates of silt and leaves; monitor water recession.",
        sla_hours_critical=4.0,
        sla_hours_high=8.0,
        sla_hours_routine=24.0,
    ),
    "other_rain_hazard": HazardDefinition(
        category_id="other_rain_hazard",
        display_name="Other User-Described Rain Hazard",
        severity=0.50,
        primary_department="General Municipal Administration",
        secondary_departments=["Disaster Response"],
        urgent_review_required=False,
        keywords=["rain issue", "monsoon problem", "water problem", "drain issue"],
        consequences=["Unclassified civic impediment"],
        warning_indicators=["User reported atypical heavy rain occurrence"],
        recommended_action="Dispatch ward inspector to survey location and classify hazard category.",
        sla_hours_critical=4.0,
        sla_hours_high=8.0,
    ),
}


def classify_hazard_from_text(
    description: str,
    user_category_hint: Optional[str] = None
) -> Tuple[HazardDefinition, float, str]:
    """
    Infers the most accurate hazard category from text using regex & keyword heuristics.
    Returns: (HazardDefinition, confidence: float [0.0 - 1.0], explanation: str)
    Treats user_category_hint as an advisory hint, not unquestionable truth.
    """
    text = (description or "").lower()
    
    # 1. Critical Emergency Override Keywords (trapped people, live wires, flash floods)
    if any(k in text for k in ["trapped", "stranded on roof", "car stuck with people", "people caught in water"]):
        haz = RAIN_HAZARD_TAXONOMY["trapped_people_or_vehicles"]
        return haz, 0.95, "Urgent life safety classification: Detected trapped individuals in floodwaters."

    if any(k in text for k in ["live wire", "electric wire", "sparking in water", "electrocution", "fallen pole", "current in water"]):
        haz = RAIN_HAZARD_TAXONOMY["fallen_electric_pole_live_wire"]
        return haz, 0.95, "Urgent life safety classification: Detected live electrical hazard in wet conditions."

    if any(k in text for k in ["building collapse", "wall collapsed", "cracking wall", "retaining wall falling"]):
        haz = RAIN_HAZARD_TAXONOMY["structural_collapse_risk"]
        return haz, 0.90, "Urgent life safety classification: Detected structural collapse risk."

    if any(k in text for k in ["manhole", "uncovered manhole", "open sewer", "open drain hole", "sewer pit"]):
        # Check if near school
        if any(sk in text for sk in ["school", "kindergarten", "college", "children"]):
            haz = RAIN_HAZARD_TAXONOMY["open_manhole"]
            return haz, 0.95, "Critical risk classification: Open manhole in proximity to educational facility."
        haz = RAIN_HAZARD_TAXONOMY["open_manhole"]
        return haz, 0.92, "High severity classification: Detected open or uncovered manhole hazard."

    if any(k in text for k in ["sinkhole", "road caved", "road collapsed", "huge pothole"]):
        haz = RAIN_HAZARD_TAXONOMY["collapsed_road_sinkhole"]
        return haz, 0.88, "High severity classification: Detected road collapse or submerged sinkhole."

    if any(k in text for k in ["water in house", "water entered house", "flooding inside home", "water in school"]):
        haz = RAIN_HAZARD_TAXONOMY["drain_overflow_into_buildings"]
        return haz, 0.85, "High severity classification: Water ingress into residential/public building."

    if any(k in text for k in ["hospital", "ambulance", "clinic"]) and any(w in text for w in ["water", "flood", "blocked", "waterlog"]):
        haz = RAIN_HAZARD_TAXONOMY["flooding_near_healthcare_facility"]
        return haz, 0.90, "High severity classification: Inundation impacting healthcare facility access."

    if any(k in text for k in ["substation", "transformer flooded", "power station water"]):
        haz = RAIN_HAZARD_TAXONOMY["water_entering_electrical_substation"]
        return haz, 0.90, "High severity classification: Inundation of critical power distribution asset."

    if any(k in text for k in ["bridge damaged", "culvert washed out", "bridge submerged", "bridge crack"]):
        haz = RAIN_HAZARD_TAXONOMY["damaged_bridge_unsafe_crossing"]
        return haz, 0.90, "High severity classification: Damaged or submerged bridge crossing."

    if any(k in text for k in ["landslide", "mudslide", "falling rocks"]):
        haz = RAIN_HAZARD_TAXONOMY["landslide_mudslide_rockfall"]
        return haz, 0.88, "High severity classification: Detected slope failure or landslide."

    if any(k in text for k in ["sewage", "foul smell", "black water", "toilet overflow"]):
        haz = RAIN_HAZARD_TAXONOMY["sewer_overflow_contaminated"]
        return haz, 0.82, "Moderate-high severity: Contaminated sewage overflow."

    if any(k in text for k in ["muddy tap water", "drinking water", "pipe burst in flood"]):
        haz = RAIN_HAZARD_TAXONOMY["drinking_water_contamination"]
        return haz, 0.82, "High severity: Potable water contamination threat."

    if any(k in text for k in ["lake overflowing", "canal breach", "bund"]):
        haz = RAIN_HAZARD_TAXONOMY["overflowing_waterways_canals"]
        return haz, 0.85, "High severity: Canal breach or overflowing waterbody."

    if any(k in text for k in ["construction pit", "foundation pit", "excavation"]):
        haz = RAIN_HAZARD_TAXONOMY["dangerous_construction_excavation"]
        return haz, 0.80, "High severity: Exposed water-filled construction excavation."

    if any(k in text for k in ["tree", "branch"]) and any(w in text for w in ["fallen", "blocking", "collapsed"]):
        haz = RAIN_HAZARD_TAXONOMY["fallen_tree_blocking_road"]
        return haz, 0.85, "Moderate severity: Fallen tree or vegetation obstructing thoroughfare."

    if any(k in text for k in ["shallow", "minor waterlogging", "water accumulation", "accumulating on the side", "puddle", "waterlogging on side"]):
        haz = RAIN_HAZARD_TAXONOMY["shallow_waterlogging"]
        return haz, 0.80, "Routine/moderate severity: Shallow water accumulation."

    if any(k in text for k in ["deep water", "waist deep", "severe flooding", "water above knee", "car submerged"]):
        haz = RAIN_HAZARD_TAXONOMY["flooded_road_deep"]
        return haz, 0.85, "High severity: Severe road inundation >2.5 ft."

    if any(k in text for k in ["drain cover", "grate missing", "broken drain cover"]):
        haz = RAIN_HAZARD_TAXONOMY["missing_drain_cover"]
        return haz, 0.80, "Moderate-high severity: Displaced drain grating."

    if any(k in text for k in ["choked", "blocked drain", "clogged pipe", "plastic in drain"]):
        haz = RAIN_HAZARD_TAXONOMY["blocked_drainage_system"]
        return haz, 0.78, "Moderate severity: Choked stormwater conduit."

    if any(k in text for k in ["warning sign", "barricade washed"]):
        haz = RAIN_HAZARD_TAXONOMY["missing_road_warning_signs"]
        return haz, 0.75, "Routine-moderate severity: Missing road safety demarcation."

    # 2. Check User Category Hint as fallback
    if user_category_hint:
        clean_hint = user_category_hint.lower().strip().replace(" ", "_")
        if clean_hint in RAIN_HAZARD_TAXONOMY:
            haz = RAIN_HAZARD_TAXONOMY[clean_hint]
            return haz, 0.65, f"Categorized using citizen advisory hint '{haz.display_name}' (Pending field verification)."

    # 3. Check for general water accumulation near schools or transit
    if any(k in text for k in ["water", "flooding", "waterlogging"]):
        if any(sk in text for sk in ["school", "hospital", "bus", "metro"]):
            haz = RAIN_HAZARD_TAXONOMY["waterlog_sensitive_site"]
            return haz, 0.75, "Moderate-high severity: Waterlogging near sensitive civic facility."
        haz = RAIN_HAZARD_TAXONOMY["flooded_road_deep"]
        return haz, 0.60, "General waterlogging reported on roadway."

    # 4. Default fallback
    haz = RAIN_HAZARD_TAXONOMY["other_rain_hazard"]
    return haz, 0.40, "Unclassified heavy rain hazard; dispatched for inspection."
