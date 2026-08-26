#!/usr/bin/env python3
"""
Placeholder graph builder – replace with real IAM parsing.
Reads findings.jsonl (unused) and writes a tiny graph.graphml
"""
import sys, pathlib, networkx as nx

def main():
    out_path = pathlib.Path("/data/graph.graphml")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    G = nx.DiGraph()
    # dummy nodes/edges
    G.add_node("arn:aws:iam::123456789012:role/dev-role", node_type="ROLE")
    G.add_node("arn:aws:iam::123456789012:role/admin-role", node_type="ROLE")
    G.add_edge("arn:aws:iam::123456789012:role/dev-role",
               "arn:aws:iam::123456789012:role/admin-role",
               edge_type="CAN_ESCALATE", action="iam:PassRole")
    nx.write_graphml(G, out_path)
    print(f"[graph] wrote graph with {G.number_of_nodes()} nodes, {G.number_of_edges()} edges to {out_path}")

if __name__ == "__main__":
    main()
