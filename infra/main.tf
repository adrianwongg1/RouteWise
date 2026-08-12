terraform {
  required_version = ">= 1.14"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.2.0"
    }
  }

  # Local state on purpose: simplest thing that works for a single-operator
  # personal project. terraform.tfstate is the ONLY record of what's deployed —
  # back it up (iCloud/Dropbox/private repo) and never hand-delete it; losing
  # track of deployed infra is exactly the problem this migration is fixing.
  # Optional future hardening (not needed now): S3 backend + DynamoDB lock table.
}

provider "aws" {
  region  = var.aws_region
  profile = "routewise"
}

locals {
  name_prefix = var.project_name

  tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
  }

  # predict = lambdaA, subscribe = lambdaB, monitor = lambdaC.
  # Backend folder names stay as-is; these keys just drive friendlier AWS
  # resource names (routewise-predict, routewise-subscribe, routewise-monitor).
  functions = {
    predict = {
      handler_file     = "${path.module}/../backend/lambdaA/handler.py"
      dynamodb_actions = []
      timeout          = 29
    }
    subscribe = {
      handler_file     = "${path.module}/../backend/lambdaB/handler.py"
      dynamodb_actions = ["dynamodb:PutItem"]
      timeout          = 29
    }
    monitor = {
      handler_file     = "${path.module}/../backend/lambdaC/handler.py"
      dynamodb_actions = ["dynamodb:Scan", "dynamodb:UpdateItem"]
      timeout          = 60
    }
  }

  function_names = { for k, v in local.functions : k => "${local.name_prefix}-${k}" }

  # predict takes no env vars at all (pure rule-based heuristic, no external
  # calls) while subscribe/monitor need DYNAMODB_TABLE. Terraform unifies
  # these into one object type and fills predict's missing key with null —
  # the `if v != null` filter in lambda.tf strips that synthesized null back
  # out before it hits `environment.variables` (a map(string) can't hold a
  # null, so skipping that filter fails at plan time).
  env_vars = {
    predict = {}
    subscribe = {
      DYNAMODB_TABLE = aws_dynamodb_table.subscriptions.name
    }
    monitor = {
      DYNAMODB_TABLE = aws_dynamodb_table.subscriptions.name
    }
  }
}
