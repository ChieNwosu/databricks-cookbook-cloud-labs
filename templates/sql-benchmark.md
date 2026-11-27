---
benchmark_id: ""
recipe_id: "0.0"
engine: mysql
engine_version: ""
status: not_started
hypothesis_id: ""
dataset_rows: null
sanitized: false
human_reviewer: ""
result_median_ms: null
result_p95_ms: null
result_rows_examined: null
result_rows_returned: null
result_index_size_bytes: null
---

# SQL benchmark record

Status stays `not_started` until a real run produced the results below. Nothing here is a measurement until you fill it from a real run. See `docs/sql-performance-standard.md`.

## Hypothesis

State one falsifiable claim, for example "the candidate examines fewer rows than the baseline for this predicate". Say what result would disprove it.

## Baseline SQL

```sql
-- baseline query
```

## Candidate SQL

```sql
-- candidate query (and any index DDL)
```

## Equivalence check

How the baseline and candidate result sets were compared (row counts, ordered or unordered diff, checksum). Result:

## Dataset

Generator and seed, row counts per table, value distributions, key cardinalities, selectivity of the predicate. Synthetic data only.

## Environment and version

Engine and exact version from `SELECT VERSION()`, runner or host type, relevant settings, buffer pool state.

## EXPLAIN

Sanitized plan output. An estimated plan is not a measurement.

## EXPLAIN ANALYZE

Sanitized actual plan output.

## Methodology

Warm-up runs, repetitions, cache state (cold or warm), run order, timing method, outlier handling.

## Results

| Variant | Median ms | p95 ms | Rows examined | Rows returned | Index size bytes |
| --- | --- | --- | --- | --- | --- |
| baseline | | | | | |
| candidate | | | | | |

## Write overhead

Insert, update and delete cost with and without the candidate index, and the extra storage.

## Conclusion

Limited to the measured data above. Leave empty until results exist.

## Limitations

Dataset scale, single environment, noise, anything not measured.

## Reviewer

Human reviewer and date. Leave empty until reviewed.
