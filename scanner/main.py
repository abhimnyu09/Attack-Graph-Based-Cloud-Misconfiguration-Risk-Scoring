#!/usr/bin/env python3
"""
Placeholder scanner – replace with real implementation.
Writes a tiny findings.jsonl to /data/findings.jsonl
"""
import json, sys, pathlib

def main():
    out_path = pathlib.Path("/data/findings.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    dummy = [
        {"resource_id": "arn:aws:s3:::public-data", "rule_id": "S3_PUBLIC_READ", "static_severity": "MEDIUM", "evidence": {}},
        {"resource_id": "arn:aws:iam::123456789012:role/dev-role", "rule_id": "IAM_ROLE_ASSUMABLE_BY_ANYONE", "static_severity": "HIGH", "evidence": {}}
    ]

    with out_path.open("w") as f:
        for row in dummy:
            f.write(json.dumps(row) + "\n")
    print(f"[scanner] wrote {len(dummy)} dummy findings to {out_path}")

if __name__ == "__main__":
    main()
