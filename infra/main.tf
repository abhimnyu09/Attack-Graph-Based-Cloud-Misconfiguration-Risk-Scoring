# -------------------------------------------------
# Terraform – seed a LocalStack (or real AWS) account
# with ~30 deliberate misconfigurations.
# -------------------------------------------------
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = var.region
  access_key                  = var.access_key
  secret_key                  = var.secret_key
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    # Use LocalStack if ENDPOINT_URL env var is set
    ec2        = var.endpoint_url
    iam        = var.endpoint_url
    s3         = var.endpoint_url
    sts        = var.endpoint_url
    lambda     = var.endpoint_url
  }
}

variable "region"       { default = "us-east-1" }
variable "access_key"   { default = "test" }
variable "secret_key"   { default = "test" }
variable "endpoint_url" { default = "" }   # empty = real AWS

# -------------------------------------------------
# Example misconfigurations (expand to ~30)
# -------------------------------------------------
# 1️⃣ Public S3 bucket
resource "aws_s3_bucket" "public_bucket" {
  bucket = "public-data"
  acl    = "public-read"
}

# 2️⃣ Over‑permissive IAM role that anyone can assume
resource "aws_iam_role" "dev_role" {
  name = "dev-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = "*"
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "dev_role_policy" {
  role = aws_iam_role.dev_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "iam:PassRole",
        "lambda:CreateFunction"
      ]
      Resource = "*"
    }]
  })
}

# 3️⃣ Admin Lambda role (full admin)
resource "aws_iam_role" "admin_role" {
  name = "admin-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "admin_full" {
  role       = aws_iam_role.admin_role.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

# 4️⃣ Lambda that runs as admin-role (creates escalation chain)
resource "aws_lambda_function" "admin_func" {
  function_name = "admin-func"
  role          = aws_iam_role.admin_role.arn
  runtime       = "python3.9"
  handler       = "index.handler"
  filename      = "dummy.zip"   # placeholder – not actually deployed
  source_code_hash = filebase64sha256("dummy.zip")
}

# -------------------------------------------------
# Output catalog for the scanner
# -------------------------------------------------
output "misconfig_catalog" {
  value = jsonencode([
    {
      id = "MC-001"
      type = "S3_PUBLIC_READ"
      resource_id = aws_s3_bucket.public_bucket.arn
      expected_severity = "MEDIUM"
    },
    {
      id = "MC-002"
      type = "IAM_ROLE_ASSUMABLE_BY_ANYONE"
      resource_id = aws_iam_role.dev_role.arn
      expected_severity = "HIGH"
    },
    {
      id = "MC-003"
      type = "IAM_ROLE_PASSROLE_LAMBDA_CREATE"
      resource_id = aws_iam_role.dev_role.arn
      expected_severity = "HIGH"
    },
    {
      id = "MC-004"
      type = "LAMBDA_RUNS_AS_ADMIN"
      resource_id = aws_lambda_function.admin_func.arn
      expected_severity = "CRITICAL"
    }
  ])
  description = "Catalog of deliberately seeded misconfigurations"
}
