output "api_base_url" {
  description = "Paste into mobile/.env as EXPO_PUBLIC_API_BASE_URL"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.subscriptions.name
}

output "lambda_function_names" {
  value = { for k, f in aws_lambda_function.this : k => f.function_name }
}
