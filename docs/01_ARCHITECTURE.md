# High‑Level Architecture

```
+-------------------+       +--------------------+       +-------------------+
|  Cloud Account    | <---> |  Scanner (Python)  | <---> |  Policy Parser    |
|  (AWS / Azure /   |  API  |  - list resources  |  IAM  |  - build graph    |
|   GCP / LocalStack)          |  - rule engine     |       |    (NetworkX)     |
+-------------------+       +--------------------+       +-------------------+
                                   |                           |
                                   v                           v
                        +------------------------+   +--------------------------+
                        |  Findings (flat list)  |   |  Access/Escalation Graph |
                        +------------------------+   +--------------------------+
                                   |                           |
                                   +------------+----------------+
                                                |
                                                v
                                 +---------------------------+
                                 |  Scoring Engine (Graph)   |
                                 |  - reachability           |
                                 |  - PageRank / betweenness |
                                 |  - shortest‑path length   |
                                 +---------------------------+
                                                |
                                                v
                                 +---------------------------+
                                 |  Dashboard (UI)           |
                                 |  - sortable table         |
                                 |  - interactive graph      |
                                 +---------------------------+
```

**Component responsibilities**

| Component | Input | Output | Docker image |
|-----------|-------|--------|--------------|
| `infra/seed.tf` | – | Cloud resources + `misconfig_catalog.json` | – (run once) |
| `scanner/` | Cloud SDK credentials | `findings.jsonl` | `cspm-scanner` |
| `graph/` | IAM policies (JSON) | `graph.graphml` + `graph_summary.txt` | `cspm-graph` |
| `scoring/` | `findings.jsonl` + `graph.graphml` | `scored_findings.jsonl` | `cspm-scorer` |
| `ui/` | `scored_findings.jsonl` + `graph.graphml` | Web UI (port 8501) | `cspm-ui` |

All containers are wired in **`docker-compose.yml`** so a single `docker‑compose up --build` builds everything and starts the UI.
