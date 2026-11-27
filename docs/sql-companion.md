# SQL companion curriculum

Three implementation tracks share one recipe id space.

| Track | Role |
| --- | --- |
| PySpark | Primary. The book's exercises, adapted to Databricks Free Edition |
| Databricks SQL | Equivalent lakehouse SQL where it makes sense |
| MySQL 8.0 | Relational implementation and query-optimization study where it makes sense |

The book's exercises stay the primary curriculum. Companion work never replaces a learning objective. No recipe SQL exists yet and nothing in this track has been executed.

## Catalog

`catalog/sql_companion.json` links to `catalog/recipes.json` by `recipe_id`. Recipe ids are unchanged.

Per recipe, per track (`databricks_sql`, `mysql`):

| Field | Meaning |
| --- | --- |
| `applicability` | `planned`, `applicable`, `not_applicable` or `unresolved`. A human decides. `planned` is used only after a human decision |
| `execution_status` | `not_started`, `drafted`, `executed_unreviewed`, `verified`. Independent of applicability |
| `artifact_path` | Planned script path under `sql/<track>/chapter-NN/`. Null unless applicable or planned |
| `rationale` | Required for `not_applicable`. Names the concept, not an invented fact |
| `evidence`, `reviewed_by` | Same rules as the main catalog |
| `target_version`, `observed_version`, `semantic_notes` | MySQL only. Target is `8.0`. Observed stays null until evidence from `SELECT VERSION()` exists |

Rules enforced by `validate_catalog.py`: ids exist, enums valid, every recipe has an entry, `not_applicable` has a rationale, `not_applicable` and `unresolved` stay `not_started`, `executed_unreviewed` and `verified` need existing evidence under `evidence/`, `observed_version` needs evidence.

Seeding: every recipe is `unresolved`, except entries where the concept itself clearly has no counterpart (for example streaming, Delta maintenance, Spark execution, Unity Catalog, DLT, tooling). Those are `not_applicable` with a rationale. Both lists are a starting point for the human to change. The 6 vs 9 gap in `coverage_gaps.json` (six unconfirmed ids named, nine unaccounted) is unrelated and is left as is.

MySQL 8.0 is the initial target because GitHub-hosted Ubuntu 24.04 runners currently provide it. The actual version must be recorded from a real run.

## Semantic differences

| Area | Databricks | MySQL |
| --- | --- | --- |
| Delta Lake | ACID transactions on files, time travel, `OPTIMIZE`, `VACUUM` | InnoDB transactions with MVCC. No queryable table history, no file compaction |
| Streaming | Structured Streaming, checkpoints, triggers, watermarks | No equivalent. Polling or triggers are a different model |
| Execution | Distributed lazy plans, shuffles, adaptive execution | Single-node optimizer, indexes, buffer pool |
| Governance | Unity Catalog metastore, lineage, volumes | `GRANT`, roles, schemas. No lineage |

Do not treat a MySQL result as proof about Spark behavior, or the reverse.

## Planned layout

```
sql/databricks/chapter-NN/   Databricks SQL scripts
sql/mysql/chapter-NN/        MySQL scripts
sql/fixtures/                deterministic generated fixtures and seeds, no real data, size capped
sql/tests/                   correctness tests comparing result sets
evidence/sql/                sanitized plans and benchmark records
```

Only placeholder READMEs exist. Benchmarks follow [sql-performance-standard.md](sql-performance-standard.md). The execution design is in [mysql-cloud-execution.md](mysql-cloud-execution.md).
