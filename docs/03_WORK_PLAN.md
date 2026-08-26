# 8‑Week Work Plan (7‑person team)

| Week | Phase | Primary Owner(s) | Exit Criteria |
|------|-------|------------------|---------------|
| 0 | **Kick‑off & Repo hygiene** | Coordinator (1) | GitHub repo, protected `main`, CI green, empty `docker‑compose up` works |
| 1‑2 | **Seed cloud account** | Cloud‑team (2) | `make seed` creates all 30 misconfigs, `misconfig_catalog.json` committed |
| 2‑3 | **Flat‑rule scanner** | Scanner‑team (2) | `make scan` → `findings.jsonl` (≈30 lines) |
| 3‑4 | **IAM → Graph builder** | Graph‑team (2) | `make graph` → `graph.graphml` (≤ 250 nodes) |
| 4‑5 | **Scoring engine** | Scoring‑person (1) + Graph‑team | `make score` → `scored_findings.jsonl` with three scoring columns |
| 5‑6 | **Dashboard / UI** | UI‑team (2) | `docker‑compose up` shows Streamlit UI at `localhost:8501` |
| 6‑7 | **Evaluation & comparison** | Analyst (1) + all | `eval/results.csv`, Precision@k / MAP plots, statistical test |
| 7‑8 | **Documentation, demo rehearsal, final polish** | All (coordinator assembles) | `final_report.pdf`, `slides.pdf`, `demo.sh`, Git tag `v1.0‑eval` |

**Parallelism notes**

* Weeks 1‑2 (infra) and Weeks 2‑3 (scanner) can run simultaneously – different people.  
* Graph building (Weeks 3‑4) only needs the seeded account, so it can start as soon as the Terraform apply finishes.  
* Scoring and UI can be developed in parallel once the graph format is frozen (Week 4).  
* The critical path is **seed → scanner → graph → scoring → UI** ≈ 5 weeks, leaving 3 weeks for evaluation, report and demo rehearsal.
