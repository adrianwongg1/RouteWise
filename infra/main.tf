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
      # Each due subscription can now make a few sequential external HTTP
      # calls (AeroDataBox + weather) instead of pure in-memory scoring;
      # several subscriptions due in one 15-min tick, processed sequentially,
      # could exceed the old 60s. No cost implication — Lambda bills actual
      # duration, not this ceiling.
      timeout = 120
    }
  }

  function_names = { for k, v in local.functions : k => "${local.name_prefix}-${k}" }

  # predict has one optional env var (AeroDataBox key — null/unset by
  # default) while subscribe/monitor need DYNAMODB_TABLE, and monitor also
  # gets the AeroDataBox key. Terraform unifies these into one object type
  # and fills each function's missing keys with null — the `if v != null`
  # filter in lambda.tf strips those synthesized nulls back out before they
  # hit `environment.variables` (a map(string) can't hold a null, so
  # skipping that filter fails at plan time). This is also why
  # aerodatabox_api_key's Terraform default is `null` and not `""`: unset
  # means the key is omitted from the environment entirely, not present as
  # an empty string, so `os.environ.get("AERODATABOX_API_KEY")` in Python
  # cleanly returns None with no extra handling needed.
  env_vars = {
    predict = {
      AERODATABOX_API_KEY = var.aerodatabox_api_key
    }
    subscribe = {
      DYNAMODB_TABLE = aws_dynamodb_table.subscriptions.name
    }
    monitor = {
      DYNAMODB_TABLE      = aws_dynamodb_table.subscriptions.name
      AERODATABOX_API_KEY = var.aerodatabox_api_key
    }
  }
}
