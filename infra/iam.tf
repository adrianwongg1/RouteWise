data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  for_each           = local.functions
  name               = "${local.name_prefix}-${each.key}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  for_each   = local.functions
  role       = aws_iam_role.lambda[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Least-privilege: only subscribe/monitor touch DynamoDB, and each gets only
# the specific actions it actually calls (PutItem for subscribe; Scan +
# UpdateItem for monitor) — not a blanket DynamoDBFullAccess like the original
# hackathon setup. predict is filtered out here since its dynamodb_actions
# list is empty (it never touches the table).
resource "aws_iam_role_policy" "dynamodb_access" {
  for_each = { for k, v in local.functions : k => v if length(v.dynamodb_actions) > 0 }
  name     = "${local.name_prefix}-${each.key}-dynamodb"
  role     = aws_iam_role.lambda[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = each.value.dynamodb_actions
      Resource = aws_dynamodb_table.subscriptions.arn
    }]
  })
}

# Separate policy/table from dynamodb_access above: predict and subscribe
# both need to bump a per-IP counter (see dynamodb.tf's rate_limits table)
# but predict otherwise has no business touching DynamoDB at all, so this
# stays its own least-privilege grant rather than folding into the policy
# above.
resource "aws_iam_role_policy" "rate_limit_access" {
  for_each = { for k, v in local.functions : k => v if v.rate_limited }
  name     = "${local.name_prefix}-${each.key}-ratelimit"
  role     = aws_iam_role.lambda[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:UpdateItem"]
      Resource = aws_dynamodb_table.rate_limits.arn
    }]
  })
}
