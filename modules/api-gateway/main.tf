resource "aws_api_gateway_rest_api" "api" {
  name = var.api_name
}

resource "aws_api_gateway_resource" "api_github_resource" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id = aws_api_gateway_rest_api.api.root_resource_id
  path_part = var.github_hook_path
}

resource "aws_api_gateway_method" "api_github_method" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.api_github_resource.id
  http_method = "POST"
  authorization = "NONE"
}

locals {
  stage_name = "production"
}

resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_method.api_github_method.resource_id
  http_method = aws_api_gateway_method.api_github_method.http_method
  integration_http_method = "POST"
  type = "AWS_PROXY"
  uri = var.lambda_invoke_arn

  #this can be moved in the pipeline
  provisioner "local-exec" {
    command = "aws apigateway create-deployment --rest-api-id ${aws_api_gateway_rest_api.api.id} --region ${var.aws_region} --stage-name ${local.stage_name}"
  }
}

resource "aws_api_gateway_deployment" "api_gateway_stage" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name = local.stage_name

  depends_on = [
    aws_api_gateway_method.api_github_method
  ]
}

resource "aws_lambda_permission" "apigw" {
  statement_id = "AllowAPIGatewayInvoke"
  action = "lambda:InvokeFunction"
  function_name = var.lambda_name
  principal = "apigateway.amazonaws.com"
  source_arn = "${aws_api_gateway_rest_api.api.execution_arn}/*/POST/${var.github_hook_path}"
}
