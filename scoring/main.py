#!/usr/bin/env python3
"""
Placeholder scoring – reads findings.jsonl + graph.graphml,
adds dummy risk_score and attack_path, writes scored_findings.jsonl
"""
import json
import os
import pathlib
import networkx as nx


def main():
    output_dir = os.getenv("OUTPUT_DIR", "data")
    findings_path = pathlib.Path(output_dir) / "findings.jsonl"
    graph_path = pathlib.Path(output_dir) / "graph.graphml"
    out_path = pathlib.Path(output_dir) / "scored_findings.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # load findings
    findings = []
    with findings_path.open() as f:
        for line in f:
            findings.append(json.loads(line))

    # load graph (unused for dummy)
    _ = nx.read_graphml(graph_path)

    # dummy scoring
    for f in findings:
        f["risk_score"] = 0.9 if "dev-role" in f["resource_id"] else 0.1
        f["attack_path"] = [
            "arn:aws:iam::123456789012:role/dev-role",
            "arn:aws:iam::123456789012:role/admin-role"
        ] if f["risk_score"] > 0.5 else []
        f["scoring_method"] = "reachability"

    with out_path.open("w") as f:
        for row in findings:
            f.write(json.dumps(row) + "\n")
    print(f"[scoring] wrote {len(findings)} scored findings to {out_path}")


if __name__ == "__main__":
    main()
