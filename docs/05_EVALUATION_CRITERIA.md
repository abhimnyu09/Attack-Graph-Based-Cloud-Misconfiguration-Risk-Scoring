# Evaluation Criteria (what the mentor will grade)

| Category | Weight | What we must show |
|----------|--------|-------------------|
| **Functional completeness** | 30 % | All 4 pipeline stages run end‑to‑end (`make seed scan graph score`). |
| **Graph correctness** | 20 % | Nodes = identities + resources; edges = `CAN_ACCESS` / `CAN_ESCALATE` derived **only** from IAM policy documents (no hard‑coded rules). |
| **Scoring insight** | 20 % | At least **one** real privilege‑escalation chain (≤ 3 hops) receives a **higher risk_score** than any isolated misconfiguration. |
| **Dashboard usability** | 10 % | Sortable table, clickable row → highlighted attack path in interactive graph, toggle “flat‑severity vs. graph‑score”. |
| **Quantitative comparison** | 10 % | Precision@5, Precision@10, MAP for *graph‑rank* vs. *flat‑rank* on the seeded ground‑truth; statistical test (Wilcoxon) with p‑value. |
| **Documentation & reproducibility** | 5 % | `README.md` + `docs/` + `Makefile` + `docker‑compose.yml` allow a fresh clone to reproduce the demo in ≤ 5 min. |
| **Presentation** | 5 % | 10‑slide deck + 5‑min live demo (pipeline run → dashboard → comparison). |

**Pass‑line** – ≥ 70 % total and **no single category < 40 %**.
