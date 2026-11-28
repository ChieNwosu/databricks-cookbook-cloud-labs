# SQL performance standard

Optimization is hypothesis testing. A query rewrite, an index suggestion or an estimated plan is a hypothesis. It becomes a finding only after measurement. No document in this repo may claim a speedup without a completed [benchmark record](../templates/sql-benchmark.md) backed by evidence. No benchmark has been run.

## Method

1. **Baseline versus candidate.** Write both queries, and any DDL the candidate needs. Change one thing at a time.
2. **Logical result equivalence.** Prove both return the same result (same rows, or the same rows after a defined ordering) before comparing time. Record how.
3. **Explicit projections and data types.** Select only needed columns. Use the narrowest appropriate type, and avoid implicit casts that block index use.
4. **Sargable predicates.** Keep the indexed column bare on one side of the comparison. Wrapping it in a function or arithmetic, or comparing mismatched types, usually prevents index range access.
5. **Selectivity and cardinality.** Record row counts, distinct counts and how many rows the predicate keeps. An index on a low-selectivity column may not help.
6. **Indexes.** Compare single-column and composite indexes. For composite indexes, column order matters (equality columns before range columns is a common starting rule, to be tested).
7. **Covering indexes.** Where an index holds every column the query needs, the engine can skip the table lookup. Test it, and count its size.
8. **Join strategies and aggregation.** Record the join order and method the plan uses, whether join columns are indexed, and whether aggregation uses an index or a temporary table.
9. **Transactions and write tradeoffs.** Every added index slows inserts, updates and deletes and takes storage. Measure write cost with and without the candidate.
10. **EXPLAIN and EXPLAIN ANALYZE.** `EXPLAIN` shows the estimated plan and is not a measurement. `EXPLAIN ANALYZE` (MySQL 8.0.18 and later) executes the query and reports actual rows and timing. Keep both, sanitized.
11. **Rows examined and returned.** Report both. A large gap suggests wasted work.
12. **Latency.** Report median and p95 over repeated runs, never a single run or a mean alone.
13. **Dataset size and distribution.** State row counts, key distributions (uniform or skewed), seed and generator. A result on a small uniform dataset does not transfer to a large skewed one.
14. **Warm-up, repetitions, caching.** Discard warm-up runs, state the repetition count, and state whether caches (buffer pool, OS cache) were cold or warm. Compare variants under the same conditions and in interleaved order.
15. **Runtime version and environment.** Record the exact engine version (`SELECT VERSION()`), host or runner type and relevant settings.
16. **Index storage and maintenance.** Record index size and the cost of keeping it current.
17. **Compute efficiency versus monetary cost.** Rows examined, CPU time and bytes read are efficiency proxies. They are not dollars. Do not state a cost saving without actual billing or a stated pricing model.

## Rules

- Conclusions are limited to the measured data and its environment.
- Do not compare Spark and MySQL timings as equivalent. They differ in architecture (distributed, lazy, file-based storage versus a single-node engine with a buffer pool), in data layout, in caching, and in hardware and service limits.
- State limitations, including dataset scale and noise.
- A human reviews the evidence before any result is marked verified.
