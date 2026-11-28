---
inclusion: always
---
# Output guardrails

- Never describe code as executed unless execution evidence exists. Keep static validation, unit testing, integration testing, cloud execution and human verification distinct.
- `executed_unreviewed` and `verified` need existing evidence. `verified` also needs a named human reviewer, runtime metadata and a date. An agent never sets `verified`.
- Scan changes and evidence for credentials and sensitive identifiers (`scripts/secret_patterns.py`, best effort only) and still review by hand.
- Report failed tests, limitations, assumptions and warnings explicitly.
- Keep reproducibility, source attribution and version information. Write original explanations, not textbook prose.
- Never claim SQL speedups without measurements. See `docs/sql-performance-standard.md`.
- Do not weaken tests, loosen validation or change acceptance criteria to get a pass. The 63 vs 72 coverage gap stays until the human supplies the table of contents.
- No em dashes in written content.
