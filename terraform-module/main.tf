# terraform-aws-drift-guard
#
# Deploys a scheduled Lambda (container image) that runs the same
# tf-drift-guard scan against a live AWS account and posts violations
# to Slack. Publish this module to the public Terraform Registry as
# `<namespace>/drift-guard/aws`.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "drift_guard" {
  name               = "drift-guard-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

resource "aws_iam_role_policy_attachment" "readonly" {
  role       = aws_iam_role.drift_guard.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.drift_guard.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "drift_guard" {
  function_name = "tf-drift-guard-scan"
  role          = aws_iam_role.drift_guard.arn
  package_type  = "Image"
  image_uri     = var.lambda_image_uri
  timeout       = 300
  memory_size   = 512

  environment {
    variables = {
      AWS_REGION        = var.region
      REQUIRED_TAGS     = var.required_tags
      SLACK_WEBHOOK_URL = var.slack_webhook_url
      FAIL_ON_VIOLATION = "false" # Lambda shouldn't "fail"; it just alerts
    }
  }
}

resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "tf-drift-guard-schedule"
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "invoke_lambda" {
  rule = aws_cloudwatch_event_rule.schedule.name
  arn  = aws_lambda_function.drift_guard.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.drift_guard.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule.arn
}

output "lambda_function_name" {
  value = aws_lambda_function.drift_guard.function_name
}
