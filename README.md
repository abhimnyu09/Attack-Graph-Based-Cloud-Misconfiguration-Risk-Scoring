# Attack‑Graph‑Based Cloud Misconfiguration Risk Scoring

**Course:** Information, Security & Privacy (ISP) – 7th Semester  
**Mentor:** Sezal Rana  
**Team:** 7 members  
**Duration:** 8 weeks (Week 1‑8)  
**Repository:** https://github.com/abhimnyu09/Attack-Graph-Based-Cloud-Misconfiguration-Risk-Scoring  

---

## 🎯 Problem
Traditional CSPM tools output a flat list of misconfigurations. All findings look equally urgent, so analysts waste time on low‑risk items while a short privilege‑escalation chain to admin stays hidden.

**Our solution:** Build a pipeline that not only lists misconfigurations but also **ranks them by real exploitability** using an IAM‑access / privilege‑escalation graph.

---

## 🏗️ Architecture
```
Cloud Account (AWS / LocalStack)
        │
        ▼
Scanner (boto3) ──► Findings (JSONL)
        │
        ▼
Policy Parser (IAM) ──► Access/Escalation Graph (NetworkX)
        │
        ▼
Scoring Engine (reachability, PageRank, hop‑count)
        │
        ▼
Dashboard (Streamlit + streamlit‑agraph)
```

All components are Dockerised; a single `docker compose up --build` brings the whole stack up.

---

## 📦 Deliverables
| # | Artefact | Format |
|---|----------|--------|
| 1 | Seeded test cloud account (~20 misconfigs) | Terraform + `misconfig_catalog.json` |
| 2 | Flat‑rule scanner | Docker image → `findings.jsonl` |
| 3 | IAM access / escalation graph | `graph.graphml` (NetworkX) |
| 4 | Scoring engine (reachability, PageRank, hop‑count) | `scored_findings.jsonl` |
| 5 | Interactive dashboard (Streamlit + `streamlit‑agraph`) | UI at `localhost:8501` |
| 6 | Evaluation report (Precision@k, MAP, statistical test) | `final_report.pdf` + plots |
| 7 | Live demo (10 min) + slide deck | `slides.pdf`, `demo.sh` |
| 8 | Reproducible repo (CI, `docker‑compose up`) | Public GitHub repo |

---

## 📅 Work Plan (8 weeks, 7 people)

| Week | Phase | Owner(s) | Exit Criteria |
|------|-------|----------|---------------|
| 0 | Repo & CI bootstrap | Coordinator | GitHub repo, protected `main`, CI green |
| 1‑2 | Seed cloud account (Terraform) | Cloud‑team (2) | `make seed` creates ~20 resources, `misconfig_catalog.json` |
| 2‑3 | Scanner (real `boto3` enum) | Scanner‑team (2) | `make scan` → `findings.jsonl` |
| 3‑4 | Graph builder (IAM → NetworkX) | Graph‑team (2) | `make graph` → `graph.graphml` |
| 4‑5 | Scoring engine (3 algorithms) | Scoring (1) + Graph | `make score` → `scored_findings.jsonl` |
| 5‑6 | Dashboard (Streamlit + agraph) | UI‑team (2) | `docker compose up` shows UI at `localhost:8501` |
| 6‑7 | Evaluation (Precision@k, MAP, Wilcoxon) | Analyst (1) | `eval/results.csv`, plots, p‑value |
| 7‑8 | Docs, demo rehearsal, final polish | All | `final_report.pdf`, `slides.pdf`, `demo.sh`, tag `v1.0‑eval` |

Critical path ≈ 5 weeks → 3 weeks buffer.

---

## ✅ Current Progress (Friday evaluation)

| Component | Status |
|-----------|--------|
| Documentation (markdown + PDF) | ✅ |
| Repo scaffolding (`docker‑compose.yml`, `Makefile`, `README.md`, CI) | ✅ |
| CI / branch protection (PR‑only, 1 approval, CI gate, linear history) | ✅ |
| Terraform seed (minimal, works on LocalStack 1.4.0) | ✅ |
| Scanner / Graph / Scorer | 🟡 Placeholder (dummy data) |
| UI / Dashboard | ✅ Works with dummy data (Streamlit @ `localhost:8501`) |
| Evaluation & final report | ⏳ Not started |

**What works locally today**

```bash
docker start localstack
export ENDPOINT_URL=http://127.0.0.1:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
make seed          # creates ~18 real resources in LocalStack
make scan && make graph && make score && make ui
# UI → http://localhost:8501  (two‑record dummy dashboard)
```

All CI checks (flake8, pytest, hadolint via Docker, Docker build, smoke test) are green on `main`.

---

## 🚀 Next Steps (Immediate)

1. **Merge seed PR** (`feat/terraform-seed` → `main`).  
2. Create `feat/scanner` branch → implement real `boto3` enumeration in `scanner/main.py`.  
3. Follow PR workflow (CI → review → squash‑merge).  
4. Subsequent tickets: `feat/graph`, `feat/scoring`, UI polish, evaluation, final report.

---

## 🛠️ Tools & Environment

| Tool | Version | Install |
|------|---------|---------|
| Docker Desktop / Docker Engine | 24+ | `brew install --cask docker` |
| Docker Compose v2 | bundled | — |
| Terraform | 1.15+ | `brew tap hashicorp/tap && brew install hashicorp/tap/terraform` |
| Python | 3.11 | `brew install python@3.11` |
| Python packages | `flake8`, `pytest`, `boto3`, `networkx`, `pandas`, `streamlit`, `streamlit-agraph` | `pip install -r <service>/requirements.txt` |
| LocalStack | 1.4.0 (Docker) | `docker run -d --name localstack -p 4566:4566 -p 4571:4571 -e SERVICES=s3,iam,lambda,sts,ec2,kms,dynamodb -e START_WEB=0 localstack/localstack:1.4.0` |
| jq | any | `brew install jq` |
| Git | any | `brew install git` |

All pipeline steps are wrapped in the `Makefile`; a single `make seed && make scan && make graph && make score && make ui` runs the full pipeline once real implementations exist.

---

## 📖 How to Run the Dashboard (Live)

```bash
# 1. Start LocalStack (once)
docker start localstack

# 2. Export env vars (or keep a .env file)
export ENDPOINT_URL=http://127.0.0.1:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

# 3. Build & start the four micro‑services
docker compose up -d

# 4. Run the full pipeline (once real scanner/graph/scorer exist)
make seed && make scan && make graph && make score

# 5. Open the Streamlit UI
make ui          # opens http://localhost:8501
```

The UI shows:
* **Risk‑Ranked Table** – sortable by `risk_score`. Click a row → highlights the exact attack path in the graph.
* **Attack Graph** tab – interactive graph (`streamlit‑agraph`) where nodes are IAM principals / resources and edges are *can‑access* / *can‑escalate* relations.

---

## 📚 Full Project Report
A detailed PDF report (`PROJECT_REPORT.pdf`) is included in the repo root.

---

*Prepared by the ISP team – ready for Friday evaluation.*