variable "name" {
  type = "string"
}

variable "account_id" {
  type = "string"
}

variable "aws_region" {
  type = "string"
}

variable "environment" {
  type = map(string)

  default = {
    TEST = "test"
  }
}

variable "handler" {
  type = string
}

