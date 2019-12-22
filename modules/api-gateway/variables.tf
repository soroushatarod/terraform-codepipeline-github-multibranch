variable "api_name" {
  type = string
}

variable "github_hook_path" {
  type = string
  default = "githubhook"
}

variable "lambda_invoke_arn" {
  type = string
}

variable "lambda_name" {
  type = string
}

variable "aws_region" {
  type = string
}