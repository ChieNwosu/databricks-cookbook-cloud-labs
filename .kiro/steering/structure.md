---
inclusion: always
---
# Structure

- `catalog/` JSON source of truth (recipes, labs, versions, compatibility, coverage gaps, SQL companion).
- `notes/chapter-NN/` evergreen notes, one per recipe, front matter must match the catalog.
- `labs/chapter-NN/` Databricks source-format notebooks. `evidence/` sanitized evidence records.
- `sql/` planned layout for companion scripts (see `docs/sql-companion.md`). `templates/` note, evidence, benchmark and inactive workflow templates.
- `docs/` human docs. `scripts/` validators. `tests/` unit tests.
- Recipe ids such as `1.1` are stable. Never rename or renumber them.
- GitHub workflows live only in `.github/workflows/`. The MySQL workflow exists only as a `.template` file under `templates/`.
