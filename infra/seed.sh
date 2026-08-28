#!/usr/bin/env bash
set -euo pipefail

ENDPOINT_URL=${ENDPOINT_URL:-http://127.0.0.1:4566}
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-test}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-test}
AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}

export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION

echo "=== Creating seed resources in LocalStack ==="

# 1. S3 buckets
echo "Creating S3 buckets..."
aws --endpoint-url="$ENDPOINT_URL" s3api create-bucket --bucket public-data --region "$AWS_DEFAULT_REGION" 2>/dev/null || true
aws --endpoint-url="$ENDPOINT_URL" s3api put-bucket-acl --bucket public-data --acl public-read 2>/dev/null || true

aws --endpoint-url="$ENDPOINT_URL" s3api create-bucket --bucket public-data-no-enc --region "$AWS_DEFAULT_REGION" 2>/dev/null || true
aws --endpoint-url="$ENDPOINT_URL" s3api put-bucket-acl --bucket public-data-no-enc --acl public-read 2>/dev/null || true

# S3 bucket policy with wildcard
aws --endpoint-url="$ENDPOINT_URL" s3api put-bucket-policy --bucket public-data --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::public-data/*"
  }]
}' 2>/dev/null || true

# 2. IAM roles and users
echo "Creating IAM resources..."

# dev-role (assumable by anyone)
aws --endpoint-url="$ENDPOINT_URL" iam create-role --role-name dev-role --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "sts:AssumeRole"
  }]
}' 2>/dev/null || true

aws --endpoint-url="$ENDPOINT_URL" iam put-role-policy --role-name dev-role --policy-name dev-role-policy --policy-document '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["iam:PassRole", "lambda:CreateFunction"],
    "Resource": "*"
  }]
}' 2>/dev/null || true

# admin-role
aws --endpoint-url="$ENDPOINT_URL" iam create-role --role-name admin-role --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}' 2>/dev/null || true

aws --endpoint-url="$ENDPOINT_URL" iam attach-role-policy --role-name admin-role --policy-arn arn:aws:iam::aws:policy/AdministratorAccess 2>/dev/null || true

# wildcard-role
aws --endpoint-url="$ENDPOINT_URL" iam create-role --role-name wildcard-role --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}' 2>/dev/null || true

aws --endpoint-url="$ENDPOINT_URL" iam put-role-policy --role-name wildcard-role --policy-name wildcard-policy --policy-document '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "*",
    "Resource": "*"
  }]
}' 2>/dev/null || true

# no-mfa-user
aws --endpoint-url="$ENDPOINT_URL" iam create-user --user-name no-mfa-user 2>/dev/null || true
aws --endpoint-url="$ENDPOINT_URL" iam create-login-profile --user-name no-mfa-user --password "TempPass123!" --no-password-reset-required 2>/dev/null || true
aws --endpoint-url="$ENDPOINT_URL" iam create-access-key --user-name no-mfa-user 2>/dev/null || true
aws --endpoint-url="$ENDPOINT_URL" iam put-user-policy --user-name no-mfa-user --policy-name full-access --policy-document '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "*",
    "Resource": "*"
  }]
}' 2>/dev/null || true

# 3. Lambda function (needs dummy.zip)
if [ -f "infra/dummy.zip" ]; then
  ADMIN_ROLE_ARN=$(aws --endpoint-url="$ENDPOINT_URL" iam get-role --role-name admin-role --query 'Role.Arn' --output text 2>/dev/null)
  if [ -n "$ADMIN_ROLE_ARN" ]; then
    aws --endpoint-url="$ENDPOINT_URL" lambda create-function \
      --function-name admin-func \
      --runtime python3.9 \
      --role "$ADMIN_ROLE_ARN" \
      --handler index.handler \
      --zip-file fileb://infra/dummy.zip 2>/dev/null || true
  fi
fi

# 4. Security groups
echo "Creating security groups..."
VPC_ID=$(aws --endpoint-url="$ENDPOINT_URL" ec2 describe-vpcs --query 'Vpcs[0].VpcId' --output text 2>/dev/null)
if [ -n "$VPC_ID" ] && [ "$VPC_ID" != "None" ]; then
  aws --endpoint-url="$ENDPOINT_URL" ec2 create-security-group --group-name ssh-open --description "Open SSH to world" --vpc-id "$VPC_ID" 2>/dev/null || true
  aws --endpoint-url="$ENDPOINT_URL" ec2 authorize-security-group-ingress --group-name ssh-open --protocol tcp --port 22 --cidr 0.0.0.0/0 2>/dev/null || true
  aws --endpoint-url="$ENDPOINT_URL" ec2 authorize-security-group-egress --group-name ssh-open --protocol -1 --cidr 0.0.0.0/0 2>/dev/null || true

  aws --endpoint-url="$ENDPOINT_URL" ec2 create-security-group --group-name web-open --description "Open HTTP/HTTPS to world" --vpc-id "$VPC_ID" 2>/dev/null || true
  aws --endpoint-url="$ENDPOINT_URL" ec2 authorize-security-group-ingress --group-name web-open --protocol tcp --port 80 --cidr 0.0.0.0/0 2>/dev/null || true
  aws --endpoint-url="$ENDPOINT_URL" ec2 authorize-security-group-ingress --group-name web-open --protocol tcp --port 443 --cidr 0.0.0.0/0 2>/dev/null || true
  aws --endpoint-url="$ENDPOINT_URL" ec2 authorize-security-group-egress --group-name web-open --protocol -1 --cidr 0.0.0.0/0 2>/dev/null || true

  aws --endpoint-url="$ENDPOINT_URL" ec2 create-security-group --group-name all-egress --description "Allow all outbound" --vpc-id "$VPC_ID" 2>/dev/null || true
  aws --endpoint-url="$ENDPOINT_URL" ec2 authorize-security-group-egress --group-name all-egress --protocol -1 --cidr 0.0.0.0/0 2>/dev/null || true
fi

# 5. DynamoDB table
echo "Creating DynamoDB table..."
aws --endpoint-url="$ENDPOINT_URL" dynamodb create-table \
  --table-name ddb-no-enc \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --no-cli-pager 2>/dev/null || true

# Wait for table to be active
sleep 3

echo "=== Seed complete ==="
# Generate catalog
cat > data/misconfig_catalog.json << 'CATALOG'
[
  {"id": "MC-001", "type": "S3_PUBLIC_READ", "resource_id": "arn:aws:s3:::public-data", "expected_severity": "MEDIUM"},
  {"id": "MC-002", "type": "IAM_ROLE_ASSUMABLE_BY_ANYONE", "resource_id": "arn:aws:iam::000000000000:role/dev-role", "expected_severity": "HIGH"},
  {"id": "MC-003", "type": "IAM_ROLE_PASSROLE_LAMBDA_CREATE", "resource_id": "arn:aws:iam::000000000000:role/dev-role", "expected_severity": "HIGH"},
  {"id": "MC-004", "type": "LAMBDA_RUNS_AS_ADMIN", "resource_id": "arn:aws:lambda:us-east-1:000000000000:function:admin-func", "expected_severity": "CRITICAL"},
  {"id": "MC-005", "type": "S3_BUCKET_WILDCARD_POLICY", "resource_id": "arn:aws:s3:::public-data", "expected_severity": "HIGH"},
  {"id": "MC-006", "type": "IAM_USER_NO_MFA", "resource_id": "arn:aws:iam::000000000000:user/no-mfa-user", "expected_severity": "HIGH"},
  {"id": "MC-007", "type": "IAM_USER_ACCESS_KEY_NO_MFA", "resource_id": "AKIA...", "expected_severity": "HIGH"},
  {"id": "MC-008", "type": "IAM_POLICY_WILDCARD", "resource_id": "arn:aws:iam::000000000000:policy/wildcard-policy", "expected_severity": "CRITICAL"},
  {"id": "MC-009", "type": "SG_SSH_OPEN_WORLD", "resource_id": "sg-xxx", "expected_severity": "HIGH"},
  {"id": "MC-010", "type": "SG_WEB_OPEN_WORLD", "resource_id": "sg-yyy", "expected_severity": "MEDIUM"},
  {"id": "MC-011", "type": "SG_ALL_EGRESS", "resource_id": "sg-zzz", "expected_severity": "LOW"},
  {"id": "MC-012", "type": "DYNAMODB_NO_ENCRYPTION", "resource_id": "arn:aws:dynamodb:us-east-1:000000000000:table/ddb-no-enc", "expected_severity": "HIGH"}
]
CATALOG
echo "Catalog written to data/misconfig_catalog.json"
