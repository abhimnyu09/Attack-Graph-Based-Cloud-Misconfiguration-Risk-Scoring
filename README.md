# Attack‑Graph‑Based Cloud Misconfiguration Risk Scoring

**ISP Semester Project** – Mentor: **Sezal Rana**  
Team: 7 students | 8‑week timeline

## Quick start (run the whole pipeline locally)

```bash
# 1️⃣  Clone & enter
git clone <your‑github‑url>
cd attack-graph-cspm

# 2️⃣  Build & start all services (scanner, graph, scorer, UI)
docker compose up --build -d

# 3️⃣  Seed a test cloud account (LocalStack by default, real AWS optional)
make seed

# 4️⃣  Run the scanner → graph → scoring
make scan && make graph && make score

# 5️⃣  Open the dashboard
open http://localhost:8501
```

## Repository layout
```
├─ docs/                 # All project documentation (PDF in repo root)
├─ infra/                # Terraform / Pulumi to seed misconfigurations
├─ scanner/              # Flat‑rule scanner (Python)
├─ graph/                # IAM → NetworkX graph builder
├─ scoring/              # Risk‑scoring engine
├─ ui/                   # Streamlit dashboard
├─ eval/                 # Evaluation notebooks & scripts
├─ docker-compose.yml
├─ Makefile
└─ .github/workflows/ci.yml
```

## Documentation
* **PDF** – `Attack_Graph_CSPM_Project_Summary.pdf` (root)  
* **Markdown chapters** – `docs/00_PROJECT_OVERVIEW.md` … `docs/06_DEMO_SCRIPT.md`

## Branching model
* `main` – protected, only merges via PR + CI pass
* `dev` – integration branch for ongoing work
* Feature branches – `feat/<short‑desc>`

## CI (GitHub Actions)
* Lint (flake8, hadolint)
* Unit tests (`pytest`)
* Docker image build for each service
* Runs on every push/PR

---
*Generated from the project spec – keep this file up‑to‑date as the repo evolves.*
