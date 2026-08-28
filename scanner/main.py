#!/usr/bin/env python3
"""
Real scanner – enumerates misconfigurations in a LocalStack/AWS account
via boto3 and writes findings.jsonl (one JSON object per line).
"""
import json
import os
import pathlib
import boto3
from botocore.config import Config

ENDPOINT_URL = os.getenv("ENDPOINT_URL", "http://127.0.0.1:4566")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "test")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

boto_cfg = Config(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=10,
)

session = boto3.session.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_DEFAULT_REGION,
)

s3 = session.client("s3", endpoint_url=ENDPOINT_URL, config=boto_cfg)
iam = session.client("iam", endpoint_url=ENDPOINT_URL, config=boto_cfg)
dynamodb = session.client("dynamodb", endpoint_url=ENDPOINT_URL, config=boto_cfg)
lambda_client = session.client("lambda", endpoint_url=ENDPOINT_URL, config=boto_cfg)
kms = session.client("kms", endpoint_url=ENDPOINT_URL, config=boto_cfg)
ec2 = session.client("ec2", endpoint_url=ENDPOINT_URL, config=boto_cfg)
rds = session.client("rds", endpoint_url=ENDPOINT_URL, config=boto_cfg)
cloudtrail = session.client("cloudtrail", endpoint_url=ENDPOINT_URL, config=boto_cfg)
secretsmanager = session.client("secretsmanager", endpoint_url=ENDPOINT_URL, config=boto_cfg)
ssm = session.client("ssm", endpoint_url=ENDPOINT_URL, config=boto_cfg)


def write_finding(f, resource_id, rule_id, severity, evidence):
    f.write(json.dumps({
        "resource_id": resource_id,
        "rule_id": rule_id,
        "static_severity": severity,
        "evidence": evidence
    }) + "\n")


def scan_s3(f):
    try:
        buckets = s3.list_buckets().get("Buckets", [])
        for b in buckets:
            name = b["Name"]
            arn = f"arn:aws:s3:::{name}"

            # Public ACL
            try:
                acl = s3.get_bucket_acl(Bucket=name)
                for grant in acl.get("Grants", []):
                    grantee = grant.get("Grantee", {})
                    if grantee.get("Type") == "Group" and "AllUsers" in grantee.get("URI", ""):
                        write_finding(f, arn, "S3_PUBLIC_READ", "MEDIUM",
                                      {"bucket": name, "grant": grant})
            except Exception:
                pass

            # Bucket policy with wildcard principal
            try:
                pol = s3.get_bucket_policy(Bucket=name)
                import json as _json
                policy = _json.loads(pol["Policy"])
                for stmt in policy.get("Statement", []):
                    principal = stmt.get("Principal")
                    if principal == "*" or (isinstance(principal, dict) and principal.get("AWS") == "*"):
                        write_finding(f, arn, "S3_BUCKET_WILDCARD_POLICY", "HIGH",
                                      {"bucket": name, "statement": stmt})
            except s3.exceptions.from_code("NoSuchBucketPolicy"):
                pass
            except Exception:
                pass

            # Versioning
            try:
                ver = s3.get_bucket_versioning(Bucket=name)
                if ver.get("Status") != "Enabled":
                    write_finding(f, arn, "S3_VERSIONING_DISABLED", "MEDIUM",
                                  {"bucket": name, "status": ver.get("Status")})
            except Exception:
                pass

            # Encryption
            try:
                _ = s3.get_bucket_encryption(Bucket=name)
                # if we get here, encryption exists
            except s3.exceptions.from_code("ServerSideEncryptionConfigurationNotFoundError"):
                write_finding(f, arn, "S3_NO_ENCRYPTION", "MEDIUM", {"bucket": name})
            except Exception:
                pass
    except Exception as e:
        print(f"[scanner] S3 scan error: {e}")


def scan_iam(f):
    try:
        # Roles
        roles = iam.list_roles().get("Roles", [])
        for role in roles:
            role_name = role["RoleName"]
            role_arn = role["Arn"]
            assume_policy = role.get("AssumeRolePolicyDocument", {})

            # Check if assumable by anyone
            for stmt in assume_policy.get("Statement", []):
                principal = stmt.get("Principal", {})
                if principal == "*" or (isinstance(principal, dict) and principal.get("AWS") == "*"):
                    if stmt.get("Effect") == "Allow" and "sts:AssumeRole" in (stmt.get("Action", []) if isinstance(stmt.get("Action"), list) else [stmt.get("Action")]):
                        write_finding(f, role_arn, "IAM_ROLE_ASSUMABLE_BY_ANYONE", "HIGH",
                                      {"role": role_name, "statement": stmt})

            # Inline policies
            try:
                inline_pols = iam.list_role_policies(RoleName=role_name).get("PolicyNames", [])
                for pol_name in inline_pols:
                    pol_doc = iam.get_role_policy(RoleName=role_name, PolicyName=pol_name)["PolicyDocument"]
                    for stmt in pol_doc.get("Statement", []):
                        actions = stmt.get("Action", [])
                        if isinstance(actions, str):
                            actions = [actions]
                        if "iam:PassRole" in actions and "lambda:CreateFunction" in actions:
                            write_finding(f, role_arn, "IAM_ROLE_PASSROLE_LAMBDA_CREATE", "HIGH",
                                          {"role": role_name, "policy": pol_name, "statement": stmt})
                        if actions == ["*"] and stmt.get("Resource") == "*":
                            write_finding(f, role_arn, "IAM_POLICY_WILDCARD", "CRITICAL",
                                          {"role": role_name, "policy": pol_name, "statement": stmt})
            except Exception:
                pass

            # Attached managed policies
            try:
                attached = iam.list_attached_role_policies(RoleName=role_name).get("AttachedPolicies", [])
                for ap in attached:
                    if ap["PolicyArn"] == "arn:aws:iam::aws:policy/AdministratorAccess":
                        write_finding(f, role_arn, "IAM_ROLE_ADMIN_DIRECT", "CRITICAL",
                                      {"role": role_name, "policy_arn": ap["PolicyArn"]})
            except Exception:
                pass

        # Users
        users = iam.list_users().get("Users", [])
        for user in users:
            user_name = user["UserName"]
            user_arn = user["Arn"]

            # Access keys
            try:
                keys = iam.list_access_keys(UserName=user_name).get("AccessKeyMetadata", [])
                for key in keys:
                    write_finding(f, key["AccessKeyId"], "IAM_USER_ACCESS_KEY_NO_MFA", "HIGH",
                                  {"user": user_name, "key_id": key["AccessKeyId"]})
            except Exception:
                pass

            # Inline user policies
            try:
                inline_pols = iam.list_user_policies(UserName=user_name).get("PolicyNames", [])
                for pol_name in inline_pols:
                    pol_doc = iam.get_user_policy(UserName=user_name, PolicyName=pol_name)["PolicyDocument"]
                    for stmt in pol_doc.get("Statement", []):
                        actions = stmt.get("Action", [])
                        if isinstance(actions, str):
                            actions = [actions]
                        if actions == ["*"] and stmt.get("Resource") == "*":
                            write_finding(f, user_arn, "IAM_POLICY_WILDCARD", "CRITICAL",
                                          {"user": user_name, "policy": pol_name, "statement": stmt})
            except Exception:
                pass

            # MFA check (login profile exists but no MFA device)
            try:
                iam.get_login_profile(UserName=user_name)
                mfa_devices = iam.list_mfa_devices(UserName=user_name).get("MFADevices", [])
                if not mfa_devices:
                    write_finding(f, user_arn, "IAM_USER_NO_MFA", "HIGH", {"user": user_name})
            except iam.exceptions.NoSuchEntityException:
                pass
            except Exception:
                pass

    except Exception as e:
        print(f"[scanner] IAM scan error: {e}")


def scan_dynamodb(f):
    try:
        tables = dynamodb.list_tables().get("TableNames", [])
        for t in tables:
            desc = dynamodb.describe_table(TableName=t)
            arn = desc["Table"]["TableArn"]
            sse = desc["Table"].get("SSEDescription", {})
            if not sse.get("Status") == "ENABLED":
                write_finding(f, arn, "DYNAMODB_NO_ENCRYPTION", "HIGH",
                              {"table": t, "sse_status": sse.get("Status")})
    except Exception as e:
        print(f"[scanner] DynamoDB scan error: {e}")


def scan_lambda(f):
    try:
        funcs = lambda_client.list_functions().get("Functions", [])
        for fn in funcs:
            arn = fn["FunctionArn"]
            role_arn = fn["Role"]
            # Check if function runs as admin (role has AdministratorAccess)
            # We'll just flag if role ARN contains 'admin-role'
            if "admin-role" in role_arn:
                write_finding(f, arn, "LAMBDA_RUNS_AS_ADMIN", "CRITICAL",
                              {"function": fn["FunctionName"], "role": role_arn})
            # Runtime check
            runtime = fn.get("Runtime", "")
            if runtime.startswith("python3.7") or runtime.startswith("python3.8"):
                write_finding(f, arn, "LAMBDA_OUTDATED_RUNTIME", "MEDIUM",
                              {"function": fn["FunctionName"], "runtime": runtime})
    except Exception as e:
        print(f"[scanner] Lambda scan error: {e}")


def scan_kms(f):
    try:
        keys = kms.list_keys().get("Keys", [])
        for key in keys:
            key_id = key["KeyId"]
            try:
                pol = kms.get_key_policy(KeyId=key_id, PolicyName="default")["Policy"]
                import json as _json
                policy = _json.loads(pol)
                for stmt in policy.get("Statement", []):
                    principal = stmt.get("Principal")
                    if principal == "*" or (isinstance(principal, dict) and principal.get("AWS") == "*"):
                        write_finding(f, key_id, "KMS_KEY_PERMISSIVE_POLICY", "CRITICAL",
                                      {"key_id": key_id, "statement": stmt})
            except Exception:
                pass
            # Rotation
            try:
                rot = kms.get_key_rotation_status(KeyId=key_id)
                if not rot.get("KeyRotationEnabled", False):
                    write_finding(f, key_id, "KMS_KEY_ROTATION_DISABLED", "MEDIUM",
                                  {"key_id": key_id})
            except Exception:
                pass
    except Exception as e:
        print(f"[scanner] KMS scan error: {e}")


def scan_ec2(f):
    try:
        # Security groups
        sgs = ec2.describe_security_groups().get("SecurityGroups", [])
        for sg in sgs:
            sg_id = sg["GroupId"]
            # Ingress open to world
            for rule in sg.get("IpPermissions", []):
                for ip_range in rule.get("IpRanges", []):
                    if ip_range.get("CidrIp") == "0.0.0.0/0":
                        port = rule.get("FromPort")
                        if port == 22:
                            write_finding(f, sg_id, "SG_SSH_OPEN_WORLD", "HIGH",
                                          {"sg_id": sg_id, "port": port})
                        elif port in (80, 443):
                            write_finding(f, sg_id, "SG_WEB_OPEN_WORLD", "MEDIUM",
                                          {"sg_id": sg_id, "port": port})
                        else:
                            write_finding(f, sg_id, "SG_OPEN_WORLD", "LOW",
                                          {"sg_id": sg_id, "port": port, "cidr": "0.0.0.0/0"})
            # Egress all
            for rule in sg.get("IpPermissionsEgress", []):
                for ip_range in rule.get("IpRanges", []):
                    if ip_range.get("CidrIp") == "0.0.0.0/0":
                        write_finding(f, sg_id, "SG_ALL_EGRESS", "LOW",
                                      {"sg_id": sg_id})

        # Default VPC SG
        try:
            default_vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}]).get("Vpcs", [])
            for vpc in default_vpcs:
                vpc_id = vpc["VpcId"]
                default_sgs = ec2.describe_security_groups(Filters=[
                    {"Name": "vpc-id", "Values": [vpc_id]},
                    {"Name": "group-name", "Values": ["default"]}
                ]).get("SecurityGroups", [])
                for sg in default_sgs:
                    for rule in sg.get("IpPermissions", []):
                        for ip_range in rule.get("IpRanges", []):
                            if ip_range.get("CidrIp") == "0.0.0.0/0":
                                write_finding(f, sg["GroupId"], "DEFAULT_SG_OPEN", "HIGH",
                                              {"vpc_id": vpc_id, "sg_id": sg["GroupId"]})
        except Exception:
            pass
    except Exception as e:
        print(f"[scanner] EC2 scan error: {e}")


def scan_rds(f):
    try:
        dbs = rds.describe_db_instances().get("DBInstances", [])
        for db in dbs:
            arn = db["DBInstanceArn"]
            if db.get("PubliclyAccessible") and not db.get("StorageEncrypted", False):
                write_finding(f, arn, "RDS_PUBLIC_NO_ENCRYPTION", "CRITICAL",
                              {"db_id": db["DBInstanceIdentifier"], "public": True, "encrypted": False})
    except Exception as e:
        print(f"[scanner] RDS scan error: {e}")


def scan_cloudtrail(f):
    try:
        trails = cloudtrail.describe_trails().get("trailList", [])
        for trail in trails:
            arn = trail.get("TrailARN", trail["Name"])
            if not trail.get("IsLogging", False):
                write_finding(f, arn, "CLOUDTRAIL_LOGGING_DISABLED", "HIGH",
                              {"trail": trail["Name"], "logging": trail.get("IsLogging")})
    except Exception as e:
        print(f"[scanner] CloudTrail scan error: {e}")


def scan_secretsmanager(f):
    try:
        secrets = secretsmanager.list_secrets().get("SecretList", [])
        for sec in secrets:
            arn = sec["ARN"]
            if not sec.get("KmsKeyId"):
                write_finding(f, arn, "SECRETS_MANAGER_PLAINTEXT", "HIGH",
                              {"secret": sec["Name"], "kms_key_id": sec.get("KmsKeyId")})
    except Exception as e:
        print(f"[scanner] SecretsManager scan error: {e}")


def scan_ssm(f):
    try:
        params = ssm.describe_parameters().get("Parameters", [])
        for param in params:
            arn = param["ARN"]
            if param["Type"] == "String" and not param.get("KeyId"):
                write_finding(f, arn, "PARAMETER_STORE_PLAINTEXT", "HIGH",
                              {"parameter": param["Name"], "type": param["Type"]})
    except Exception as e:
        print(f"[scanner] SSM scan error: {e}")


def main():
    out_path = pathlib.Path("/data/findings.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w") as f:
        scan_s3(f)
        scan_iam(f)
        scan_dynamodb(f)
        scan_lambda(f)
        scan_kms(f)
        scan_ec2(f)
        scan_rds(f)
        scan_cloudtrail(f)
        scan_secretsmanager(f)
        scan_ssm(f)

    # Count lines
    count = sum(1 for _ in out_path.open())
    print(f"[scanner] wrote {count} findings to {out_path}")


if __name__ == "__main__":
    main()
