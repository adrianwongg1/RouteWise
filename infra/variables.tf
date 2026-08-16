variable "aws_region" {
  type        = string
  default     = "us-west-2"
  description = "AWS region to deploy into."
}

variable "project_name" {
  type        = string
  default     = "routewise"
  description = "Prefix used for all AWS resource names/tags."
}

variable "monthly_budget_usd" {
  type        = string
  default     = "5"
  description = "AWS Budgets monthly cost threshold in USD."
}

variable "budget_alert_email" {
  type        = string
  default     = "adrianwong055@gmail.com"
  description = "Email notified when the budget threshold is crossed."
}

variable "throttle_rate_limit" {
  type        = number
  default     = 5
  description = "API Gateway steady-state requests/second cap, applied before requests reach Lambda."
}

variable "throttle_burst_limit" {
  type        = number
  default     = 10
  description = "API Gateway concurrent-burst cap, on top of throttle_rate_limit."
}

variable "predict_rate_limit_per_minute" {
  type        = number
  default     = 10
  description = "Max /predict requests allowed from a single source IP per 60s window before that caller gets a 429."
}

variable "subscribe_rate_limit_per_minute" {
  type        = number
  default     = 5
  description = "Max /subscribe requests allowed from a single source IP per 60s window before that caller gets a 429."
}

variable "aerodatabox_api_key" {
  type        = string
  sensitive   = true
  default     = null
  description = "AeroDataBox (RapidAPI) key for flight-number route/status lookups. Leave unset to run predict/monitor in offline-heuristic-only mode (default, matches prior behavior)."
}
