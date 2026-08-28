# -------------------------------------------------
# Terraform – seed a LocalStack account with misconfigurations
# Using AWS provider v4 for better LocalStack 1.4.0 compatibility
# -------------------------------------------------
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
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
  s3_use_path_style           = true
  endpoints {
    ec2        = var.endpoint_url
    iam        = var.endpoint_url
    s3         = var.endpoint_url
    sts        = var.endpoint_url
    lambda     = var.endpoint_url
    dynamodb   = var.endpoint_url
  }
}

variable "region"       { default = "us-east-1" }
variable "access_key"   { default = "test" }
variable "secret_key"   { default = "test" }
variable "endpoint_url" { default = "" }

# 1️⃣ Public S3 bucket
resource "aws_s3_bucket" "public_bucket" {
  bucket = "public-data"
  acl    = "public-read"
}

# 2️⃣ Over-permissive IAM role that anyone can assume
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
      Action = ["iam:PassRole", "lambda:CreateFunction"]
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

# 4️⃣ Lambda that runs as admin-role (escalation chain)
resource "aws_lambda_function" "admin_func" {
  function_name = "admin-func"
  role          = aws_iam_role.admin_role.arn
  runtime       = "python3.9"
  handler       = "index.handler"
  filename      = "dummy.zip"
  source_code_hash = filebase64sha256("dummy.zip")
}

# 5️⃣ S3 bucket with wildcard principal policy
resource "aws_s3_bucket_policy" "wildcard_policy" {
  bucket = aws_s3_bucket.public_bucket.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.public_bucket.arn}/*"
    }]
  })
}

# 6️⃣ IAM user with access key and no MFA
resource "aws_iam_user" "no_mfa_user" {
  name = "no-mfa-user"
}
resource "aws_iam_user_login_profile" "no_mfa_profile" {
  user    = aws_iam_user.no_mfa_user.name
  pgp_key = "keybase:somekey"
}
resource "aws_iam_access_key" "no_mfa_key" {
  user = aws_iam_user.no_mfa_user.name
}
resource "aws_iam_user_policy" "no_mfa_full" {
  name = "full-access"
  user = aws_iam_user.no_mfa_user.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}

# 7️⃣ IAM policy with full *:* attached to a role
resource "aws_iam_role" "wildcard_role" {
  name = "wildcard-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}
resource "aws_iam_role_policy" "wildcard_policy_role" {
  role = aws_iam_role.wildcard_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}

# 8️⃣ Security group open to world on SSH (22)
resource "aws_security_group" "sg_ssh_open" {
  name        = "ssh-open"
  description = "Open SSH to world"
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 9️⃣ Security group open to world on HTTP/HTTPS
resource "aws_security_group" "sg_web_open" {
  name        = "web-open"
  description = "Open HTTP/HTTPS to world"
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 🔟 Security group allowing all egress
resource "aws_security_group" "sg_all_egress" {
  name        = "all-egress"
  description = "Allow all outbound"
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 1️⃣1️⃣ DynamoDB table without encryption at rest
resource "aws_dynamodb_table" "ddb_no_enc" {
  name           = "ddb-no-enc"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"
  attribute {
    name = "id"
    type = "S"
  }
  server_side_encryption {
    enabled = false
  }
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
    },
    {
      id = "MC-005"
      type = "S3_BUCKET_WILDCARD_POLICY"
      resource_id = aws_s3_bucket_policy.wildcard_policy.id
      expected_severity = "HIGH"
    },
    {
      id = "MC-006"
      type = "IAM_USER_NO_MFA"
      resource_id = aws_iam_user.no_mfa_user.arn
      expected_severity = "HIGH"
    },
    {
      id = "MC-007"
      type = "IAM_USER_ACCESS_KEY_NO_MFA"
      resource_id = aws_iam_access_key.no_mfa_key.id
      expected_severity = "HIGH"
    },
    {
      id = "MC-008"
      type = "IAM_POLICY_WILDCARD"
      resource_id = aws_iam_role_policy.wildcard_policy_role.id
      expected_severity = "CRITICAL"
    },
    {
      id = "MC-009"
      type = "SG_SSH_OPEN_WORLD"
      resource_id = aws_security_group.sg_ssh_open.id
      expected_severity = "HIGH"
    },
    {
      id = "MC-010"
      type = "SG_WEB_OPEN_WORLD"
      resource_id = aws_security_group.sg_web_open.id
      expected_severity = "MEDIUM"
    },
    {
      id = "MC-011"
      type = "SG_ALL_EGRESS"
      resource_id = aws_security_group.sg_all_egress.id
      expected_severity = "LOW"
    },
    {
      id = "MC-012"
      type = "DYNAMODB_NO_ENCRYPTION"
      resource_id = aws_dynamodb_table.ddb_no_enc.arn
      expected_severity = "HIGH"
    }
  ])
  description = "Catalog of deliberately seeded misconfigurations"
}
