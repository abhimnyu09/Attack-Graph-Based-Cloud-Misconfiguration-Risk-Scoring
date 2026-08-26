# Project Overview – Attack‑Graph‑Based Cloud Misconfiguration Risk Scoring

**Goal**  
Build a **cloud‑security scanner** that not only lists misconfigurations but also **ranks them by real exploitability** using an IAM‑access / privilege‑escalation graph.

**Why it matters**  
* Traditional CSPM tools emit a flat list (public bucket, over‑permissive role, open SG…).
* Security teams drown in alerts and often fix low‑risk items while a short privilege‑escalation chain to admin stays unnoticed.
* A graph shows *paths* an attacker can walk; the shorter / more central the path, the higher the true risk.

**Core Deliverables (end of semester)**  

| # | Artefact | Format |
|---|----------|--------|
| 1 | Seeded test cloud account (≈30 known bad settings) | Terraform / Pulumi + `misconfig_catalog.json` |
| 2 | Flat‑rule scanner (resource → finding) | Docker image, `findings.jsonl` |
| 3 | IAM access / escalation graph (nodes + “can‑access / can‑escalate” edges) | `graph.graphml` + `graph_summary.txt` |
| 4 | Scoring engine (reachability, PageRank, hop‑count) | `scored_findings.jsonl` (adds `risk_score`, `attack_path`) |
| 5 | Interactive dashboard (table + clickable attack‑path graph) | Streamlit / React container, reachable at `localhost:8501` |
| 6 | Evaluation report (Precision@k, MAP, statistical test) | `eval/results.csv`, `eval/figures/*.png`, `final_report.pdf` |
| 7 | 10‑min live demo + 10‑slide deck | `slides.pdf`, `demo.sh` |
| 8 | Public GitHub repo with CI, `docker‑compose up` reproducible run | `github.com/<org>/attack-graph-cspm` |

**Success metric for the mentor (Friday evaluation)**  
*One‑click pipeline runs, dashboard shows at least one real admin‑escalation path, and a side‑by‑side table proves the graph ranking moves that path from #12 (flat) to #2 (graph).*
