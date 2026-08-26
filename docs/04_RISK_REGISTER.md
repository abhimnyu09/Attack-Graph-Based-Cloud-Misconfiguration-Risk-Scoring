# Risk Register & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R1 | Cloud‑provider API changes / rate limits | Low | Medium | Pin SDK versions in `requirements.txt`; use LocalStack for CI runs. |
| R2 | Incomplete IAM‑edge modelling (missing escalation actions) | Medium | High | Start from the **AWS IAM Privilege‑Escalation** open‑source list (≈ 30 known patterns). Add unit‑tests for each pattern. |
| R3 | Graph size explosion on real accounts | Low (test‑bed is tiny) | Low | Seed ≤ 200 nodes; algorithms are O(V+E) – trivial for this size. |
| R4 | Dashboard performance with > 1k nodes | Low | Low | Use `cytoscape.js` with `cose` layout; lazy‑load sub‑graphs on click. |
| R5 | Team coordination overhead (7 people) | High | Medium | Weekly 30‑min stand‑up, GitHub Projects board, `CODEOWNERS` for each folder. |
| R6 | Mentor expects “novel” scoring method | Low | Medium | Implement **three** scoring modes (reachability, PageRank, hop‑count) and a **hybrid weighted sum**; discuss trade‑offs in report. |
| R7 | No access to a real AWS account (budget / policy) | Medium | High | Fallback to **LocalStack** (full IAM API parity) for all development & CI; only one demo run needs a real free‑tier account. |
| R8 | Docker multi‑arch build failures (ARM vs x86) | Low | Medium | Build only x86 images for demo; document ARM build steps for future work. |

**Review cadence** – revisit this register at every stand‑up; move items to “Closed” once mitigation is verified.
