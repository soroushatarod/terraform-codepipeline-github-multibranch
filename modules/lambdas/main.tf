resource "aws_iam_role" "iam_for_lambda" {
  name = "${var.name}_lambda_codepipeline"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "iam_policy_for_lambda" {
  role = aws_iam_role.iam_for_lambda.id
  name = "${var.name}_policy_lambdas_gitodepipeline"
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaCloudwatch",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LambdaSSM",
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:PutParameter",
        "ssm:DeleteParameter",
        "ssm:GetParametersByPath"
      ],
      "Resource": "arn:aws:ssm:${var.aws_region}:${var.account_id}:parameter/codepipeline/*"
    },
    {
      "Sid": "LambdaCodePipeline",
      "Effect": "Allow",
      "Action": [
        "codepipeline:GetPipeline*",
        "codepipeline:CreatePipeline*",
        "codepipeline:UpdatePipeline*",
        "codepipeline:DeletePipeline*",
        "codepipeline:StartPipelineExecution*",
        "iam:PassRole"
      ],
      "Resource": "*"
    }
  ]
}
EOF
}

data "archive_file" "lambda_zip" {
  type = "zip"
  source_dir = "${path.module}/lambdas_src"
  output_path = "${path.module}/function.zip"
}


resource "aws_lambda_function" "lambda" {
  function_name = var.name
  source_code_hash = data.archive_file.lambda_zip.output_path
  filename = "${path.module}/function.zip"
  runtime = "python3.7"
  handler = var.handler
  role = aws_iam_role.iam_for_lambda.arn

  environment {
    variables = var.environment
  }
}


