# RouteWise

# https://routewiseapp.netlify.app/

A flight delay risk predictor. Enter a flight number or a route, get a delay-risk
score with a plain-English explanation, and optionally subscribe for push
notifications.

Originally built at a hackathon (UCI CloudHacks) on Amazon Bedrock; now runs
entirely on a free, deterministic, offline heuristic instead — no external API
key required anywhere in the stack.

## How prediction works

There's no live flight-tracking data source and no trained model behind this.
`backend/lambdaA/handler.py` and `backend/lambdaC/handler.py` score a flight
with a small set of well-documented, general aviation patterns:

- Airline on-time-performance tier (rough, illustrative — based on publicly
  reported DOT/BTS rankings, not a live lookup)
- Hub-airport congestion (a fixed list of chronically congested airports)
- Time of day (delays cascade later in the operating day)
- Day of week (Friday/Sunday leisure travel vs. midweek)
- Season (summer storms and winter holidays vs. shoulder months)

Same input always produces the same output. Treat the result as a rough,
general gut-check, not a calibrated prediction — there's no per-flight
historical data or live signal (weather, ATC delays, inbound-aircraft status)
behind it. Search using **Route mode** (origin + destination + date + time)
for the most complete result; **Flight # mode** only has the airline-tier
signal to go on, since there's no route/schedule lookup for a bare flight
number.

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
`terraform.tfvars` file unless you want to override one, e.g. the region.

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

- Subscriptions currently only send their initial confirmation push. The
  "notify if risk changes" check in `lambdaC` re-scores each active
  subscription every 15 minutes, but since scoring is deterministic and
  nothing about a saved subscription changes over time, it can never detect
  a change to alert on.
- No live flight-status tracking (gate changes, actual delays, landing) —
  the original spec's day-of live polling was never wired to a data source.
