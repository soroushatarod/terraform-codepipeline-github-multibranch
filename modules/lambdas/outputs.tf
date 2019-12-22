output "arn" {
  value = aws_lambda_function.lambda.arn
}

output "name" {
  value = var.name
}

output "invoke_arn" {
  value = aws_lambda_function.lambda.invoke_arn
}