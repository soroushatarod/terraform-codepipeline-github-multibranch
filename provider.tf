variable "access_key" {}
variable "secret_key" {}
variable "account_id" {}
variable "aws_region" {}

provider "aws" {
  region = var.aws_region
  access_key = var.access_key
  secret_key = var.secret_key
}