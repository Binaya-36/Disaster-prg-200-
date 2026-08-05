from datetime import datetime

__version__ = "2.0.0"

THRESHOLDS = {
    "flood": {
        "rainfall_mm": 120.0,               
        "humidity_pct": 80.0,
    },
    "landslide": {
        "rainfall_mm": 150.0,
        "terrains": ("mountain", "hill"),   
    },
    "storm": {
        "wind_speed_kmh": 60.0,
    },
    "heatwave": {
        "temperature_c": 38.0,
    },
}
SCORE_CURVES = {
    "flood": [
        (120.0, 40.0),      
        (180.0, 60.0),      
        (250.0, 80.0),
        (350.0, 95.0),
        (500.0, 100.0),     
    ],
    "landslide": [
        (150.0, 45.0),
        (220.0, 65.0),
        (300.0, 85.0),
        (400.0, 100.0),
    ],
    "storm": [
        (60.0, 40.0),
        (90.0, 65.0),
        (120.0, 85.0),
        (150.0, 100.0),
    ],
    "heatwave": [
        (38.0, 40.0),
        (41.0, 60.0),
        (44.0, 80.0),
        (47.0, 100.0),
    ],
}

RISK_LEVELS = [
    (0, 24, "Low"),
    (25, 49, "Moderate"),
    (50, 74, "High"),
    (75, 100, "Severe"),
]

LEVEL_RANK = {"Low": 0, "Moderate": 1, "High": 2, "Severe": 3}


EVENT_TRIGGER_LEVELS = ("High", "Severe")

VALID_RANGES = {
    "rainfall": (0.0, 2000.0),      
    "temperature": (-60.0, 60.0),   
    "humidity": (0.0, 100.0),       
    "wind_speed": (0.0, 500.0),     
}

# --- 1f. Misc ---
MPS_TO_KMH = 3.6            
MULTI_HAZARD_BONUS = 3.0    
NO_RISK_LABEL = "No Significant Risk"

DEFAULT_TERRAIN = "hill"    

DISTRICT_TERRAIN = {
    # --- Mountain ---
    "solukhumbu": "mountain", "mustang": "mountain", "manang": "mountain",
    "dolpa": "mountain", "humla": "mountain", "mugu": "mountain",
    "jumla": "mountain", "rasuwa": "mountain", "sindhupalchok": "mountain",
    "dolakha": "mountain", "taplejung": "mountain", "bajhang": "mountain",
    "sankhuwasabha": "mountain", "darchula": "mountain", "kalikot": "mountain",

    # --- Hill ---
    "kaski": "hill", "pokhara": "hill", "tanahun": "hill", "syangja": "hill",
    "palpa": "hill", "gorkha": "hill", "lamjung": "hill", "dhading": "hill",
    "nuwakot": "hill", "kavrepalanchok": "hill", "ramechhap": "hill",
    "okhaldhunga": "hill", "ilam": "hill", "dhankuta": "hill",
    "baglung": "hill", "myagdi": "hill", "parbat": "hill", "gulmi": "hill",
    "arghakhanchi": "hill", "pyuthan": "hill", "rolpa": "hill",
    "salyan": "hill", "surkhet": "hill", "dailekh": "hill", "achham": "hill",
    "doti": "hill", "dadeldhura": "hill", "baitadi": "hill",
    "udayapur": "hill", "khotang": "hill", "bhojpur": "hill",
    "terhathum": "hill", "panchthar": "hill", "makwanpur": "hill",
    "sindhuli": "hill",

    "kathmandu": "valley", "lalitpur": "valley", "bhaktapur": "valley",
    "dang": "valley",

    "jhapa": "terai", "morang": "terai", "sunsari": "terai",
    "saptari": "terai", "siraha": "terai", "dhanusha": "terai",
    "mahottari": "terai", "sarlahi": "terai", "rautahat": "terai",
    "bara": "terai", "parsa": "terai", "chitwan": "terai",
    "nawalparasi": "terai", "rupandehi": "terai", "butwal": "terai",
    "kapilvastu": "terai", "banke": "terai", "nepalgunj": "terai",
    "bardiya": "terai", "kailali": "terai", "dhangadhi": "terai",
    "kanchanpur": "terai", "birgunj": "terai", "biratnagar": "terai",
}


def get_terrain(district):
    """
    Look up the terrain type for a district.

    Returns
    -------
    tuple(str, bool)
        (terrain_name, was_defaulted). `was_defaulted` is True when the
        district was not found, so the caller can warn the user that the
        landslide result is a guess rather than a fact.

    >>> get_terrain("Mustang")
    ('mountain', False)
    """
    if not isinstance(district, str):
        return DEFAULT_TERRAIN, True

    key = district.strip().lower()
    if key in DISTRICT_TERRAIN:
        return DISTRICT_TERRAIN[key], False
    return DEFAULT_TERRAIN, True


def list_known_districts():
    """
    Return every district in the lookup table, sorted and Title Cased.

    Member 5 can feed this straight into a Streamlit selectbox so users pick
    a valid district instead of typing a name that falls back to the default.
    """
    return sorted(name.title() for name in DISTRICT_TERRAIN)


REQUIRED_FIELDS = ("rainfall", "temperature", "humidity", "wind_speed")

FIELD_UNITS = {
    "rainfall": "mm", "temperature": "degrees C",
    "humidity": "%", "wind_speed": "km/h",
}


class WeatherDataError(Exception):
    """
    Raised when weather data cannot be used for prediction.

    A custom exception (rather than a plain ValueError) lets Member 5 catch
    exactly this problem:

        try:
            result = predict_disaster_risk(district, weather)
        except WeatherDataError as e:
            st.error(str(e))
    """
    pass


def _to_float(value, field_name):
    """
    Convert one weather reading to a float, or raise WeatherDataError.

    Covers the things that realistically go wrong: the key was missing so
    the value is None, the API sent text like "N/A", or the value is NaN.
    Booleans are rejected explicitly because True would silently become 1.0
    and look like a valid reading.
    """
    if value is None:
        raise WeatherDataError(
            f"Missing weather value: '{field_name}' was not provided."
        )

    if isinstance(value, bool):
        raise WeatherDataError(
            f"Invalid weather value: '{field_name}' must be a number, got a boolean."
        )

    try:
        number = float(value)
    except (TypeError, ValueError):
        raise WeatherDataError(
            f"Invalid weather value: '{field_name}' must be a number, got {value!r}."
        )

    # NaN and infinity parse successfully but break every comparison below.
    if number != number or number in (float("inf"), float("-inf")):
        raise WeatherDataError(
            f"Invalid weather value: '{field_name}' is not a finite number."
        )

    return number


def _check_range(value, field_name):
    """
    Reject readings outside physically possible limits.

    A humidity of 250% means the sensor or the API response is broken.
    Predicting on such data would produce a confident but meaningless
    warning, which is worse than an honest error.
    """
    low, high = VALID_RANGES[field_name]
    if not (low <= value <= high):
        raise WeatherDataError(
            f"Out-of-range weather value: '{field_name}' = {value} "
            f"{FIELD_UNITS[field_name]}; expected between {low} and {high}."
        )
    return value


def validate_district(district):
    """
    Check a district name was supplied and tidy it up.

    Returns the trimmed, Title Cased name ("  kathmandu " -> "Kathmandu").
    Raises WeatherDataError when blank, because a disaster event record
    would be useless without knowing where it applies.
    """
    if district is None:
        raise WeatherDataError("Missing district: a district name is required.")

    if not isinstance(district, str):
        raise WeatherDataError(
            f"Invalid district: expected text, got {type(district).__name__}."
        )

    cleaned = district.strip()
    if not cleaned:
        raise WeatherDataError("Invalid district: the name is empty.")

    return cleaned.title()


def validate_weather_data(weather):

    if not isinstance(weather, dict):
        raise WeatherDataError(
            f"Invalid weather data: expected a dictionary, "
            f"got {type(weather).__name__}."
        )

    # Report ALL missing fields at once rather than stopping at the first,
    # so the caller can fix everything in a single pass.
    missing = [field for field in REQUIRED_FIELDS if field not in weather]
    if missing:
        raise WeatherDataError("Missing weather fields: " + ", ".join(missing) + ".")

    clean = {}
    for field in REQUIRED_FIELDS:
        clean[field] = _check_range(_to_float(weather[field], field), field)
    return clean


def interpolate_score(value, curve):

    if not curve:
        return 0.0

    if value <= curve[0][0]:
        return curve[0][1]
    if value >= curve[-1][0]:
        return curve[-1][1]

    for index in range(len(curve) - 1):
        low_value, low_score = curve[index]
        high_value, high_score = curve[index + 1]

        if low_value <= value <= high_value:
            span = high_value - low_value
            if span == 0:                       # guard against a bad curve
                return low_score
            fraction = (value - low_value) / span
            return low_score + fraction * (high_score - low_score)

    return curve[-1][1]     # unreachable with a sorted curve; safety net


def score_for_hazard(hazard, value):

    return interpolate_score(value, SCORE_CURVES[hazard])


def clamp_score(score):
   
    return max(0, min(100, round(float(score))))


def get_risk_level(score):

    value = clamp_score(score)
    for lower, upper, label in RISK_LEVELS:
        if lower <= value <= upper:
            return label
    return RISK_LEVELS[-1][2]   # only reachable if RISK_LEVELS has a gap



def check_flood(weather, terrain):
    """
    FLOOD RULE: Rainfall > 120 mm AND Humidity > 80%.

    Both conditions must hold. Heavy rain alone can drain away; heavy rain
    with saturated air means the ground and drainage are already struggling,
    which is when water starts to pool.

    Score: base from the rainfall curve, then two modifiers --
      * humidity 80% adds 0, 100% adds 8 (less evaporation to help);
      * terrain: flat terai +6 and valleys +4 hold water, mountains -6 shed it.
    """
    rules = THRESHOLDS["flood"]
    rainfall = weather["rainfall"]
    humidity = weather["humidity"]

    if not (rainfall > rules["rainfall_mm"] and humidity > rules["humidity_pct"]):
        return None

    score = score_for_hazard("flood", rainfall)
    score += interpolate_score(humidity, [(80.0, 0.0), (100.0, 8.0)])
    score += {"terai": 6.0, "valley": 4.0, "hill": 0.0,
              "mountain": -6.0}.get(terrain, 0.0)

    return {
        "disaster_type": "Flood",
        "risk_score": clamp_score(score),
        "reason": (
            f"Rainfall {rainfall:.1f} mm exceeds {rules['rainfall_mm']:.0f} mm "
            f"and humidity {humidity:.0f}% exceeds {rules['humidity_pct']:.0f}% "
            f"on {terrain} terrain."
        ),
    }


def check_landslide(weather, terrain):
    """
    LANDSLIDE RULE: Rainfall > 150 mm AND terrain is mountain or hill.

    Terrain is a hard gate, not a modifier: flat terai land cannot produce a
    landslide no matter how much rain falls, so the rule returns None there
    even at 400 mm.

    Score: base from the rainfall curve, +8 for mountain (steeper slopes
    fail at lower rainfall than middle hills).
    """
    rules = THRESHOLDS["landslide"]
    rainfall = weather["rainfall"]

    if not (rainfall > rules["rainfall_mm"] and terrain in rules["terrains"]):
        return None

    score = score_for_hazard("landslide", rainfall)
    score += {"mountain": 8.0, "hill": 0.0}.get(terrain, 0.0)

    return {
        "disaster_type": "Landslide",
        "risk_score": clamp_score(score),
        "reason": (
            f"Rainfall {rainfall:.1f} mm exceeds {rules['rainfall_mm']:.0f} mm "
            f"on unstable {terrain} terrain."
        ),
    }


def check_storm(weather, terrain):

    rules = THRESHOLDS["storm"]
    wind = weather["wind_speed"]

    if not (wind > rules["wind_speed_kmh"]):
        return None

    return {
        "disaster_type": "Storm",
        "risk_score": clamp_score(score_for_hazard("storm", wind)),
        "reason": (
            f"Wind speed {wind:.1f} km/h exceeds "
            f"{rules['wind_speed_kmh']:.0f} km/h."
        ),
    }


def check_heatwave(weather, terrain):
   
    rules = THRESHOLDS["heatwave"]
    temperature = weather["temperature"]
    humidity = weather["humidity"]

    if not (temperature > rules["temperature_c"]):
        return None

    score = score_for_hazard("heatwave", temperature)
    score += interpolate_score(humidity, [(40.0, 0.0), (90.0, 8.0)])

    return {
        "disaster_type": "Heatwave",
        "risk_score": clamp_score(score),
        "reason": (
            f"Temperature {temperature:.1f} C exceeds "
            f"{rules['temperature_c']:.0f} C at {humidity:.0f}% humidity."
        ),
    }


# The registry the engine loops over. Add new hazards here.
ALL_RULES = [check_flood, check_landslide, check_storm, check_heatwave]


def evaluate_all_rules(weather, terrain):

    triggered = [outcome for outcome in
                 (rule(weather, terrain) for rule in ALL_RULES)
                 if outcome is not None]

    triggered.sort(key=lambda hazard: hazard["risk_score"], reverse=True)
    return triggered

LEVEL_ORDER = ["Low", "Moderate", "High", "Severe"]

ADVICE = {
    "Flood": {
        "Low": [
            "Monitor local rainfall updates and radio bulletins.",
            "Keep drains and gutters around your home clear of rubbish.",
        ],
        "Moderate": [
            "Move important documents, electronics and grain stores upstairs.",
            "Avoid walking or driving through moving water, however shallow.",
        ],
        "High": [
            "Prepare a go-bag: water, dry food, medicine, torch, documents.",
            "Identify the nearest high ground or designated shelter now.",
            "Disconnect electrical appliances if water enters the building.",
        ],
        "Severe": [
            "Evacuate low-lying areas immediately and move to higher ground.",
            "Do not cross flooded bridges, culverts or riverbanks.",
            "Contact local authorities or the emergency helpline for rescue.",
        ],
    },
    "Landslide": {
        "Low": [
            "Watch for new cracks in slopes, walls or ground near your home.",
            "Avoid unnecessary travel on hill roads during heavy rain.",
        ],
        "Moderate": [
            "Listen for cracking trees or knocking boulders.",
            "Keep away from steep slopes and freshly cut roadside banks.",
        ],
        "High": [
            "Move away from slopes with bulging ground, tilted trees or seeping water.",
            "Prepare to relocate to a flat, open area away from the hillside.",
            "Avoid overnight stays in houses directly below a steep slope.",
        ],
        "Severe": [
            "Evacuate the slope area immediately; do not wait for visible movement.",
            "Close hill roads and warn neighbours and downhill households.",
            "Report any ground movement to local authorities without delay.",
        ],
    },
    "Storm": {
        "Low": [
            "Secure loose items on roofs, balconies and in yards.",
            "Check that windows and doors close properly.",
        ],
        "Moderate": [
            "Bring livestock and vehicles under shelter.",
            "Charge phones and torches in case of a power cut.",
        ],
        "High": [
            "Stay indoors and away from windows and glass panels.",
            "Keep clear of trees, hoarding boards and electricity poles.",
            "Postpone travel until the wind eases.",
        ],
        "Severe": [
            "Shelter in the strongest interior room, away from all windows.",
            "Do not go outdoors until authorities confirm the storm has passed.",
            "Report fallen power lines; never touch or approach them.",
        ],
    },
    "Heatwave": {
        "Low": [
            "Drink water regularly, before you feel thirsty.",
            "Wear light, loose, light-coloured clothing.",
        ],
        "Moderate": [
            "Avoid outdoor work between 11 AM and 4 PM.",
            "Check on elderly neighbours, small children and outdoor workers.",
        ],
        "High": [
            "Stay in shade or a cooled room during peak afternoon hours.",
            "Add oral rehydration salts or lemon-salt water to your fluid intake.",
            "Never leave children or animals inside a parked vehicle.",
        ],
        "Severe": [
            "Suspend all outdoor labour and physical activity.",
            "Watch for heatstroke: confusion, hot dry skin, or stopping sweating.",
            "Move any affected person to shade, cool them, and seek medical help.",
        ],
    },
}

NO_RISK_ADVICE = [
    "No disaster conditions detected in the current weather data.",
    "Continue routine monitoring of weather updates.",
]


def build_recommendations(disaster_type, risk_level):

    hazard_advice = ADVICE.get(disaster_type)
    if hazard_advice is None or risk_level not in LEVEL_ORDER:
        return [f"Follow local authority guidance regarding {disaster_type}."]

    upto = LEVEL_ORDER.index(risk_level) + 1

    lines = []
    for level in LEVEL_ORDER[:upto]:
        lines.extend(hazard_advice.get(level, []))
    return lines


def build_multi_hazard_recommendations(hazards):
    if not hazards:
        return list(NO_RISK_ADVICE)

    if len(hazards) == 1:
        return build_recommendations(
            hazards[0]["disaster_type"], hazards[0]["risk_level"]
        )

    lines = []
    for hazard in hazards:
        lines.append(f"[{hazard['disaster_type']} - {hazard['risk_level']} risk]")
        lines.extend(
            build_recommendations(hazard["disaster_type"], hazard["risk_level"])
        )
    return lines

DISASTER_EVENT_COLUMNS = (
    "district", "disaster_type", "risk_score", "risk_level",
    "event_date", "event_time", "triggered_at", "status", "reason",
)

DISASTER_EVENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS disaster_events (
    event_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    district      TEXT    NOT NULL,
    disaster_type TEXT    NOT NULL,
    risk_score    INTEGER NOT NULL,
    risk_level    TEXT    NOT NULL,
    event_date    TEXT    NOT NULL,   -- YYYY-MM-DD
    event_time    TEXT    NOT NULL,   -- HH:MM:SS
    triggered_at  TEXT    NOT NULL,   -- full ISO timestamp
    status        TEXT    NOT NULL,   -- 'Active' when first created
    reason        TEXT
);
"""


def should_trigger_event(risk_level):
    return risk_level in EVENT_TRIGGER_LEVELS


def create_disaster_event(district, disaster_type, risk_score, risk_level,
                          reason="", event_time=None):
   
    if not should_trigger_event(risk_level):
        return None

    moment = event_time or datetime.now()

    return {
        "district": district,
        "disaster_type": disaster_type,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "event_date": moment.strftime("%Y-%m-%d"),
        "event_time": moment.strftime("%H:%M:%S"),
        "triggered_at": moment.isoformat(timespec="seconds"),
        "status": "Active",
        "reason": reason,
    }


def _combine_scores(hazards):

    if not hazards:
        return 0
    return clamp_score(
        hazards[0]["risk_score"] + MULTI_HAZARD_BONUS * (len(hazards) - 1)
    )


def predict_disaster_risk(district, weather, terrain=None, event_time=None):
    clean_district = validate_district(district)
    clean_weather = validate_weather_data(weather)

    warnings = []

    if terrain is None:
        terrain, was_defaulted = get_terrain(clean_district)
        if was_defaulted:
            warnings.append(
                f"District '{clean_district}' is not in the terrain table; "
                f"assumed '{terrain}'. The landslide result is an estimate."
            )
    else:
        terrain = str(terrain).strip().lower()

    hazards = evaluate_all_rules(clean_weather, terrain)

    if hazards:
        for hazard in hazards:
            hazard["risk_level"] = get_risk_level(hazard["risk_score"])
        overall_score = _combine_scores(hazards)
        disaster_type = hazards[0]["disaster_type"]
        reason = hazards[0]["reason"]
    else:
        overall_score = 0
        disaster_type = NO_RISK_LABEL
        reason = "No rule thresholds were exceeded by the current readings."

    overall_level = get_risk_level(overall_score)

    event = create_disaster_event(
        clean_district, disaster_type, overall_score,
        overall_level, reason, event_time,
    )

    recommendations = build_multi_hazard_recommendations(hazards)

    return {

        "district": clean_district,
        "disaster_type": disaster_type,
        "risk_score": overall_score,
        "risk_level": overall_level,
        "recommendations": recommendations,

        "event": event,
        "event_triggered": event is not None,


        "terrain": terrain,
        "reason": reason,
        "all_hazards": hazards,
        "weather_used": clean_weather,
        "warnings": warnings,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


def safe_predict_disaster_risk(district, weather, terrain=None, event_time=None):

    try:
        return predict_disaster_risk(district, weather, terrain, event_time)
    except WeatherDataError as error:
        return {"error": str(error)}
    except Exception as error:                      # pragma: no cover
        return {"error": f"Prediction failed unexpectedly: {error}"}


def predict_many(weather_by_district, event_time=None):

    if not isinstance(weather_by_district, dict):
        raise WeatherDataError(
            f"Expected a dictionary of district -> weather, "
            f"got {type(weather_by_district).__name__}."
        )

    results = []
    for district, weather in weather_by_district.items():
        result = safe_predict_disaster_risk(district, weather,
                                            event_time=event_time)
        if "error" in result:
            result["district"] = district
        results.append(result)

    results.sort(key=lambda item: item.get("risk_score", -1), reverse=True)
    return results


def find_affected_districts(weather_by_district, minimum_level="High",
                            event_time=None):
    if minimum_level not in LEVEL_RANK:
        raise WeatherDataError(
            f"Unknown risk level '{minimum_level}'. "
            f"Use one of: {', '.join(LEVEL_ORDER)}."
        )

    threshold = LEVEL_RANK[minimum_level]

    return [
        result for result in predict_many(weather_by_district, event_time)
        if "error" not in result
        and LEVEL_RANK.get(result["risk_level"], -1) >= threshold
    ]


def collect_disaster_events(results):
    return [
        result["event"] for result in results
        if "error" not in result and result.get("event")
    ]

def convert_wind_speed(value, unit="m/s"):
    factors = {"m/s": MPS_TO_KMH, "mps": MPS_TO_KMH,
               "km/h": 1.0, "kmh": 1.0, "mph": 1.609344}

    key = str(unit).strip().lower()
    if key not in factors:
        raise WeatherDataError(
            f"Unknown wind speed unit '{unit}'. "
            f"Use one of: {', '.join(sorted(set(factors)))}."
        )

    try:
        number = float(value)
    except (TypeError, ValueError):
        raise WeatherDataError(f"Invalid wind speed value: {value!r} is not a number.")

    return number * factors[key]


def normalise_weather(api_result, wind_unit="m/s", rainfall_mm_24h=None):
    if not isinstance(api_result, dict):
        raise WeatherDataError(
            f"Invalid weather API result: expected a dictionary, "
            f"got {type(api_result).__name__}."
        )

    if "error" in api_result:
        raise WeatherDataError(f"Weather API error: {api_result['error']}")

    needed = ("city", "temperature", "humidity", "wind_speed", "rainfall")
    missing = [key for key in needed if key not in api_result]
    if missing:
        raise WeatherDataError(
            "Weather API result is missing fields: " + ", ".join(missing) + "."
        )

    warnings = []
    if rainfall_mm_24h is not None:
        rainfall = rainfall_mm_24h
    else:
        rainfall = api_result["rainfall"]
        warnings.append(
            "Rainfall came from the API's 1-hour reading, but flood and "
            "landslide thresholds are 24-hour totals. Pass rainfall_mm_24h "
            "for an accurate result."
        )

    weather = {
        "rainfall": rainfall,
        "temperature": api_result["temperature"],
        "humidity": api_result["humidity"],
        "wind_speed": convert_wind_speed(api_result["wind_speed"], wind_unit),
    }

    return api_result["city"], weather, warnings


def predict_from_weather_api(api_result, wind_unit="m/s", rainfall_mm_24h=None,
                             terrain=None, safe=True, event_time=None):

    try:
        district, weather, warnings = normalise_weather(
            api_result, wind_unit, rainfall_mm_24h
        )
    except WeatherDataError as error:
        if safe:
            return {"error": str(error)}
        raise

    if safe:
        result = safe_predict_disaster_risk(district, weather, terrain, event_time)
    else:
        result = predict_disaster_risk(district, weather, terrain, event_time)

    if "error" not in result:
        result["warnings"] = warnings + result.get("warnings", [])

    return result
