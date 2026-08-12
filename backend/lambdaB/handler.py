import json
import os
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal

import boto3

DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}

REQUIRED = (
    "push_token",
    "flight_iata",
    "flight_date",
    "origin",
    "destination",
    "scheduled_departure",
    "predicted_risk",
)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def reply(status, body):
    return {"statusCode": status, "headers": CORS_HEADERS, "body": json.dumps(body)}


def risk_label(p):
    if p <= 0.40:
        return "LOW"
    if p <= 0.65:
        return "MEDIUM"
    return "HIGH"


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


def handler(event, _context):
    if (event.get("requestContext", {}).get("http", {}).get("method")
            or event.get("httpMethod")) == "OPTIONS":
        return reply(204, {})

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return reply(400, {"error": "invalid JSON body"})

    missing = [k for k in REQUIRED if body.get(k) is None]
    if missing:
        return reply(400, {"error": f"missing fields: {missing}"})

    push_token = body["push_token"]
    flight_iata = body["flight_iata"]
    flight_date = body["flight_date"]
    risk = float(body["predicted_risk"])
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    item = {
        "phone": push_token,
        "flight_data": f"{flight_iata}#{flight_date}",
        "flight_iata": flight_iata,
        "flight_date": flight_date,
        "origin": body["origin"],
        "destination": body["destination"],
        "scheduled_departure": body["scheduled_departure"],
        "airline": body.get("airline", "Unknown"),
        "predicted_risk": Decimal(str(risk)),
        "last_predicted_risk": Decimal(str(risk)),
        "last_delay_minutes": None,
        "status": "active",
        "created_at": now,
    }

    try:
        table.put_item(Item=item)
    except Exception as e:
        return reply(500, {"error": f"dynamodb error: {e}"})

    pct = round(risk * 100)
    label = risk_label(risk)
    flight = body["flight_iata"]
    origin, dest = body["origin"], body["destination"]
    sched = body["scheduled_departure"]

    try:
        send_push(
            push_token,
            title=f"Watching {flight} ✈️",
            body=(
                f"{origin} → {dest} on {body['flight_date']} at {sched}. "
                f"Current delay risk: {pct}% ({label}). "
                f"You'll be notified of any status changes."
            ),
        )
    except Exception as e:
        # Don't fail the subscribe if the confirmation push fails
        print(f"push confirmation failed: {e}")

    return reply(200, {"subscribed": True})
