# -------------------------------------------------
# Makefile – one‑liners for the whole pipeline
# -------------------------------------------------
.PHONY: help seed scan graph score ui up down logs clean

help:
	@echo "Available targets:"
	@echo "  make up        – build & start all containers (docker compose up -d)"
	@echo "  make down      – stop & remove containers"
	@echo "  make logs      – tail logs of all services"
	@echo "  make seed      – seed LocalStack with misconfigurations (requires awscli)"
	@echo "  make scan      – run scanner inside its container → data/findings.jsonl"
	@echo "  make graph     – build IAM graph → data/graph.graphml"
	@echo "  make score     – score findings → data/scored_findings.jsonl"
	@echo "  make ui        – open Streamlit dashboard in browser"
	@echo "  make clean     – remove generated data files"

# -------------------------------------------------
up:
	docker compose up --build -d

down:
	docker compose down -v

logs:
	docker compose logs -f

# -------------------------------------------------
# 1️⃣ Seed cloud account (LocalStack) – uses AWS CLI from host
# -------------------------------------------------
seed:
	@echo ">>> Seeding test account (LocalStack)…"
	@export ENDPOINT_URL=http://localhost:4566 && \
	 export AWS_ACCESS_KEY_ID=test && \
	 export AWS_SECRET_ACCESS_KEY=test && \
	 export AWS_DEFAULT_REGION=us-east-1 && \
	 ./infra/seed.sh
	@echo ">>> Seed complete. Catalog written to data/misconfig_catalog.json"

# -------------------------------------------------
# 2️⃣ Scanner
# -------------------------------------------------
scan:
	@echo ">>> Running scanner…"
	@docker compose exec -T scanner python main.py
	@echo ">>> findings.jsonl written to data/"

# -------------------------------------------------
# 3️⃣ Graph builder
# -------------------------------------------------
graph:
	@echo ">>> Building IAM access/escalation graph…"
	@docker compose exec -T graph python main.py
	@echo ">>> graph.graphml written to data/"

# -------------------------------------------------
# 4️⃣ Scoring engine
# -------------------------------------------------
score:
	@echo ">>> Scoring findings with graph algorithms…"
	@docker compose exec -T scorer python main.py
	@echo ">>> scored_findings.jsonl written to data/"

# -------------------------------------------------
# 5️⃣ UI – just opens the browser (macOS `open`, Linux `xdg-open`)
# -------------------------------------------------
ui:
	@echo ">>> Opening Streamlit dashboard…"
	@sleep 2 && (open http://localhost:8501 2>/dev/null || xdg-open http://localhost:8501 2>/dev/null || echo "Open http://localhost:8501 manually")

# -------------------------------------------------
clean:
	rm -rf data/*.jsonl data/*.graphml data/misconfig_catalog.json
