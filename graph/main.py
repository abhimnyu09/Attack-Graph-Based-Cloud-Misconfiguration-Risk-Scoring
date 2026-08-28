#!/usr/bin/env python3
"""
Real IAM graph builder.
Enumerates IAM principals (roles, users, groups), their trust policies,
and effective permissions (inline + managed + group-inherited).
Builds a NetworkX DiGraph with nodes for principals and Lambda resources,
edges:
  - CAN_ASSUME (trust policy allows sts:AssumeRole)
  - CAN_ESCALATE (principal has permissions that can elevate to another principal)
Writes /data/graph.graphml
"""
import os
import json
import boto3
import networkx as nx
from botocore.config import Config


ENDPOINT_URL = os.getenv("ENDPOINT_URL")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "test")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")


def get_iam_client():
    return boto3.client(
        "iam",
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION,
        config=Config(retries={"max_attempts": 3}),
    )


def get_lambda_client():
    return boto3.client(
        "lambda",
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION,
        config=Config(retries={"max_attempts": 3}),
    )


def parse_policy_doc(doc):
    """Return list of statements (dict) from a policy document."""
    if isinstance(doc, str):
        doc = json.loads(doc)
    stmts = doc.get("Statement", [])
    if isinstance(stmts, dict):
        stmts = [stmts]
    return stmts


def statements_allow_action(statements, action_pattern, resource_pattern="*"):
    """Check if any statement allows action_pattern on resource_pattern."""
    for s in statements:
        if s.get("Effect") != "Allow":
            continue
        actions = s.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]
        resources = s.get("Resource", [])
        if isinstance(resources, str):
            resources = [resources]
        for a in actions:
            if match_pattern(a, action_pattern):
                for r in resources:
                    if match_pattern(r, resource_pattern):
                        return True
    return False


def match_pattern(value, pattern):
    """Simple wildcard match: pattern may contain *."""
    if pattern == "*":
        return True
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    return value == pattern


def get_all_managed_policy_docs(iam, policy_arns):
    """Fetch default version document for each managed policy ARN."""
    docs = []
    for arn in policy_arns:
        try:
            pol = iam.get_policy(PolicyArn=arn)["Policy"]
            ver = iam.get_policy_version(
                PolicyArn=arn, VersionId=pol["DefaultVersionId"]
            )["PolicyVersion"]
            docs.append(ver["Document"])
        except Exception:
            continue
    return docs


def collect_principal_permissions(iam, principal_type, name):
    """Return list of policy documents (inline + managed) for a principal."""
    docs = []
    if principal_type == "role":
        # inline
        paginator = iam.get_paginator("list_role_policies")
        for page in paginator.paginate(RoleName=name):
            for pname in page["PolicyNames"]:
                pol = iam.get_role_policy(RoleName=name, PolicyName=pname)
                docs.append(pol["PolicyDocument"])
        # managed
        attached = iam.list_attached_role_policies(RoleName=name)["AttachedPolicies"]
        arns = [p["PolicyArn"] for p in attached]
        docs.extend(get_all_managed_policy_docs(iam, arns))
    elif principal_type == "user":
        paginator = iam.get_paginator("list_user_policies")
        for page in paginator.paginate(UserName=name):
            for pname in page["PolicyNames"]:
                pol = iam.get_user_policy(UserName=name, PolicyName=pname)
                docs.append(pol["PolicyDocument"])
        attached = iam.list_attached_user_policies(UserName=name)["AttachedPolicies"]
        arns = [p["PolicyArn"] for p in attached]
        docs.extend(get_all_managed_policy_docs(iam, arns))
        # groups
        groups = iam.list_groups_for_user(UserName=name)["Groups"]
        for g in groups:
            gname = g["GroupName"]
            docs.extend(collect_principal_permissions(iam, "group", gname))
    elif principal_type == "group":
        paginator = iam.get_paginator("list_group_policies")
        for page in paginator.paginate(GroupName=name):
            for pname in page["PolicyNames"]:
                pol = iam.get_group_policy(GroupName=name, PolicyName=pname)
                docs.append(pol["PolicyDocument"])
        attached = iam.list_attached_group_policies(GroupName=name)["AttachedPolicies"]
        arns = [p["PolicyArn"] for p in attached]
        docs.extend(get_all_managed_policy_docs(iam, arns))
    return docs


def is_admin_policy(doc):
    """Heuristic: policy grants *:* on *."""
    stmts = parse_policy_doc(doc)
    for s in stmts:
        if s.get("Effect") != "Allow":
            continue
        actions = s.get("Action", [])
        resources = s.get("Resource", [])
        if isinstance(actions, str):
            actions = [actions]
        if isinstance(resources, str):
            resources = [resources]
        if "*" in actions and "*" in resources:
            return True
        # also check for AdministratorAccess managed policy name later
    return False


def main():
    iam = get_iam_client()
    lam = get_lambda_client()

    G = nx.DiGraph()

    # ----- Principals -----
    roles = iam.list_roles()["Roles"]
    users = iam.list_users()["Users"]
    groups = iam.list_groups()["Groups"]

    principal_arns = {}
    # Roles
    for r in roles:
        arn = r["Arn"]
        principal_arns[arn] = {"type": "ROLE", "name": r["RoleName"]}
        G.add_node(arn, node_type="PRINCIPAL", principal_type="ROLE", name=r["RoleName"])
    # Users
    for u in users:
        arn = u["Arn"]
        principal_arns[arn] = {"type": "USER", "name": u["UserName"]}
        G.add_node(arn, node_type="PRINCIPAL", principal_type="USER", name=u["UserName"])
    # Groups
    for g in groups:
        arn = g["Arn"]
        principal_arns[arn] = {"type": "GROUP", "name": g["GroupName"]}
        G.add_node(arn, node_type="PRINCIPAL", principal_type="GROUP", name=g["GroupName"])

    # ----- Trust policies -> CAN_ASSUME edges -----
    for r in roles:
        role_arn = r["Arn"]
        trust_doc = r.get("AssumeRolePolicyDocument")
        if not trust_doc:
            continue
        stmts = parse_policy_doc(trust_doc)
        for s in stmts:
            if s.get("Effect") != "Allow":
                continue
            actions = s.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            if "sts:AssumeRole" not in actions:
                continue
            principals = s.get("Principal", {})
            # Handle Principal = "*" (allow all)
            if principals == "*" or (
                isinstance(principals, dict) and principals.get("AWS") == "*"
            ):
                any_node = "arn:aws:iam::*:*"
                if not G.has_node(any_node):
                    G.add_node(
                        any_node,
                        node_type="PRINCIPAL",
                        principal_type="ANY",
                        name="ANY",
                    )
                G.add_edge(any_node, role_arn, edge_type="CAN_ASSUME", action="sts:AssumeRole")
            else:
                # Principal can be AWS ARN, Service, Federated, etc.
                if "AWS" in principals:
                    aws_prins = principals["AWS"]
                    if isinstance(aws_prins, str):
                        aws_prins = [aws_prins]
                    for p in aws_prins:
                        if p == "*":
                            any_node = "arn:aws:iam::*:*"
                            if not G.has_node(any_node):
                                G.add_node(
                                    any_node,
                                    node_type="PRINCIPAL",
                                    principal_type="ANY",
                                    name="ANY",
                                )
                            G.add_edge(any_node, role_arn, edge_type="CAN_ASSUME", action="sts:AssumeRole")
                        elif p in principal_arns:
                            G.add_edge(p, role_arn, edge_type="CAN_ASSUME", action="sts:AssumeRole")
                if "Service" in principals:
                    svcs = principals["Service"]
                    if isinstance(svcs, str):
                        svcs = [svcs]
                    for svc in svcs:
                        svc_node = f"service:{svc}"
                        if not G.has_node(svc_node):
                            G.add_node(
                                svc_node,
                                node_type="PRINCIPAL",
                                principal_type="SERVICE",
                                name=svc,
                            )
                        G.add_edge(svc_node, role_arn, edge_type="CAN_ASSUME", action="sts:AssumeRole")

    # ----- Determine admin roles -----
    admin_role_arns = set()
    for r in roles:
        arn = r["Arn"]
        # check managed policies for AdministratorAccess
        attached = iam.list_attached_role_policies(RoleName=r["RoleName"])[
            "AttachedPolicies"
        ]
        for p in attached:
            if p["PolicyName"] == "AdministratorAccess":
                admin_role_arns.add(arn)
                break
        # also check inline for *:*
        perms = collect_principal_permissions(iam, "role", r["RoleName"])
        for doc in perms:
            if is_admin_policy(doc):
                admin_role_arns.add(arn)
                break

    # ----- Permissions per principal for escalation detection -----
    principal_perms = {}
    for arn, info in principal_arns.items():
        ptype = info["type"].lower()
        pname = info["name"]
        docs = collect_principal_permissions(iam, ptype, pname)
        principal_perms[arn] = docs

    # Helper to test if principal has permission
    def principal_has(arn, action_pat, resource_pat="*"):
        for doc in principal_perms.get(arn, []):
            if statements_allow_action(parse_policy_doc(doc), action_pat, resource_pat):
                return True
        return False

    # Determine which principals have full *:* permission
    def principal_has_full_access(arn):
        for doc in principal_perms.get(arn, []):
            if is_admin_policy(doc):
                return True
        return False

    # ----- Escalation edges -----
    all_role_arns = [r["Arn"] for r in roles]

    # Principals with full access can escalate to any admin role
    for arn in principal_arns:
        if principal_has_full_access(arn):
            for admin_arn in admin_role_arns:
                if arn != admin_arn:
                    G.add_edge(
                        arn,
                        admin_arn,
                        edge_type="CAN_ESCALATE",
                        action="full-access (*:*)",
                    )

    for arn, info in principal_arns.items():
        # 1. PassRole + Lambda CreateFunction (wildcard)
        if principal_has(arn, "iam:PassRole", "*") and principal_has(
            arn, "lambda:CreateFunction", "*"
        ):
            for target_role in all_role_arns:
                if target_role != arn:
                    G.add_edge(
                        arn,
                        target_role,
                        edge_type="CAN_ESCALATE",
                        action="iam:PassRole+lambda:CreateFunction",
                    )
        # 2. AttachRolePolicy / PutRolePolicy on *
        if principal_has(arn, "iam:AttachRolePolicy", "*") or principal_has(
            arn, "iam:PutRolePolicy", "*"
        ):
            for target_role in all_role_arns:
                if target_role != arn:
                    G.add_edge(
                        arn,
                        target_role,
                        edge_type="CAN_ESCALATE",
                        action="iam:AttachRolePolicy/PutRolePolicy",
                    )
        # 3. CreateAccessKey on user (self or other)
        if principal_has(arn, "iam:CreateAccessKey", "*"):
            for u in users:
                u_arn = u["Arn"]
                if u_arn != arn:
                    G.add_edge(
                        arn,
                        u_arn,
                        edge_type="CAN_ESCALATE",
                        action="iam:CreateAccessKey",
                    )
        # 4. Direct AssumeRole to admin role
        for admin_arn in admin_role_arns:
            if principal_has(arn, "sts:AssumeRole", admin_arn):
                G.add_edge(
                    arn,
                    admin_arn,
                    edge_type="CAN_ESCALATE",
                    action="sts:AssumeRole",
                )

    # ----- Lambda resources -----
    try:
        funcs = lam.list_functions()["Functions"]
        for f in funcs:
            func_arn = f["FunctionArn"]
            role_arn = f.get("Role")
            G.add_node(
                func_arn,
                node_type="RESOURCE",
                resource_type="LAMBDA",
                name=f["FunctionName"],
            )
            if role_arn and role_arn in principal_arns:
                # Lambda acts as its execution role
                G.add_edge(
                    func_arn,
                    role_arn,
                    edge_type="ACTS_AS",
                    action="lambda:InvokeFunction",
                )
    except Exception:
        pass

    # ----- Write output -----
    out_path = "/data/graph.graphml"
    nx.write_graphml(G, out_path)
    print(
        f"[graph] wrote graph with {G.number_of_nodes()} nodes, {G.number_of_edges()} edges to {out_path}"
    )


if __name__ == "__main__":
    main()
