# Contributing

## Human review gate

Nothing is marked `verified` without a human reviewer and real Databricks evidence (a run link or screenshot, the runtime version and the date). Automated tools and AI assistants may draft content. They may not set `verified`, and they must not invent run output.

Statuses: `not_started`, `drafted`, `executed_unreviewed`, `verified`. See [docs/testing-requirements.md](docs/testing-requirements.md).

## No copying

Do not copy text, notebooks or data from the book or from the upstream Packt repository. Write explanations and code yourself. Link to upstream paths instead. See [docs/provenance.md](docs/provenance.md).

## Secrets

Never commit tokens, keys, passwords, workspace URLs with personal data or emails. The validator and notebook lint scan for common patterns.

## Before opening a pull request

```
python scripts/generate_docs.py
python scripts/validate_catalog.py
python scripts/lint_notebooks.py
python -m unittest discover -s tests -v
```

Edit `catalog/*.json` by hand, then regenerate the docs. CI runs the same checks.

## Evidence

Add evidence under `evidence/<chapter>/` using `templates/evidence-record.md`. Remove private details first.
