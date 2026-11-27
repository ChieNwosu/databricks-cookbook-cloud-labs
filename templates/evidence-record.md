---
recipe_id: "0.0"
engine: ""
engine_version: ""
evidence_type: static_validation
run_url: ""
screenshot_path: ""
date: ""
databricks_runtime: ""
sanitized: false
human_reviewer: ""
result: ""
---

# Evidence record

`evidence_type` is one of `static_validation`, `unit_test`, `integration_test`, `cloud_execution`, `human_verification`. Only `cloud_execution` and `human_verification` records can support `executed_unreviewed` or `verified`.

Provide either `run_url` or `screenshot_path` for cloud execution. Both must come from a real run. Set `sanitized: true` only after you removed private details.

- Recipe:
- Engine and engine version (for example pyspark on Databricks, or mysql from `SELECT VERSION()`):
- Date (YYYY-MM-DD):
- Databricks runtime version (Databricks runs only):
- Human reviewer:
- Result (pass, fail, partial) and a short factual note:

Do not include secrets, tokens, emails or workspace identifiers that should stay private.
