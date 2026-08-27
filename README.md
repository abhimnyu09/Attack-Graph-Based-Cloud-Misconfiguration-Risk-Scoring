# Attack‑Graph‑Based Cloud Misconfiguration Risk Scoring

**Course:** Information, Security & Privacy (ISP) – 7th Semester  
**Mentor:** Sezal Rana  
**Team:** 7 members  
**Duration:** 8 weeks (Week 1‑8)  
**Repository:** https://github.com/abhimnyu09/Attack-Graph-Based-Cloud-Misconfiguration-Risk-Scoring  

---

## 🎯 Problem (plain language)

Cloud‑Security‑Posture‑Management (CSPM) tools today give you a *flat list* of misconfigurations – e.g. “S3 bucket is public”, “IAM role has too many permissions”. Every entry looks equally critical, so security teams spend time fixing low‑risk issues while a **short chain of permissions that leads to full admin access** goes unnoticed.

**What we are building:** a pipeline that (1) discovers misconfigurations, (2) builds a **graph of who can do what** in the cloud (IAM policies → “can‑access / can‑escalate” edges), (3) runs graph algorithms to compute a **risk score** for each finding, and (4) shows the results in an interactive dashboard where you can click a finding and instantly see the exact escalation path that makes it dangerous.

**Concrete example**  
*Finding:* “Role **dev‑role** can be assumed by anyone.”  
*Graph:* `anyone  →(assume)→ dev‑role →(PassRole+CreateFunction)→ admin‑role →(Lambda runs as admin)→ full admin`.  
*Score:* 0.92 (very high) because the path is only three hops. A flat scanner would label this “HIGH” but would not show that it actually leads to full admin.

---

## 🏗️ Architecture Overview
```
┌─────────────────────┐
│ Cloud Account       │   (AWS or LocalStack)
│  (AWS / LocalStack) │
└───────┬─────────────┘
        │  boto3 API calls
        ▼
┌─────────────────────┐      ┌─────────────────────┐
│ Scanner (boto3)     │ ──►  │ Findings (JSONL)    │
│  - enumerate S3,    │      │  resource_id, rule, │
│    IAM, DynamoDB…   │      │  static severity    │
└─────────────────────┘      └─────────────────────┘
        │
        │  IAM policies (JSON)
        ▼
┌─────────────────────┐      ┌─────────────────────┐
│ Policy Parser       │ ──►  │ Access / Escalation │
│  - parse IAM JSON   │      │ Graph (NetworkX)    │
│  - build nodes/edges│      │ nodes = principals, │
└─────────────────────┘      │ resources          │
        │                    │ edges = can‑access /│
        ▼                    │ can‑escalate        │
┌─────────────────────┐
│ Scoring Engine      │
│  - reachability     │
│  - PageRank         │
│  - hop‑count        │
└───────┬─────────────┘
        ▼
┌─────────────────────┐
│ Dashboard (Streamlit│
│ + streamlit‑agraph) │
│  • sortable table   │
│  • clickable graph  │
└─────────────────────┘
```

All components are Dockerised; a single `docker compose up --build` brings the whole stack up.

---

## 📦 Deliverables (what we will hand‑in)

| # | Artefact | Format |
|---|----------|--------|
| 1 | Seeded test cloud account (~20 misconfigs) | Terraform + `misconfig_catalog.json` |
| 2 | Flat‑rule scanner | Docker image → `findings.jsonl` |
| 3 | IAM access / escalation graph | `graph.graphml` (NetworkX) |
| 4 | Scoring engine (reachability, PageRank, hop‑count) | `scored_findings.jsonl` |
| 5 | Interactive dashboard (Streamlit + `streamlit‑agraph`) | UI at `localhost:8501` |
| 6 | Evaluation report (Precision@k, MAP, Wilcoxon) | `final_report.pdf` + plots |
| 5 | Live demo (10 min) + slide deck | `slides.pdf`, `demo.sh` |
| 6 | Reproducible repo (CI, `docker‑compose up`) | Public GitHub repo |

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

## ✅ Current Progress (as of Friday evaluation)

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
# 1. Start LocalStack (v1.4.0) – all services healthy
docker start localstack

# 2. Export env vars for Terraform / scanner
export ENDPOINT_URL=http://127.0.0.1:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

# 3. Run the full dummy pipeline
make seed          # creates ~18 real resources in LocalStack
make scan && make graph && make score && make ui
# UI → http://localhost:8501  (two‑record dummy dashboard)
```

All CI checks (flake8, pytest, hadolint via Docker, Docker build, smoke test) are green on `main`.

---

## 🛠️ Tools & Environment – exact install commands

Run **once** on a fresh macOS (Linux similar, replace `brew` with `apt`/`dnf`).

```bash
# 1. Homebrew (if not present)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Core CLI tools
brew install git jq python@3.11 terraform docker docker-compose

# 3. Docker Desktop (GUI) – required for Docker daemon on macOS
brew install --cask docker
open -a Docker        # start the daemon, wait until the whale icon says “Docker Desktop is running”

# 4. Terraform from HashiCorp tap (official)
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# 5. Python virtual environment (optional but recommended)
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install flake8 pytest boto3 networkx pandas streamlit streamlit-agraph

# 6. LocalStack (v1.4.0 – the last version without license checks)
docker pull localstack/localstack:1.4.0
docker run -d --name localstack \
  -p 4566:4566 -p 4571:4571 \
  -e SERVICES=s3,iam,lambda,sts,ec2,kms,dynamodb \
  -e START_WEB=0 \
  localstack/localstack:1.4.0
```

*All subsequent commands assume the virtual environment is active (`source .venv/bin/activate`).*

---

## 📖 Complete Run‑Book – From Zero to Live Dashboard

> **Run every command in the same terminal window** so the exported variables stay set.

```bash
# -------------------------------------------------
# 0️⃣  Clone the repository (once)
# -------------------------------------------------
git clone https://github.com/abhimnyu09/Attack-Graph-Based-Cloud-Misconfiguration-Risk-Scoring.git
cd Attack-Graph-Based-Cloud-Misconfiguration-Risk-Scoring

# -------------------------------------------------
# 1️⃣  Start LocalStack (run once, keep it alive)
# -------------------------------------------------
docker start localstack   # if you already created the container
#   OR, first time only:
# docker run -d --name localstack \
#   -p 4566:4566 -p 4571:4571 \
#   -e SERVICES=s3,iam,lambda,sts,ec2,kms,dynamodb \
#   -e START_WEB=0 \
#   localstack/localstack:1.4.0

# Wait until every service reports "available"
until curl -s http://127.0.0.1:4566/_localstack/health | jq -e 'all(.services[]; .=="available")' >/dev/null; do
  echo "waiting for LocalStack..."
  sleep 3
done

# -------------------------------------------------
# 2️⃣  Export AWS / LocalStack env vars (keep them for the whole session)
# -------------------------------------------------
export ENDPOINT_URL=http://127.0.0.1:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

# -------------------------------------------------
# 2️⃣ Build & start the four micro‑services (scanner, graph, scorer, UI)
# -------------------------------------------------
docker compose up -d            # builds images on first run
docker compose ps               # all four containers should show “Up”

# -------------------------------------------------
# 3️⃣  Seed the cloud account with ~18 deliberate misconfigurations
# -------------------------------------------------
make seed
# → creates IAM roles, policies, user+keys, security groups, DynamoDB table,
#   KMS key, Lambda function, S3 bucket policy, versioning config, etc.
#   Writes data/misconfig_catalog.json (≈ 18 entries)

# Verify the catalog
cat data/misconfig_catalog.json | jq length   # → 18

# -------------------------------------------------
# 4️⃣  Run the **real** pipeline (once scanner / graph / scorer are implemented)
# -------------------------------------------------
# make scan   # real boto3 enumeration → data/findings.jsonl
# make graph  # builds IAM graph → data/graph.graphml
# make score  # scores findings → data/scored_findings.jsonl

# -------------------------------------------------
# 5️⃣  Launch the Streamlit dashboard
# -------------------------------------------------
make ui          # opens http://localhost:8501 in your default browser
```

**What you will see today (with placeholder code)**  
*Risk‑Ranked Table* – two rows (public S3 bucket, assumable IAM role) with dummy `risk_score`.  
*Attack Graph* tab – a tiny graph `dev‑role → admin‑role`.  
When the real scanner / graph / scorer are finished, the same UI will display **all 18 seeded findings** with accurate risk scores and clickable escalation paths.

---

## 📚 Full Project Report
A detailed PDF (`PROJECT_REPORT.pdf`) lives in the repo root. It contains the same narrative plus evaluation methodology, risk‑scoring formulas, and future work.

---

## 📚 Quick Reference – Make Targets

| Target | What it does |
|--------|--------------|
| `make up` | `docker compose up --build -d` |
| `make down` | `docker compose down -v` |
| `make logs` | `docker compose logs -f` |
| `make seed` | Terraform apply (creates cloud resources) |
| `make scan` | Run scanner → `data/findings.jsonl` |
| `make graph` | Build IAM graph → `data/graph.graphml` |
| `make score` | Score findings → `data/scored_findings.jsonl` |
| `make ui` | Open Streamlit UI (`localhost:8501`) |
| `make clean` | Remove generated `data/*.jsonl`, `*.graphml` |

---

## 👥 Team & Mentor
| Role | Name |
|------|------|
| Mentor | Sezal Rana |
| Team (7) | … (add names) |

---

*Prepared by the ISP team – ready for Friday evaluation.*