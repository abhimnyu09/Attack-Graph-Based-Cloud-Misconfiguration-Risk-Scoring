# -------------------------------------------------
# Makefile – one‑liners for the whole pipeline
# -------------------------------------------------
.PHONY: help seed scan graph score ui up down logs clean

help:
	@echo "Available targets:"
	@echo "  make up        – build & start all containers (docker compose up -d)"
	@echo "  make down      – stop & remove containers"
	@echo "  make logs      – tail logs of all services"
	@echo "  make seed      – run Terraform to seed misconfigurations (LocalStack by default)"
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
# 1️⃣ Seed cloud account (Terraform)
# -------------------------------------------------
seed:
	@echo ">>> Seeding test account (LocalStack)…"
	@cd infra && terraform init -upgrade && terraform apply -auto-approve
	@echo ">>> Seed complete. Catalog written to data/misconfig_catalog.json"

# -------------------------------------------------
# 2️⃣ Scanner
# -------------------------------------------------
scan:
	@echo ">>> Running scanner…"
	@docker compose exec -T scanner python -m scanner.main \
		--output /data/findings.jsonl
	@echo ">>> findings.jsonl written to data/"

# -------------------------------------------------
# 3️⃣ Graph builder
# -------------------------------------------------
graph:
	@echo ">>> Building IAM access/escalation graph…"
	@docker compose exec -T graph python -m graph.main \
		--input /data/findings.jsonl \
		--output /data/graph.graphml
	@echo ">>> graph.graphml written to data/"

# -------------------------------------------------
# 4️⃣ Scoring engine
# -------------------------------------------------
score:
	@echo ">>> Scoring findings with graph algorithms…"
	@docker compose exec -T scorer python -m scoring.main \
		--findings /data/findings.jsonl \
		--graph /data/graph.graphml \
		--output /data/scored_findings.jsonl
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
