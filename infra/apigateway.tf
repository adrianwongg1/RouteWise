# CORS handled at the API level — no explicit OPTIONS routes needed.
# API Gateway answers preflight itself here without invoking Lambda at all.
# The Lambdas' own manual OPTIONS handling (see handler.py) becomes
# unreachable-but-harmless through this path; left in place since it's useful
# if a function is ever invoked directly (e.g. a Function URL) instead.
resource "aws_apigatewayv2_api" "this" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["content-type"]
  }

  tags = local.tags
}

# $default stage (not a named stage) so the invoke URL has no extra path
# segment — matches what mobile/.env.example documents and what
# mobile/src/api/predict.ts + subscribe.ts expect: `${API_BASE_URL}/predict`.
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true
  tags        = local.tags
}

resource "aws_apigatewayv2_integration" "predict" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.this["predict"].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "subscribe" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.this["subscribe"].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "predict" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "POST /predict"
  target    = "integrations/${aws_apigatewayv2_integration.predict.id}"
}

resource "aws_apigatewayv2_route" "subscribe" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "POST /subscribe"
  target    = "integrations/${aws_apigatewayv2_integration.subscribe.id}"
}

resource "aws_lambda_permission" "apigw_predict" {
  statement_id  = "AllowAPIGatewayInvokePredict"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this["predict"].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}

resource "aws_lambda_permission" "apigw_subscribe" {
  statement_id  = "AllowAPIGatewayInvokeSubscribe"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this["subscribe"].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}
