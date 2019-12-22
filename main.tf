module "lambdas" {
  source = "./modules/lambdas"
  name = "code_pipeline_manager_laravel"
  account_id = var.account_id
  aws_region = var.aws_region
  environment = {
    PIPELINE_NAME = "Laravel"
    REGION = var.aws_region
  }
  handler = "app.lambda_handler"
}

module "api_gateway" {
  source = "./modules/api-gateway"
  api_name = "github"
  github_hook_path = "github-webhook"
  lambda_invoke_arn = module.lambdas.invoke_arn
  lambda_name = module.lambdas.name
  aws_region = var.aws_region
}

module "cloudwatch" {
  source = "./modules/cloudwatch"
  account_id = var.account_id
  aws_region = var.aws_region
}
