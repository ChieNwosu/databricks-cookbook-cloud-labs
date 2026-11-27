# databricks-cookbook-cloud-labs

Original, cloud-first labs that follow the topics of a Databricks data engineering cookbook and adapt them to Databricks Free Edition. The repo tracks which recipes run unchanged, which need adaptation and which need an environment Free Edition does not offer.

## Status

**No lab in this repo is verified.** Phase 0 provides the catalog, validators, templates and one Chapter 1 smoke test notebook. No notebook has been executed, and the authors had no Databricks access. Every status is `not_started` or `drafted`. Compatibility classes are preliminary.

See the [coverage ledger](docs/coverage-ledger.md) for counts and gaps (63 of 72 recipes are evidenced upstream, 9 are unaccounted for).

## Quickstart

1. Create or sign in to a Databricks Free Edition workspace.
2. Follow [docs/first-notebook.md](docs/first-notebook.md) to import and run [labs/chapter-01/00-smoke-test.py](labs/chapter-01/00-smoke-test.py).
3. Save evidence under `evidence/chapter-01/` through a pull request.

Local checks need only Python 3.11:

```
python scripts/validate_catalog.py
python scripts/generate_docs.py --check
python scripts/lint_notebooks.py
python -m unittest discover -s tests -v
```

## Docs

- [First notebook](docs/first-notebook.md)
- [Coverage ledger](docs/coverage-ledger.md)
- [Compatibility matrix](docs/compatibility-matrix.md)
- [Upstream analysis](docs/upstream-analysis.md)
- [Provenance](docs/provenance.md)
- [Testing requirements](docs/testing-requirements.md)
- [Version drift](docs/version-drift.md)
- [Contributing](CONTRIBUTING.md)

Catalog data lives in [catalog/](catalog/). Templates live in [templates/](templates/).

## Guardrails

- No book text, upstream notebooks or upstream data are copied.
- No fabricated results. Nothing is `verified` without human review and real evidence.
- No secrets in the repo.
- No Docker and no paid cloud resources.

## Licence and attribution

This repo is under the [LICENSE](LICENSE) in the repo root. It is an independent project. The topics follow *Data Engineering with Databricks Cookbook* by Pulkit Chadha, published by Packt, and the upstream code repository [PacktPublishing/Data-Engineering-with-Databricks-Cookbook](https://github.com/PacktPublishing/Data-Engineering-with-Databricks-Cookbook) (MIT, Packt 2023) is linked, not vendored. Not affiliated with or endorsed by Packt, the author or Databricks.

Repo: https://github.com/ChieNwosu/databricks-cookbook-cloud-labs
