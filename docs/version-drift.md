# Version drift

`catalog/versions.json` tracks upstream component versions (Spark 3.4.1, Kafka 3.5.1, ZooKeeper 3.8.2, JupyterLab 4.0.2; Delta not yet determined, so `null`) against the Databricks Free Edition runtime. Free Edition values stay `null` until observed in a real workspace.

## Cadence

Review at the start of each phase and at least every 90 days.

## Recording drift

1. Observe the runtime, Spark and Delta versions in a workspace and record them under `free_edition` with date, observer and an evidence link.
2. Add an entry to `drift_log` describing what differs and which recipes are affected.
3. Add a "Drift notes" entry in each affected recipe note.
