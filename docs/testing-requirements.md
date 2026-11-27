# Testing and verification requirements

## Status ladder

`not_started` > `drafted` > `executed_unreviewed` > `verified`

- `not_started`: catalog entry only.
- `drafted`: original note and notebook written, never run.
- `executed_unreviewed`: run on Databricks, not yet reviewed by a human.
- `verified`: requires all of the following.
  - An evidence file that exists in the repo.
  - A named human reviewer.
  - The Databricks runtime version.
  - The verification date.

Recipes of class `alt_env` cannot be `verified` without evidence from the alternative environment.

## Automated checks

`python scripts/validate_catalog.py` checks catalog schema, ids, enums, the verified rules above, referenced paths, note front matter, generated docs freshness and secret-like patterns. It cannot run notebooks. The coverage gap against the expected 72 recipes is a warning by default and an error with `--strict`.

`python -m unittest discover -s tests -v` runs the validator tests, including negative cases.

Automated checks never replace a real Databricks run or human review.
