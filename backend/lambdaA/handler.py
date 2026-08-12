import json
import re
from datetime import datetime, timezone

AIRLINE_CODES = {
    "AA": "American Airlines", "UA": "United Airlines", "DL": "Delta Air Lines",
    "WN": "Southwest Airlines", "B6": "JetBlue Airways", "AS": "Alaska Airlines",
    "NK": "Spirit Airlines", "F9": "Frontier Airlines", "G4": "Allegiant Air",
    "SY": "Sun Country Airlines", "HA": "Hawaiian Airlines", "VX": "Virgin America",
    "MQ": "Envoy Air", "OO": "SkyWest Airlines", "YX": "Republic Airways",
    "9E": "Endeavor Air", "YV": "Mesa Airlines", "OH": "PSA Airlines",
}

# Rough, illustrative tiers based on publicly reported DOT/BTS historical
# on-time-performance rankings — not a live ranking, not flight-specific.
AIRLINE_TIER = {
    "DL": "A", "HA": "A", "AS": "A",
    "WN": "B", "AA": "B", "UA": "B", "SY": "B", "VX": "B",
    "B6": "C", "NK": "C", "F9": "C", "G4": "C",
    "MQ": "C", "OO": "C", "YX": "C", "9E": "C", "YV": "C", "OH": "C",
}
TIER_ADJUSTMENT = {"A": -0.05, "B": 0.0, "C": 0.06}

# Airports with well-documented chronic congestion/weather delay issues.
CONGESTED_AIRPORTS = {"ORD", "EWR", "JFK", "LGA", "SFO", "BOS", "DCA", "ATL", "MIA", "PHL"}


def airline_from_iata(flight_iata: str) -> str:
    code = re.match(r"^([A-Z]{2})", flight_iata or "")
    if code:
        return AIRLINE_CODES.get(code.group(1), f"{code.group(1)} Airlines")
    return "Unknown"


CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}


def reply(status, body):
    return {"statusCode": status, "headers": CORS_HEADERS, "body": json.dumps(body)}


def risk_level(p):
    if p <= 0.40:
        return "LOW"
    if p <= 0.65:
        return "MEDIUM"
    return "HIGH"


# Deterministic, no external calls — grounded in general DOT/BTS-style patterns, not live data.
def score_flight(*, airline_code, airline_name, origin, destination, dt, has_time):
    base = 0.21
    factors = []

    tier_adj = TIER_ADJUSTMENT.get(AIRLINE_TIER.get(airline_code, "B"), 0.0)
    if tier_adj < 0:
        factors.append((f"{airline_name} has historically posted above-average on-time performance", tier_adj))
    elif tier_adj > 0:
        factors.append((f"{airline_name} has historically posted below-average on-time performance", tier_adj))

    congested = sorted({a.upper() for a in (origin, destination) if a and a.upper() in CONGESTED_AIRPORTS})
    airport_adj = 0.06 if congested else 0.0
    if congested:
        factors.append((f"{'/'.join(congested)} is a historically congestion-prone airport", airport_adj))

    time_adj = 0.0
    if has_time:
        h = dt.hour
        if 5 <= h <= 8:
            time_adj = -0.05
            factors.append(("early-morning departures tend to run on time before delays build up later in the day", time_adj))
        elif 16 <= h <= 20:
            time_adj = 0.05
            factors.append(("evening departures see more delay risk as congestion builds through the day", time_adj))
        elif h >= 21 or h <= 4:
            time_adj = 0.03
            factors.append(("late-night departures carry some accumulated delay risk", time_adj))

    dow_adj = 0.0
    if dt.weekday() in (4, 6):
        dow_adj = 0.02
        factors.append(("Friday/Sunday travel sees heavier leisure traffic", dow_adj))
    elif dt.weekday() in (1, 2):
        dow_adj = -0.02
        factors.append(("midweek flights see lighter traffic", dow_adj))

    season_adj = 0.0
    if dt.month in (6, 7, 8, 12):
        season_adj = 0.05
        factors.append(("summer storm season and holiday travel volume increase delays", season_adj))
    elif dt.month in (4, 5, 9, 10):
        season_adj = -0.03
        factors.append(("spring/fall months typically see fewer weather-related delays", season_adj))

    prob = max(0.03, min(0.95, base + tier_adj + airport_adj + time_adj + dow_adj + season_adj))

    factors.sort(key=lambda f: -abs(f[1]))
    top = [label for label, _ in factors[:2]]
    explanation = (
        "Based on general historical patterns: " + "; ".join(top) + "."
        if top else
        "No major historical risk factors stand out for this flight — risk is close to the typical baseline."
    )

    return {
        "delay_probability": round(prob, 2),
        "risk_level": risk_level(prob),
        "explanation": explanation,
    }


def handler(event, _context):
    if (event.get("requestContext", {}).get("http", {}).get("method")
            or event.get("httpMethod")) == "OPTIONS":
        return reply(204, {})

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return reply(400, {"error": "invalid JSON body"})

    flight_date = body.get("flight_date")
    if not flight_date:
        return reply(400, {"error": "flight_date is required"})

    flight_iata = body.get("flight_iata")
    origin = body.get("origin")
    destination = body.get("destination")
    departure_time = body.get("departure_time")

    if not flight_iata and not (origin and destination):
        return reply(400, {"error": "provide flight_iata or origin+destination"})

    try:
        dt = datetime.fromisoformat(flight_date)
    except ValueError:
        dt = datetime.now(timezone.utc)

    if departure_time:
        try:
            h, m = departure_time.split(":")
            dt = dt.replace(hour=int(h), minute=int(m))
        except Exception:
            departure_time = None

    airline_match = re.match(r"^([A-Z]{2})", flight_iata or "")
    airline_code = airline_match.group(1) if airline_match else None
    airline_name = airline_from_iata(flight_iata) if flight_iata else "Unknown"

    pred = score_flight(
        airline_code=airline_code,
        airline_name=airline_name,
        origin=origin,
        destination=destination,
        dt=dt,
        has_time=bool(departure_time),
    )

    return reply(200, {
        "flight_iata": flight_iata,
        "flight_date": flight_date,
        "airline": airline_name,
        "origin": origin or "???",
        "destination": destination or "???",
        "scheduled_departure": departure_time,
        "current_status": None,
        "current_delay_minutes": None,
        "predicted_probability": pred["delay_probability"],
        "risk_level": pred["risk_level"],
        "explanation": pred["explanation"],
    })
