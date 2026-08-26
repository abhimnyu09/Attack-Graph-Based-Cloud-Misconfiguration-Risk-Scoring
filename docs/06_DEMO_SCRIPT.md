# Friday Demo Script (5 minutes)

| Time | Action | What the audience sees |
|------|--------|------------------------|
| 0:00‑0:15 | **Title slide** – project name, team, mentor. | Slide 1 |
| 0:15‑0:45 | **Problem statement** – “Flat CSPM = noise”. | Slide 2 (tiny screenshot of a raw scanner list). |
| 0:45‑1:30 | **One‑click pipeline** – run `make seed && make scan && make graph && make score` (terminal). | Live terminal output (≈ 30 s). |
| 1:30‑3:00 | **Dashboard walk‑through**  <br>1. Open `http://localhost:8501`. <br>2. Show table sorted by **Risk Score**. <br>3. Click the top row (e.g., `dev-role → admin-role`). <br>4. Graph highlights the exact 3‑hop escalation path. | Streamlit UI – table + interactive graph. |
| 3:00‑4:00 | **Side‑by‑side comparison** – toggle “Flat severity” view; point out the same finding drops from #2 → #12. | Same UI, two tabs. |
| 4:00‑4:30 | **Quantitative result** – show one slide with Precision@5 / MAP numbers + p‑value. | Slide 8 (bar chart). |
| 4:30‑5:00 | **Take‑away & next steps** – “Graph‑based ranking surfaces the real admin‑escalation; next: multi‑account, CI gate, auto‑remediation.” | Slide 9‑10. |

**Speaker notes** (copy into presenter view)

* “The scanner is just a rule engine – nothing new.”  
* “The novelty is the **graph** built *solely* from IAM policy documents.”  
* “Scoring is transparent: we show the exact path that gave the score.”  
* “Numbers prove the graph moves the true threat from the middle of the list to the top.”  

**Backup plan** – if UI fails, open `scored_findings.jsonl` with `jq` and print the top‑5 rows; the mentor can still see the ranking.
