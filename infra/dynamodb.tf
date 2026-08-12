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
