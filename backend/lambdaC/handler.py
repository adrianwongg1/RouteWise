import json
import os
import re
import urllib.request
from datetime import date, datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr

DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

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


def predict_for_sub(sub):
    try:
        dt = datetime.fromisoformat(f"{sub['flight_date']}T{sub['scheduled_departure']}")
    except ValueError:
        dt = datetime.now(timezone.utc)

    airline_match = re.match(r"^([A-Z]{2})", sub.get("flight_iata") or "")
    airline_code = airline_match.group(1) if airline_match else None

    return score_flight(
        airline_code=airline_code,
        airline_name=sub.get("airline", "Unknown"),
        origin=sub.get("origin"),
        destination=sub.get("destination"),
        dt=dt,
        has_time=True,
    )


def handle_preflight(sub, days_until):
    push_token = sub["phone"]
    flight = sub["flight_iata"]

    pred = predict_for_sub(sub)

    new_prob = float(pred["delay_probability"])
    last = float(sub.get("last_predicted_risk") or 0)
    if abs(new_prob - last) <= 0.05:
        return

    pct = round(new_prob * 100)
    origin, dest = sub["origin"], sub["destination"]
    sched = sub["scheduled_departure"]
    label = risk_label(new_prob)

    try:
        send_push(
            push_token,
            title=f"{flight} delay risk update",
            body=(
                f"{origin}→{dest} on {sub['flight_date']} at {sched}. "
                f"Risk now {pct}% {label}."
                + (f" {days_until} days to go." if days_until > 1 else " Your flight is today!")
            ),
        )
    except Exception as e:
        print(f"push failed: {e}")
        return

    update_sub(push_token, f"{flight}#{sub['flight_date']}", {"last_predicted_risk": Decimal(str(new_prob))})


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
