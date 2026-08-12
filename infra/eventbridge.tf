# Fires every 15 min; should_run() inside lambdaC/handler.py decides whether
# there's actually anything to do for a given invocation based on
# days-until-flight. Scheduled rules on the default event bus invoking a
# Lambda target directly carry no EventBridge charge.
resource "aws_cloudwatch_event_rule" "monitor_schedule" {
  name                = "${var.project_name}-monitor-schedule"
  schedule_expression = "rate(15 minutes)"
  tags                = local.tags
}

resource "aws_cloudwatch_event_target" "monitor" {
  rule      = aws_cloudwatch_event_rule.monitor_schedule.name
  target_id = "lambda"
  arn       = aws_lambda_function.this["monitor"].arn
}

resource "aws_lambda_permission" "events_invoke_monitor" {
  statement_id  = "AllowEventBridgeInvokeMonitor"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this["monitor"].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.monitor_schedule.arn
}
