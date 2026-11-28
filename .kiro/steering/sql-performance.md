---
inclusion: fileMatch
fileMatchPattern: ["sql/**", "docs/sql-performance-standard.md", "templates/sql-benchmark.md", "evidence/sql/**"]
---
# SQL performance

Optimization is hypothesis testing. Follow `docs/sql-performance-standard.md` and `templates/sql-benchmark.md`.

- No speedup claim without measured baseline and candidate results (median and p95, rows examined and returned, environment and version).
- A rewritten query, an index suggestion or an estimated plan is not evidence of speed.
- Prove logical result equivalence before comparing timings.
- Do not compare Spark and MySQL timings as equivalent.
- MySQL 8.0 is the initial target. Record the observed version only from evidence.
