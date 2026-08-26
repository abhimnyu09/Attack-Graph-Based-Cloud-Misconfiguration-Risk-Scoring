# Attack‑Graph‑Based Cloud Misconfiguration Risk Scoring  
**Semester Project – ISP (Information Security & Privacy)**  
Mentor: **Sezal Rana** | Team: 7 students | Duration: 8 weeks  

---  

## 1. Problem Statement
Traditional Cloud‑Security‑Posture‑Management (CSPM) tools emit a *flat* list of misconfigurations (public bucket, over‑permissive role, open security group, missing MFA, …).  
All findings look equally urgent, so analysts waste time on low‑risk items while a short **privilege‑escalation chain** to full admin stays hidden.

## 2. Our Solution
Build a **pipeline** that

1. **Seeds** a test cloud account with ~30 known bad settings.  
2. **Scans** the account → flat JSONL findings.  
3. **Parses every IAM policy** → a directed graph (nodes = identities & resources, edges = “can‑access” / “can‑escalate”).  
4. **Scores** each finding with graph algorithms (reachability, PageRank, hop‑count).  
5. **Visualises** the ranked list and the exact attack path in an interactive dashboard.  

The result: a **risk‑ranked** view that tells the security team *“fix this role first because it sits on a 3‑step path to admin”*.

## 3. Core Deliverables
| # | Artefact | Format |
|---|----------|--------|
| 1 | Seeded cloud account + catalog | Terraform + `misconfig_catalog.json` |
| 2 | Flat‑rule scanner | Docker image `cspm-scanner` → `findings.jsonl` |
| 3 | IAM access / escalation graph | `graph.graphml` (NetworkX) |
| 4 | Scoring engine (3 algorithms) | `scored_findings.jsonl` (adds `risk_score`, `attack_path`) |
| 5 | Dashboard (table + clickable graph) | Streamlit container on `localhost:8501` |
| 6 | Evaluation report (Precision@k, MAP, stats) | `eval/results.csv`, plots, `final_report.pdf` |
| 7 | 10‑min live demo + 10‑slide deck | `slides.pdf`, `demo.sh` |
| 8 | Reproducible repo (CI, `docker‑compose up`) | Public GitHub repo |

## 4. Architecture (text diagram)

```
Cloud Account ↔ Scanner ↔ Policy Parser → Graph (NetworkX)
                              ↘︎                ↙︎
                           Findings      Scoring Engine
                              ↘︎                ↙︎
                           Dashboard (Streamlit / React)
```

All components are containerised; a single `docker‑compose up --build` builds everything.

## 5. Data Model (key JSONL schemas)

* **Scanner finding** – `resource_id, rule_id, static_severity, evidence`  
* **Graph node** – `node_id, node_type (USER|ROLE|RESOURCE), metadata`  
* **Graph edge** – `edge_type (CAN_ACCESS|CAN_ESCALATE), action, source_policy`  
* **Scored finding** – scanner fields **+** `risk_score (0‑1), attack_path [node_ids], scoring_method`

## 6. Work Plan (8 weeks, 7 people)

| Week | Phase | Owner(s) | Exit |
|------|-------|----------|------|
| 0 | Repo & CI | Coordinator | CI green |
| 1‑2 | Seed account (Terraform) | Cloud‑team (2) | `make seed` works |
| 2‑3 | Flat scanner | Scanner‑team (2) | `make scan` → findings |
| 3‑4 | Graph builder | Graph‑team (2) | `make graph` → graphml |
| 4‑5 | Scoring engine | Scoring (1) + Graph | `make score` → scored |
| 5‑6 | Dashboard | UI‑team (2) | UI at `localhost:8501` |
| 6‑7 | Evaluation & stats | Analyst (1) | Precision@k, MAP, p‑value |
| 7‑8 | Docs, demo rehearsal, final polish | All | `final_report.pdf`, `slides.pdf`, tag `v1.0-eval` |

Parallel tracks keep the critical path ≈ 5 weeks.

## 7. Risk Register (high‑level)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| IAM‑edge modelling incomplete | Medium | High | Start from public AWS privilege‑escalation list; unit‑test each pattern. |
| No real AWS account | Medium | High | Develop against LocalStack; one free‑tier run for demo. |
| Team coordination | High | Medium | Weekly stand‑up, GitHub Projects, CODEOWNERS. |
| Mentor wants novelty | Low | Medium | Provide three scoring modes + hybrid; discuss trade‑offs. |

## 8. Evaluation Criteria (mentor grading)

| Category | Weight |
|----------|--------|
| Functional completeness | 30 % |
| Graph correctness | 20 % |
| Scoring insight (real chain ranked high) | 20 % |
| Dashboard usability | 10 % |
| Quantitative comparison (Precision@k, MAP, stats) | 10 % |
| Docs & reproducibility | 5 % |
| Presentation | 5 % |

## 9. Friday Demo Flow (5 min)

1. Title & problem (30 s)  
2. One‑click pipeline run (45 s)  
3. Dashboard – sorted table + clickable attack path (90 s)  
4. Flat vs. graph toggle – show re‑ranking (60 s)  
5. Numbers + next steps (60 s)

## 10. How to Generate the PDF (run once)

```bash
# from repo root
cd docs
# concatenate all chapters in order
cat 00_PROJECT_OVERVIEW.md \
    01_ARCHITECTURE.md \
    02_DATA_MODEL.md \
    03_WORK_PLAN.md \
    04_RISK_REGISTER.md \
    05_EVALUATION_CRITERIA.md \
    06_DEMO_SCRIPT.md > PROJECT_SUMMARY.md

# convert to PDF (requires pandoc + a LaTeX engine, e.g. texlive)
pandoc PROJECT_SUMMARY.md -o ../Attack_Graph_CSPM_Project_Summary.pdf \
       --toc --pdf-engine=xelatex -V geometry:margin=1in
```

The resulting **`Attack_Graph_CSPM_Project_Summary.pdf`** is a ~12‑page, professionally formatted document you can share instantly with the whole group.

---  

## 6. Next Immediate Steps (today)

1. `mkdir -p docs infra scanner graph scoring ui eval`  
2. Paste each markdown block above into the matching file under `docs/`.  
3. Commit & push – the repo now has **complete documentation** before any code.  
4. Run the `pandoc` command → hand the PDF to teammates.  

You’re now ready to start coding with a **shared, version‑controlled spec** that everyone can refer to. Good luck! 🚀
