# -------------------------------------------------
# Terraform – seed a LocalStack (or real AWS) account
# with a minimal set of deliberate misconfigurations
# that are known to work on LocalStack 1.4.0.
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
    ec2        = var.endpoint_url
    iam        = var.endpoint_url
    s3         = var.endpoint_url
    sts        = var.endpoint_url
    lambda     = var.endpoint_url
    dynamodb   = var.endpoint_url
    kms        = var.endpoint_url
  }
}

variable "region"       { default = "us-east-1" }
variable "access_key"   { default = "test" }
variable "secret_key"   { default = "test" }
variable "endpoint_url" { default = "" }

# -------------------------------------------------
# Misconfiguration resources
# -------------------------------------------------

# 1️⃣ Public S3 bucket
resource "aws_s3_bucket" "public_bucket" {
  bucket = "public-data"
  acl    = "public-read"
}

# 2️⃣ Second public bucket (no encryption)
resource "aws_s3_bucket" "public_bucket_no_enc" {
  bucket = "public-data-no-enc"
  acl    = "public-read"
}

# 3️⃣ S3 bucket policy with wildcard principal
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

# 4️⃣ S3 bucket versioning suspended
resource "aws_s3_bucket_versioning" "no_versioning" {
  bucket = aws_s3_bucket.public_bucket.id
  versioning_configuration {
    status = "Suspended"
  }
}

# 5️⃣ Over‑permissive IAM role assumable by anyone
resource "aws_iam_role" "dev_role" {
  name = "dev-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "dev_role_policy" {
  role = aws_iam_role.dev_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["iam:PassRole", "lambda:CreateFunction"]
      Resource = "*"
    }]
  })
}

# 6️⃣ Admin role (full admin) for Lambda
resource "aws_iam_role" "admin_role" {
  name = "admin-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "admin_full" {
  role       = aws_iam_role.admin_role.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

# 7️⃣ Second admin role attached directly (duplicate)
resource "aws_iam_role" "admin_role_direct" {
  name = "admin-role-direct"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "admin_direct_full" {
  role       = aws_iam_role.admin_role_direct.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

# 8️⃣ Wildcard IAM role (full *:* policy)
resource "aws_iam_role" "wildcard_role" {
  name = "wildcard-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
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

# 9️⃣ IAM user with access key, no MFA, full policy
resource "aws_iam_user" "no_mfa_user" {
  name = "no-mfa-user"
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

# 🔟 Dev role policy (PassRole + Lambda create)
resource "aws_iam_role_policy" "dev_role_policy" {
  role = aws_iam_role.dev_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["iam:PassRole", "lambda:CreateFunction"]
      Resource = "*"
    }]
  })
}

# 🔟 Wildcard policy on role
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

# 🔟 Admin role policy attachment
resource "aws_iam_role_policy_attachment" "admin_full" {
  role       = aws_iam_role.admin_role.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

resource "aws_iam_role_policy_attachment" "admin_direct_full" {
  role       = aws_iam_role.admin_role_direct.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

# 🔟 Security groups
resource "aws_security_group" "ssh_open" {
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

resource "aws_security_group" "web_open" {
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

resource "aws_security_group" "all_egress" {
  name        = "all-egress"
  description = "Allow all outbound"
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 🔟 DynamoDB table without encryption
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

# 🔟 Basic KMS key (default policy)
resource "aws_kms_key" "basic_key" {
  description = "Basic KMS key"
  enable_key_rotation = false
}

# 🔟 Lambda function (uses dummy.zip present in infra/)
resource "aws_lambda_function" "admin_func" {
  function_name = "admin-func"
  role          = aws_iam_role.admin_role.arn
  runtime       = "python3.9"
  handler       = "lambda_handler.handler"
  filename      = "dummy.zip"
  source_code_hash = filebase64sha256("dummy.zip")
}

# 🔟 S3 bucket policy wildcard
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

# 🔟 S3 bucket versioning suspended
resource "aws_s3_bucket_versioning" "no_versioning" {
  bucket = aws_s3_bucket.public_bucket.id
  versioning_configuration {
    status = "Suspended"
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
      type = "S3_BUCKET_WILDCARD_POLICY"
      resource_id = aws_s3_bucket_policy.wildcard_policy.id
      expected_severity = "HIGH"
    },
    {
      id = "MC-003"
      type = "S3_VERSIONING_DISABLED"
      resource_id = aws_s3_bucket_versioning.no_versioning.bucket
      expected_severity = "MEDIUM"
    },
    {
      id = "MC-004"
      type = "IAM_ROLE_ASSUMABLE_BY_ANYONE"
      resource_id = aws_iam_role.dev_role.arn
      expected_severity = "HIGH"
    },
    {
      id = "MC-005"
      type = "IAM_ROLE_PASSROLE_LAMBDA_CREATE"
      resource_id = aws_iam_role.dev_role.arn
      expected_severity = "HIGH"
    },
    {
      id = "MC-006"
      type = "IAM_ROLE_ADMIN_FULL"
      resource_id = aws_iam_role.admin_role.arn
      expected_severity = "CRITICAL"
    },
    {
      id = "MC-007"
      type = "IAM_ROLE_ADMIN_DIRECT"
      resource_id = aws_iam_role.admin_role_direct.arn
      expected_severity = "CRITICAL"
    },
    {
      id = "MC-008"
      type = "IAM_ROLE_WILDCARD_POLICY"
      resource_id = aws_iam_role_policy.wildcard_policy_role.id
      expected_severity = "CRITICAL"
    },
    {
      id = "MC-009"
      type = "IAM_ROLE_WILDCARD_ASSUMABLE"
      resource_id = aws_iam_role.wildcard_role.arn
      expected_severity = "HIGH"
    },
    {
      id = "MC-010"
      type = "IAM_USER_NO_MFA"
      resource_id = aws_iam_user.no_mfa_user.arn
      expected_severity = "HIGH"
    },
    {
      id = "MC-011"
      type = "IAM_USER_ACCESS_KEY_NO_MFA"
      resource_id = aws_iam_access_key.no_mfa_key.id
      expected_severity = "HIGH"
    },
    {
      id = "MC-012"
      type = "IAM_USER_POLICY_WILDCARD"
      resource_id = aws_iam_user_policy.no_mfa_full.id
      expected_severity = "CRITICAL"
    },
    {
      id = "MC-013"
      type = "SG_SSH_OPEN_WORLD"
      resource_id = aws_security_group.ssh_open.id
      expected_severity = "HIGH"
    },
    {
      id = "MC-014"
      type = "SG_WEB_OPEN_WORLD"
      resource_id = aws_security_group.web_open.id
      expected_severity = "MEDIUM"
    },
    {
      id = "MC-015"
      type = "SG_ALL_EGRESS"
      resource_id = aws_security_group.all_egress.id
      expected_severity = "LOW"
    },
    {
      id = "MC-016"
      type = "DYNAMODB_NO_ENCRYPTION"
      resource_id = aws_dynamodb_table.ddb_no_enc.arn
      expected_severity = "HIGH"
    },
    {
      id = "MC-017"
      type = "KMS_KEY_ROTATION_DISABLED"
      resource_id = aws_kms_key.basic_key.arn
      expected_severity = "MEDIUM"
    },
    {
      id = "MC-018"
      type = "LAMBDA_RUNS_AS_ADMIN"
      resource_id = aws_lambda_function.admin_func.arn
      expected_severity = "CRITICAL"
    },
    {
      id = "MC-019"
      type = "S3_BUCKET_WILDCARD_POLICY"
      resource_id = aws_s3_bucket_policy.wildcard_policy.id
      expected_severity = "HIGH"
    },
    {
      id = "MC-020"
      type = "S3_VERSIONING_DISABLED"
      resource_id = aws_s3_bucket_versioning.no_versioning.bucket
      expected_severity = "MEDIUM"
    }
  ])
  description = "Catalog of deliberately seeded misconfigurations (~20)"
}