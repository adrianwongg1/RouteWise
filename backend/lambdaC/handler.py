import json
import os
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr

DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

AERODATABOX_API_KEY = os.environ.get("AERODATABOX_API_KEY")
AERODATABOX_HOST = "aerodatabox.p.rapidapi.com"

# Generic, non-PII identifier — required by NWS, and this repo is public.
NWS_USER_AGENT = "(RouteWise-personal-project, github.com/adrianwongg1/RouteWise)"

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

# Lat/lon for api.weather.gov lookups, sourced from OurAirports
# (ourairports.com/data) — matches the US airports mobile/src/components/
# FlightCard.tsx already recognizes in AIRPORT_TZ/AIRPORT_CITY. NWS has no
# coverage outside the US, so there's no point extending this table further.
AIRPORT_COORDS = {
    "JFK": (40.6394, -73.7793), "LGA": (40.7772, -73.8726), "EWR": (40.6894, -74.1705),
    "BOS": (42.362, -71.0079), "PHL": (39.8719, -75.2411), "DCA": (38.8521, -77.0377),
    "IAD": (38.9445, -77.4558), "BWI": (39.1754, -76.6683), "MIA": (25.796, -80.2898),
    "FLL": (26.0726, -80.1527), "MCO": (28.4294, -81.309), "TPA": (27.9755, -82.5332),
    "ATL": (33.6367, -84.4281), "CLT": (35.214, -80.9431), "RDU": (35.8787, -78.7873),
    "DTW": (42.2138, -83.3538), "CLE": (41.4117, -81.8498), "PIT": (40.4915, -80.2329),
    "BDL": (41.9386, -72.688), "ORF": (36.8953, -76.201), "RIC": (37.5052, -77.3197),
    "ORD": (41.9786, -87.9048), "MDW": (41.786, -87.7524), "MSP": (44.8801, -93.2217),
    "STL": (38.7487, -90.37), "MCI": (39.3017, -94.7139), "MSY": (29.9934, -90.2647),
    "HOU": (29.6453, -95.2768), "IAH": (29.9844, -95.3414), "DFW": (32.8968, -97.038),
    "DAL": (32.8448, -96.8477), "AUS": (30.1975, -97.662), "SAT": (29.5337, -98.4698),
    "MEM": (35.0438, -89.9763), "BNA": (36.1245, -86.6782), "OMA": (41.3032, -95.8941),
    "DSM": (41.534, -93.6567), "MKE": (42.9472, -87.8966), "IND": (39.7173, -86.2944),
    "DEN": (39.86, -104.6738), "SLC": (40.7889, -111.9799), "ABQ": (35.04, -106.6089),
    "TUS": (32.115, -110.9381), "ELP": (31.8099, -106.3756), "BOI": (43.5644, -116.223),
    "LAX": (33.9425, -118.408), "SFO": (37.6198, -122.3748), "SJC": (37.3625, -121.9292),
    "OAK": (37.7201, -122.2212), "SEA": (47.4479, -122.3103), "PDX": (45.5887, -122.598),
    "SAN": (32.7336, -117.19), "LAS": (36.0834, -115.1518), "PHX": (33.4353, -112.0059),
    "SMF": (38.6954, -121.591), "BUR": (34.2028, -118.3581), "ONT": (34.056, -117.601),
    "SNA": (33.6751, -117.8693), "HNL": (21.3184, -157.9257), "ANC": (61.179, -149.9926),
    "FAI": (64.8151, -147.856),
}


def risk_label(p):
    if p <= 0.40:
        return "LOW"
    if p <= 0.65:
        return "MEDIUM"
    return "HIGH"


def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def send_push(push_token, title, body):
    payload = json.dumps({
        "to": push_token,
        "title": title,
        "body": body,
        "sound": "default",
    }).encode()
    req = urllib.request.Request(
        EXPO_PUSH_URL,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def update_sub(push_token, flight_data, fields):
    expr = "SET " + ", ".join(f"#{k} = :{k}" for k in fields)
    table.update_item(
        Key={"phone": push_token, "flight_data": flight_data},
        UpdateExpression=expr,
        ExpressionAttributeNames={f"#{k}": k for k in fields},
        ExpressionAttributeValues={f":{k}": v for k, v in fields.items()},
    )


def fetch_flight_status(flight_iata, flight_date):
    """Best-effort AeroDataBox lookup: resolves route/schedule/live status
    for a bare flight number. Returns a dict or None on ANY failure (no key
    configured, network error, unexpected shape) — never raises. Field names
    are provisional pending verification against a real response."""
    if not AERODATABOX_API_KEY or not flight_iata:
        return None

    url = (
        f"https://{AERODATABOX_HOST}/flights/number/"
        f"{urllib.parse.quote(flight_iata)}/{urllib.parse.quote(flight_date)}"
    )
    req = urllib.request.Request(
        url,
        headers={
            "X-RapidAPI-Key": AERODATABOX_API_KEY,
            "X-RapidAPI-Host": AERODATABOX_HOST,
            # Without an explicit UA, urllib's default "Python-urllib/x.x" gets
            # a 403 from Cloudflare in front of this API — confirmed against
            # the live endpoint, not a guess.
            "User-Agent": "RouteWise-personal-project/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        flights = data if isinstance(data, list) else []
        # A bare-date query can return more than one calendar-day instance
        # (e.g. a UTC/local boundary case) — confirmed against a live
        # response. Prefer the entry whose local departure date actually
        # matches what was asked for; fall back to the first entry rather
        # than returning nothing if none match exactly.
        flight = next(
            (f for f in flights
             if ((f.get("departure") or {}).get("scheduledTime") or {}).get("local", "").startswith(flight_date)),
            flights[0] if flights else None,
        )
        if not flight:
            return None

        dep = flight.get("departure") or {}
        arr = flight.get("arrival") or {}
        sched = (dep.get("scheduledTime") or {}).get("local") or (dep.get("scheduledTime") or {}).get("utc")
        revised = (dep.get("revisedTime") or {}).get("local") or (dep.get("revisedTime") or {}).get("utc")

        scheduled_dt = datetime.fromisoformat(sched.replace("Z", "+00:00")) if sched else None
        delay_minutes = None
        if sched and revised:
            revised_dt = datetime.fromisoformat(revised.replace("Z", "+00:00"))
            delay_minutes = round((revised_dt - scheduled_dt).total_seconds() / 60)

        return {
            "origin": (dep.get("airport") or {}).get("iata"),
            "destination": (arr.get("airport") or {}).get("iata"),
            "scheduled_dt": scheduled_dt,
            "current_status": flight.get("status"),
            "current_delay_minutes": delay_minutes,
        }
    except Exception:
        return None


def fetch_weather_adjustment(iata, dt):
    """Best-effort api.weather.gov lookup. Returns (adjustment, label) or
    None if the airport isn't in AIRPORT_COORDS, dt is outside NWS's ~7-day
    forecast horizon, or any network/parse step fails."""
    coords = AIRPORT_COORDS.get((iata or "").upper())
    if not coords:
        return None

    target = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if target < now or target > now + timedelta(days=7):
        return None

    lat, lon = coords
    headers = {"User-Agent": NWS_USER_AGENT, "Accept": "application/geo+json"}
    try:
        points_req = urllib.request.Request(f"https://api.weather.gov/points/{lat},{lon}", headers=headers)
        with urllib.request.urlopen(points_req, timeout=5) as r:
            points = json.loads(r.read())

        forecast_req = urllib.request.Request(points["properties"]["forecastHourly"], headers=headers)
        with urllib.request.urlopen(forecast_req, timeout=5) as r:
            forecast = json.loads(r.read())

        periods = forecast["properties"]["periods"]
        period = min(periods, key=lambda p: abs(datetime.fromisoformat(p["startTime"]) - target))
    except Exception:
        return None

    short = (period.get("shortForecast") or "").lower()
    pop = (period.get("probabilityOfPrecipitation") or {}).get("value") or 0
    label_detail = period.get("shortForecast", "conditions")

    if any(term in short for term in ("thunderstorm", "snow", "ice", "blizzard", "hurricane", "tornado")):
        return (0.15, f"severe weather ({label_detail}) forecast around departure time")
    if pop >= 60 or "rain" in short:
        return (0.08, f"rain likely ({label_detail}) around departure time")
    if pop >= 30:
        return (0.03, f"a chance of precipitation ({label_detail}) around departure time")
    return (-0.02, f"clear conditions ({label_detail}) forecast around departure time")


# Pure function, no I/O of its own — callers may pass in externally-sourced
# weather_adj/weather_label (real NWS data) to override the generic seasonal
# guess; falls back to the month-bucket heuristic when they're not given.
def score_flight(*, airline_code, airline_name, origin, destination, dt, has_time,
                  weather_adj=0.0, weather_label=None):
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

    if weather_label:
        weather_component = weather_adj
        factors.append((weather_label, weather_adj))
    else:
        weather_component = 0.0
        if dt.month in (6, 7, 8, 12):
            weather_component = 0.05
            factors.append(("summer storm season and holiday travel volume increase delays", weather_component))
        elif dt.month in (4, 5, 9, 10):
            weather_component = -0.03
            factors.append(("spring/fall months typically see fewer weather-related delays", weather_component))

    prob = max(0.03, min(0.95, base + tier_adj + airport_adj + time_adj + dow_adj + weather_component))

    factors.sort(key=lambda f: -abs(f[1]))
    top = [label for label, _ in factors[:2]]
    explanation = (
        "Based on general historical patterns: " + "; ".join(top) + "."
        if top else
        "No major historical risk factors stand out for this flight — risk is close to the typical baseline."
    )

    return {
        "delay_probability": round(prob, 2),
        "risk_level": risk_label(prob),
        "explanation": explanation,
    }


def predict_for_sub(sub):
    try:
        dt = datetime.fromisoformat(f"{sub['flight_date']}T{sub['scheduled_departure']}")
    except ValueError:
        dt = datetime.now(timezone.utc)

    airline_match = re.match(r"^([A-Z]{2})", sub.get("flight_iata") or "")
    airline_code = airline_match.group(1) if airline_match else None

    origin, destination = sub.get("origin"), sub.get("destination")
    weather = None
    if origin and destination:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda a: fetch_weather_adjustment(a, dt), (origin, destination)))
        candidates = [w for w in results if w]
        if candidates:
            weather = max(candidates, key=lambda w: w[0])

    return score_flight(
        airline_code=airline_code,
        airline_name=sub.get("airline", "Unknown"),
        origin=origin,
        destination=destination,
        dt=dt,
        has_time=True,
        weather_adj=weather[0] if weather else 0.0,
        weather_label=weather[1] if weather else None,
    )


def handle_preflight(sub, days_until):
    push_token = sub["phone"]
    flight = sub["flight_iata"]
    flight_data = f"{flight}#{sub['flight_date']}"
    origin, dest = sub["origin"], sub["destination"]
    sched = sub["scheduled_departure"]

    live = fetch_flight_status(flight, sub["flight_date"])
    pred = predict_for_sub(sub)

    new_prob = float(pred["delay_probability"])
    last_prob = float(sub.get("last_predicted_risk") or 0)

    new_status = (live or {}).get("current_status")
    last_status = sub.get("last_status")
    new_delay = (live or {}).get("current_delay_minutes")
    last_delay = sub.get("last_delay_minutes")
    last_delay = float(last_delay) if last_delay is not None else None

    status_lower = (new_status or "").lower()
    is_landed = status_lower in ("landed", "arrived")
    is_terminal_bad = status_lower in ("cancelled", "canceled", "diverted")
    status_changed = bool(new_status) and new_status != last_status
    delay_changed = new_delay is not None and last_delay is not None and abs(new_delay - last_delay) >= 15
    risk_changed = abs(new_prob - last_prob) > 0.05

    if not (is_landed or is_terminal_bad or status_changed or delay_changed or risk_changed):
        return

    if is_landed:
        title = f"{flight} has landed"
        body = f"Arrived at {dest}." + (f" Final delay: +{int(new_delay)} min." if new_delay else " On schedule.")
    elif is_terminal_bad:
        title = f"{flight} {status_lower}"
        body = f"{origin}→{dest} on {sub['flight_date']} — check with your airline for rebooking."
    elif delay_changed or status_changed:
        title = f"{flight} status update"
        body = (
            f"{origin}→{dest} on {sub['flight_date']} at {sched}. Now: {new_status or 'unknown'}"
            + (f", +{int(new_delay)} min delay." if new_delay else ".")
        )
    else:
        pct = round(new_prob * 100)
        label = risk_label(new_prob)
        title = f"{flight} delay risk update"
        body = (
            f"{origin}→{dest} on {sub['flight_date']} at {sched}. "
            f"Risk now {pct}% {label}."
            + (f" {days_until} days to go." if days_until > 1 else " Your flight is today!")
        )

    try:
        send_push(push_token, title=title, body=body)
    except Exception as e:
        print(f"push failed: {e}")
        return

    updates = {"last_predicted_risk": Decimal(str(new_prob))}
    if new_status is not None:
        updates["last_status"] = new_status
    if new_delay is not None:
        updates["last_delay_minutes"] = new_delay
    if is_landed or is_terminal_bad:
        updates["status"] = "completed"
    update_sub(push_token, flight_data, updates)


def should_run(days_until, hour, minute):
    if days_until > 14 or days_until < 0:
        return False
    if days_until == 0:
        return hour == 8 and minute < 15
    if 3 <= days_until <= 14:
        return hour == 9 and minute < 15
    if 1 <= days_until <= 2:
        return hour in (8, 14, 20) and minute < 15
    return False


def process(sub, now):
    try:
        fd = date.fromisoformat(sub["flight_date"])
    except ValueError:
        return

    push_token = sub["phone"]
    flight_iata = sub["flight_iata"]
    days_until = (fd - now.date()).days

    if days_until < 0:
        # Safety-net fallback: guarantees a subscription eventually completes
        # even if live status never confirmed landing (quota exhausted, no
        # AeroDataBox key, flight not found). handle_preflight() marks
        # status=completed immediately when it *does* see a landed/cancelled/
        # diverted status, so this sweep is normally a no-op by the time it runs.
        update_sub(push_token, f"{flight_iata}#{sub['flight_date']}", {"status": "completed"})
        return

    if not should_run(days_until, now.hour, now.minute):
        return

    handle_preflight(sub, days_until)


def scan_active():
    items, kwargs = [], {"FilterExpression": Attr("status").eq("active")}
    while True:
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            return items
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


def handler(_event, _context):
    now = datetime.now(timezone.utc)
    subs = scan_active()
    for sub in subs:
        try:
            process(sub, now)
        except Exception as e:
            print(f"error {sub.get('phone')}/{sub.get('flight_iata')}: {e}")
    return {"processed": len(subs)}
