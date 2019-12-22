output "aws_api_endpoint" {
  value = "${aws_api_gateway_deployment.api_gateway_stage.invoke_url}/${var.github_hook_path}"
}