# Data Model – What flows between the pieces

## 1. Misconfiguration Catalog (source of truth)
```json
{
  "misconfigs": [
    {
      "id": "MC-001",
      "type": "S3_PUBLIC_READ",
      "resource_id": "arn:aws:s3:::public-data",
      "expected_severity": "MEDIUM"
    },
    {
      "id": "MC-007",
      "type": "IAM_ROLE_ASSUMABLE_BY_ANYONE",
      "resource_id": "arn:aws:iam::123456789012:role/dev-role",
      "expected_severity": "HIGH"
    }
    …
  ]
}
```

## 2. Scanner Finding (one line per finding – **JSONL**)
```json
{"resource_id":"arn:aws:s3:::public-data","rule_id":"S3_PUBLIC_READ","static_severity":"MEDIUM","evidence":{"policy":"..."}}
{"resource_id":"arn:aws:iam::123456789012:role/dev-role","rule_id":"IAM_ROLE_ASSUMABLE_BY_ANYONE","static_severity":"HIGH","evidence":{"trust_policy":"..."}}
```

## 3. Graph (NetworkX `DiGraph`, persisted as **GraphML**)
* **Node attributes**  
  - `node_id` (ARN or principal identifier)  
  - `node_type` ∈ {`USER`, `ROLE`, `SERVICE_ACCOUNT`, `RESOURCE`}  
  - `metadata` (e.g., resource name, attached policies)

* **Edge attributes**  
  - `edge_type` ∈ {`CAN_ACCESS`, `CAN_ESCALATE`}  
  - `action` (e.g., `s3:GetObject`, `iam:PassRole`)  
  - `source_policy` (pointer to the policy document that granted it)

## 4. Scored Finding (extends scanner finding)
```json
{
  "resource_id": "arn:aws:iam::123456789012:role/dev-role",
  "rule_id": "IAM_ROLE_ASSUMABLE_BY_ANYONE",
  "static_severity": "HIGH",
  "risk_score": 0.85,
  "attack_path": [
    "arn:aws:iam::123456789012:role/dev-role",
    "arn:aws:iam::123456789012:role/admin-role",
    "arn:aws:lambda:::function:admin-func"
  ],
  "scoring_method": "reachability"
}
```

All files are **line‑delimited JSON** → easy to stream with `jq`, `pandas.read_json(lines=True)`, or load directly in the UI.
