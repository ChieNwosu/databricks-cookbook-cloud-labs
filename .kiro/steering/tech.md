---
inclusion: always
---
# Tech

- Python 3.11, standard library only. No new dependencies, remote scripts or MCP tools without human approval.
- Validators live in `scripts/`, unit tests (unittest) in `tests/`, catalog data in `catalog/*.json`.
- Generated docs (`docs/coverage-ledger.md`, `docs/compatibility-matrix.md`) come from `python scripts/generate_docs.py`. Never edit them by hand.
- Checks to run before committing:
  - `python scripts/generate_docs.py --check`
  - `python scripts/validate_catalog.py` (and `--strict`, which is expected to fail only on the 63 vs 72 coverage gap)
  - `python scripts/lint_notebooks.py`
  - `python scripts/check_policy.py`
  - `python -m unittest discover -s tests -v`
- Targets: Databricks Free Edition (PySpark and Databricks SQL), MySQL 8.0 for the companion track. Record real versions only from evidence.
- No Docker, no paid resources, no workflow dispatch.
