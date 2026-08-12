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
