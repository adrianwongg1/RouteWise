# RouteWise

# https://routewiseapp.netlify.app/

A flight delay risk predictor. Enter a flight number or a route, get a delay-risk
score with a plain-English explanation, and optionally subscribe for push
notifications.

Originally built at a hackathon (UCI CloudHacks) on Amazon Bedrock; now runs
on a free, deterministic, offline heuristic by default, optionally enhanced
with real flight and weather data — no external API key is *required*
anywhere in the stack, but setting one unlocks more of the app.

## How prediction works

By default there's no live flight-tracking data source and no trained model
behind this. `backend/lambdaA/handler.py` and `backend/lambdaC/handler.py`
score a flight with a small set of well-documented, general aviation
patterns:

- Airline on-time-performance tier (rough, illustrative — based on publicly
  reported DOT/BTS rankings, not a live lookup)
- Hub-airport congestion (a fixed list of chronically congested airports)
- Time of day (delays cascade later in the operating day)
- Day of week (Friday/Sunday leisure travel vs. midweek)
- Season (summer storms and winter holidays vs. shoulder months) — used as a
  fallback only; see below

Same input always produces the same output when running on the heuristic
alone. Treat that baseline result as a rough, general gut-check, not a
calibrated prediction — there's no per-flight historical data behind it.

**If `AERODATABOX_API_KEY` is set** (optional — see `infra/terraform.tfvars.example`),
two things change:
- **Route lookup**: "Flight #" searches resolve a real route/schedule via
  [AeroDataBox](https://aerodatabox.com) instead of showing "route not
  provided." Live status and delay minutes populate too.
- **Live tracking for subscriptions**: the monitor Lambda (`lambdaC`) checks
  real flight status instead of just re-running the static heuristic —
  subscriptions get pushed on an actual status change, a meaningful delay
  change, or landing, not just once at signup.

**Weather is always on for Route-mode searches** (no key needed — it's
[api.weather.gov](https://www.weather.gov/documentation/services-web-api),
free and keyless) and replaces the generic season guess with real
forecast conditions at the airports involved, whenever the flight is within
NWS's ~7-day forecast horizon. Outside that window, or if the airport isn't
in the hardcoded coordinate table, it falls back to the season guess.

Every external call in this app is best-effort: a network hiccup, missing
key, or unrecognized airport just falls back silently to the next layer down
— nothing external ever turns into a user-facing error.

## Architecture

```
mobile/    Expo React Native app (iOS + web) — Search screen, Result screen
backend/   3 AWS Lambda functions (Python, stdlib only, no dependencies)
  lambdaA    POST /predict   — score a flight
  lambdaB    POST /subscribe — save a subscription, send a confirmation push
  lambdaC    scheduled       — re-score active subscriptions every 15 min
infra/     Terraform for the AWS side (DynamoDB, Lambda, API Gateway, EventBridge)
```

Requests hit an API Gateway HTTP API in front of the two request-driven
Lambdas. A DynamoDB table stores subscriptions (partition key `phone` — holds
an Expo push token, not a phone number — sort key `flight_data`). An
EventBridge schedule invokes the monitor Lambda every 15 minutes.

## Setup

### Backend (AWS)

Requires an AWS account and [Terraform](https://developer.hashicorp.com/terraform).

```bash
aws configure --profile routewise   # your own AWS credentials

cd infra
terraform init
terraform plan
terraform apply
```

`terraform apply` prints `api_base_url` when done — use it in the next step.
Every variable has a default (see `variables.tf`); you don't need a
`terraform.tfvars` file at all unless you want to override one (e.g. the
region) or opt into real flight/weather data — see
`infra/terraform.tfvars.example` for the optional `aerodatabox_api_key`.

### Mobile app

Requires [Node.js](https://nodejs.org) and the Expo Go app on your phone.

```bash
cd mobile
npm install
cp .env.example .env   # then fill in EXPO_PUBLIC_API_BASE_URL with the
                        # api_base_url output from the Terraform step
npx expo start
```

Scan the QR code with Expo Go. `npx expo start --web` also works for a
browser-only preview (push notifications are native-only and disabled on web).

## Cost

Designed to stay inside AWS's Always-Free tier at personal-scale usage:
Lambda, DynamoDB (fixed low provisioned capacity, not on-demand), and
EventBridge cost $0 at this volume; API Gateway is free for the first 12
months per account, then a fraction of a cent per request after. A
[`monthly_budget_usd`](infra/variables.tf) alert (default $5) emails you if
that ever stops being true.

## Known limitations

- **Without `AERODATABOX_API_KEY`**: subscriptions only ever send their
  initial confirmation push (scoring is deterministic with no live data, so
  there's nothing that can change to alert on), "Flight #" search shows no
  route, and there's no live status/landing tracking. This is the default,
  zero-external-dependency mode.
- **With it**: AeroDataBox's free tier is 600 API units/month — comfortably
  enough for personal use (roughly 30 concurrent subscription lifetimes/month
  under the current polling cadence in `should_run()`), not "share the link
  with friends" scale without revisiting the cadence or upgrading tiers.
- **Weather** only covers the ~7-day NWS forecast horizon and US airports —
  most bookings are further out than that and fall back to the season guess
  regardless of whether a flight-data key is set.
- **Landing-detection latency** matches whatever cadence `should_run()`
  already provides (once/day pre-flight, 8am on travel day) — confirmed via
  live status instead of guessed via a day-after date sweep, but not
  near-real-time. The date-sweep fallback still exists as a safety net for
  when live status is unavailable or never confirms landing.
