resource "aws_cloudwatch_event_rule" "codepipeline_status" {
  name = local.rule_name
  event_pattern = <<PATTERN
 {
  "source": [
    "aws.codepipeline"
  ],
  "detail-type": [
    "CodePipeline Pipeline Execution State Change"
  ],
  "detail": {
    "state": [
      "FAILED",
      "RESUMED",
      "SUCCEEDED",
      "CANCELED"
    ]
  }
}
PATTERN
  description = "notify github status about the pipeline progress"
}

resource "aws_cloudwatch_event_target" "lambda_to_github" {
  arn = module.lambda_github_notification.arn
  rule = aws_cloudwatch_event_rule.codepipeline_status.name
}
locals {
  lambda_name = "notify_github_on_codepipeline_progress"
  rule_name = "notify-github-on-codepipeline-status"
  action_rule_name = "codepipeline-action-to-github"
  list_of_rules = [
    local.rule_name,
    local.action_rule_name
  ]
}

module "lambda_github_notification" {
  source = "../lambdas"
  name = local.lambda_name
  handler = "app.cloudwatch_handler"
  environment = {
    "default" = "none"
  }
  account_id = var.account_id
  aws_region = var.aws_region

}


resource "aws_lambda_permission" "allow_cloudwatch" {
  count = length(local.list_of_rules)
  action = "lambda:InvokeFunction"
  function_name = local.lambda_name
  principal = "events.amazonaws.com"
  statement_id = "AllowExecutionFromCloudWatch${count.index}"

  source_arn = "arn:aws:events:${var.aws_region}:${var.account_id}:rule/${local.list_of_rules[count.index]}"
}

resource "aws_cloudwatch_event_rule" "codepipeline_action_to_github" {
  name = local.action_rule_name
  event_pattern = <<PATTERN
{
  "source": [
    "aws.codepipeline"
  ],
  "detail-type": [
    "CodePipeline Action Execution State Change"
  ],
  "detail": {
    "state": [
      "STARTED",
      "FAILED",
      "SUCCEEDED"
    ]
  }
}
PATTERN


}

resource "aws_cloudwatch_event_target" "action_to_github_target" {
  rule = local.action_rule_name
  arn = module.lambda_github_notification.arn
}