# Upstream analysis

Upstream: [PacktPublishing/Data-Engineering-with-Databricks-Cookbook](https://github.com/PacktPublishing/Data-Engineering-with-Databricks-Cookbook). Analysis is based on the repository file tree (GitHub API listing, 111 paths) and the upstream LICENSE file. Notebook contents were not copied or reproduced here.

## Structure

- `Chapter01` to `Chapter11`: one folder per chapter.
- Chapters 1 to 7 hold Jupyter notebooks named `<recipe id> <slug>.ipynb`. Chapters 4 and 5 also hold `4.0` and `5.0` notebooks that generate Kafka test data.
- Chapter 8 holds two workflow YAML files (8.1, 8.4) and four support SQL files (Setup, Clean Up, Data Preparation DLT, Download Inventory Data).
- Chapter 9 holds SQL pipeline files plus a bundle folder for 9.6.
- Chapter 10 holds SQL files and a diagram under `diagrams/Chapter10`.
- Chapter 11 holds Python files and a full asset bundle example with GitHub Actions workflows for 11.5.
- Root files: `docker-compose.yml`, `docker/` (base, jupyterlab, spark-base, spark-master, spark-worker), `build.sh`, `data/`.

Recipe counts evidenced by file names: 63 of the 72 expected. See [coverage-ledger.md](coverage-ledger.md) for per-chapter gaps. IDs without an upstream artifact are not given invented titles.

## Docker-based architecture

Upstream runs locally with Docker Compose: a Kafka broker (3.5.1) with ZooKeeper, a Spark 3.4.1 standalone cluster (one master, two workers), and a JupyterLab container. Notebooks therefore assume a local Spark session, local file paths and a reachable Kafka broker.

## Data folder inventory (names only)

- `data/Credit Card/`: CardBase, CustomerBase, FraudBase, TransactionBase (CSV)
- `Online_Retail.csv`, `Reviews.csv`, `netflix_titles.csv`, `netflix_titles_batch_2.csv`, `titles.csv`
- `Stanford Question Answering Dataset.json`, `nobel_prizes.json`
- `nobel_prizes.xml`
- `recipes.parquet`

## Licensing

The upstream LICENSE is the MIT License, copyright 2023 Packt. MIT permits copying with the notice retained. This repository still vendors nothing from upstream: no notebooks, no datasets, no book text. Labs here are written independently and reference upstream only by path and URL. Datasets should be obtained from their original public sources; confirm each dataset's own license before use, since the MIT file does not necessarily cover third-party data.

## Mapping upstream dependencies to Free Edition

Free Edition constraints are summarized in [compatibility-matrix.md](compatibility-matrix.md). These mappings are preliminary and unverified.

| Upstream dependency | Free Edition approach | Class impact |
| --- | --- | --- |
| Kafka broker and ZooKeeper | No local broker and outbound access is limited. Use a rate source or files landing in a volume to simulate a stream. | Kafka recipes become adapted or alt_env |
| Spark master and workers, `spark.master` and cluster configs | Serverless compute only. Remove master settings and cluster-level tuning configs. | adapted |
| JupyterLab and local Spark session | Use Databricks notebooks with the provided `spark` session. | adapted |
| Local file paths under `data/` | Upload data to a Unity Catalog volume and read from the volume path. | adapted |
| RDD, `sparkContext`, cache and persist APIs | Restricted on serverless. Use DataFrame APIs or explain the restriction. | adapted |
| Docker build scripts | Not applicable in a browser workspace. | not used |
| Databricks CLI, VS Code extension, bundles, GitHub Actions | Run outside the browser. | alt_env |
