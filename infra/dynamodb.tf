# Key schema matches the actual application code (backend/lambdaB and
# backend/lambdaC put_item/update_item/scan calls) — NOT the old deleted
# SPEC.md, which documented a different, wrong sort key.
#
# Partition key `phone` actually holds the Expo push token (leftover naming
# from an earlier SMS-based design). Sort key `flight_data` is the composite
# string "{flight_iata}#{flight_date}".
#
# PROVISIONED at 3/3 RCU/WCU, not PAY_PER_REQUEST, so cost is a hard $0
# (comfortably inside the DynamoDB Always-Free 25 RCU / 25 WCU allocation)
# instead of usage-proportional.
resource "aws_dynamodb_table" "subscriptions" {
  name           = "${var.project_name}-subscriptions"
  billing_mode   = "PROVISIONED"
  read_capacity  = 3
  write_capacity = 3
  hash_key       = "phone"
  range_key      = "flight_data"

  attribute {
    name = "phone"
    type = "S"
  }

  attribute {
    name = "flight_data"
    type = "S"
  }

  tags = local.tags
}

# Per-source-IP request counters backing application-level rate limiting in
# predict/subscribe (see backend/lambdaA and lambdaB handler.py). The API
# Gateway stage throttle (see apigateway.tf) caps total cost across every
# caller combined but is one shared bucket — this table lets a single caller
# be capped independently so one abusive script can't starve everyone else's
# share of that bucket.
#
# `rate_key` is "{function}#{source_ip}#{window}" — a fixed 60s window
# encoded right into the key, so each window's item is naturally distinct
# and the `expires_at` TTL (DynamoDB's built-in, no-cost expiry sweep) cleans
# up old windows automatically; nothing ever needs an explicit delete.
#
# PROVISIONED at 3/3 RCU/WCU like the subscriptions table above — the API
# Gateway throttle already caps this app at 5 req/s account-wide, so 3/3 is
# never actually a bottleneck, and combined the two tables still sit well
# inside the DynamoDB Always-Free 25 RCU / 25 WCU allocation.
resource "aws_dynamodb_table" "rate_limits" {
  name           = "${var.project_name}-rate-limits"
  billing_mode   = "PROVISIONED"
  read_capacity  = 3
  write_capacity = 3
  hash_key       = "rate_key"

  attribute {
    name = "rate_key"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = local.tags
}
