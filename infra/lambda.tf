data "archive_file" "lambda_zip" {
  for_each    = local.functions
  type        = "zip"
  source_file = each.value.handler_file
  output_path = "${path.module}/build/${each.key}.zip"
}

resource "aws_cloudwatch_log_group" "lambda" {
  for_each          = local.functions
  name              = "/aws/lambda/${local.function_names[each.key]}"
  retention_in_days = 14
  tags              = local.tags
}

resource "aws_lambda_function" "this" {
  for_each         = local.functions
  function_name    = local.function_names[each.key]
  role             = aws_iam_role.lambda[each.key].arn
  runtime          = "python3.13"
  handler          = "handler.handler"
  filename         = data.archive_file.lambda_zip[each.key].output_path
  source_code_hash = data.archive_file.lambda_zip[each.key].output_base64sha256
  timeout          = each.value.timeout
  memory_size      = 512

  environment {
    variables = { for k, v in local.env_vars[each.key] : k => v if v != null }
  }

  tags       = local.tags
  depends_on = [aws_cloudwatch_log_group.lambda]
}
