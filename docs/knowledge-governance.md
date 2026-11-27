# Knowledge governance

Notes in `notes/` are the base of an evergreen, evidence-grounded knowledge base that may later be searched with full-text or semantic retrieval. Nothing for retrieval is built in Phase 0.1: no vector database, embedding pipeline, RAG application or external service.

## Note front matter

| Key | Purpose |
| --- | --- |
| `concept_id` | Stable lowercase id, unique across notes (for example `recipe-1.1`). Never reused or renamed |
| `recipe_id`, `chapter`, `title`, `compatibility`, `status` | Must equal the catalog entry |
| `learning_objective` | Written by the human |
| `implementation_engine`, `engine_version` | `pyspark`, `databricks_sql` or `mysql`, and the observed version (null until evidence) |
| `verification_status` | Mirrors `status` |
| `evidence_links`, `last_verified`, `reviewer` | Evidence and review. Required when `verified` |
| `known_limitations`, `related_concepts`, `revalidation_triggers` | Lists. Triggers are conditions that require revalidation, such as a new runtime version |
| `authorship` | `human`, `agent_generated` or `mixed`. A `verified` note cannot be purely `agent_generated` |
| `human_reflection_present` | True once the human has written reflections |
| `source_ref`, `provenance` | Source attribution. Link upstream, never copy |

Body sections stay consistent (Goal, Concepts in my own words, Prerequisites, Adapted steps, Expected observations, Pitfalls, Evidence, Drift notes) so chunking by heading works later.

## Rules

- Unverified claims are not established facts. A note is retrieval-eligible as fact only when `status` is `verified`. Other notes are drafts and must be labelled so by any consumer.
- Human reflections go only in `## My reflections (human-authored)`. Agents must not edit it. Agent-written text belongs elsewhere in the note and `authorship` says so.
- Write original explanations. Do not paste book prose.
- Evidence records (`templates/evidence-record.md`) state engine, engine version, evidence type (`static_validation`, `unit_test`, `integration_test`, `cloud_execution`, `human_verification`), whether they were sanitized, and the human reviewer.

`validate_catalog.py` checks the keys, enums, the reflections heading and the verified requirements. It cannot judge whether claims are true.
