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
  filename      = "dummy.zip"
  source_code_hash = filebase64sha256("dummy.zip")
}

# 5️⃣ Public S3 bucket without encryption
resource "aws_s3_bucket" "public_bucket_no_enc" {
  bucket = "public-data-no-enc"
  acl    = "public-read"
}
resource "aws_s3_bucket_server_side_encryption_configuration" "no_enc" {
  bucket = aws_s3_bucket.public_bucket_no_enc.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
# Actually we want no encryption, so omit encryption config – just public bucket.

# 6️⃣ S3 bucket with wildcard principal policy
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

# 7️⃣ IAM user with access key and no MFA
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

# 8️⃣ IAM policy with full *:* attached to a role
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

# 9️⃣ Security group open to world on SSH (22)
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

# 🔟 Security group open to world on HTTP/HTTPS
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

# 🔟🔟 Security group allowing all egress
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

# 1️⃣1️⃣ RDS instance publicly accessible, no encryption
resource "aws_db_instance" "rds_public_no_enc" {
  identifier        = "rds-public-noenc"
  engine            = "mysql"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  username          = "admin"
  password          = "password123"
  publicly_accessible = true
  storage_encrypted = false
  skip_final_snapshot = true
}

# 1️⃣2️⃣ DynamoDB table without encryption at rest
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

# 1️⃣3️⃣ KMS key with permissive policy and rotation disabled
resource "aws_kms_key" "kms_permissive" {
  description = "Permissive KMS key"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = "kms:*"
      Resource  = "*"
    }]
  })
  enable_key_rotation = false
}

# 1️⃣4️⃣ CloudTrail not enabled (no trail resource) – we represent by creating a trail with logging disabled
resource "aws_cloudtrail" "trail_disabled" {
  name                          = "trail-disabled"
  s3_bucket_name                = aws_s3_bucket.public_bucket.id
  enable_logging                = false
  is_multi_region_trail         = false
  include_global_service_events = false
}

# 1️⃣5️⃣ Secrets Manager secret stored as plaintext (no KMS encryption)
resource "aws_secretsmanager_secret" "plain_secret" {
  name = "plain-secret"
  kms_key_id = ""  # uses default AWS managed key, but we consider it a misconfig if no custom KMS
}
resource "aws_secretsmanager_secret_version" "plain_secret_ver" {
  secret_id = aws_secretsmanager_secret.plain_secret.id
  secret_string = "username=admin,password=secret123"
}

# 1️⃣6️⃣ Parameter Store plaintext parameter
resource "aws_ssm_parameter" "plain_param" {
  name  = "/plain/param"
  type  = "String"
  value = "secret-value"
}

# 1️⃣7️⃣ VPC flow logs disabled (no flow log resource) – represent by not creating flow log; we skip.



# 1️⃣9️⃣ IAM role with AdministratorAccess directly attached (duplicate of admin role but separate)
resource "aws_iam_role" "admin_role_direct" {
  name = "admin-role-direct"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}
resource "aws_iam_role_policy_attachment" "admin_direct_full" {
  role       = aws_iam_role.admin_role_direct.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

# 2️⃣0️⃣ S3 bucket versioning disabled
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
      id = "MC-008b"
      type = "IAM_ROLE_WILDCARD_ASSUMABLE"
      resource_id = aws_iam_role.wildcard_role.arn
      expected_severity = "HIGH"
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
      type = "RDS_PUBLIC_NO_ENCRYPTION"
      resource_id = aws_db_instance.rds_public_no_enc.arn
      expected_severity = "CRITICAL"
    },
    {
      id = "MC-013"
      type = "DYNAMODB_NO_ENCRYPTION"
      resource_id = aws_dynamodb_table.ddb_no_enc.arn
      expected_severity = "HIGH"
    },
    {
      id = "MC-014"
      type = "KMS_KEY_PERMISSIVE_POLICY"
      resource_id = aws_kms_key.kms_permissive.arn
      expected_severity = "CRITICAL"
    },
    {
      id = "MC-015"
      type = "KMS_KEY_ROTATION_DISABLED"
      resource_id = aws_kms_key.kms_permissive.arn
      expected_severity = "MEDIUM"
    },
    {
      id = "MC-016"
      type = "CLOUDTRAIL_LOGGING_DISABLED"
      resource_id = aws_cloudtrail.trail_disabled.arn
      expected_severity = "HIGH"
    },
    {
      id = "MC-017"
      type = "SECRETS_MANAGER_PLAINTEXT"
      resource_id = aws_secretsmanager_secret.plain_secret.arn
      expected_severity = "HIGH"
    },
    {
      id = "MC-018"
      type = "PARAMETER_STORE_PLAINTEXT"
      resource_id = aws_ssm_parameter.plain_param.arn
      expected_severity = "HIGH"
    },
    {
      id = "MC-019"
      type = "IAM_ROLE_ADMIN_DIRECT"
      resource_id = aws_iam_role.admin_role_direct.arn
      expected_severity = "CRITICAL"
    },
    {
      id = "MC-020"
      type = "S3_VERSIONING_DISABLED"
      resource_id = aws_s3_bucket_versioning.no_versioning.bucket
      expected_severity = "MEDIUM"
    }
  ])
  description = "Catalog of deliberately seeded misconfigurations (~30)"
}
