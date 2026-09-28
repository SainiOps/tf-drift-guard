variable "schedule_expression" {
  description = "EventBridge schedule (e.g. rate(1 hour), cron(...))"
  type        = string
  default     = "rate(6 hours)"
}

variable "required_tags" {
  description = "Comma-separated required tag keys"
  type        = string
  default     = "owner,environment"
}

variable "slack_webhook_url" {
  description = "Slack incoming webhook URL for alerts (leave empty to disable)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "lambda_image_uri" {
  description = "ECR image URI containing the drift-guard scan container"
  type        = string
}
