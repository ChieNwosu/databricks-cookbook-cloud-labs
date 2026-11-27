# Testing and verification requirements

## Status ladder

`not_started` > `drafted` > `executed_unreviewed` > `verified`

- `not_started`: catalog entry only.
- `drafted`: original note and notebook written, never run.
- `executed_unreviewed`: run on Databricks, not yet reviewed by a human. Requires at least one existing evidence file.
- `verified`: requires all of the following.
  - An evidence file that exists in the repo.
  - A named human reviewer.
  - The Databricks runtime version.
  - The verification date.

Evidence paths must be repo-relative, contain no `..`, resolve (after symlinks) inside `evidence/`, and point to an existing file. The same rule applies to recipes and labs.

Recipes of class `alt_env` cannot be `verified` without evidence from the alternative environment.

## Automated checks

`python scripts/validate_catalog.py` checks catalog schema, ids, enums, the verified rules above, referenced paths, note front matter, generated docs freshness and secret-like patterns. It cannot run notebooks. The coverage gap against the expected 72 recipes is a warning by default and an error with `--strict`.

`python -m unittest discover -s tests -v` runs the validator tests, including negative cases.

## Consistency rules

- A note's `recipe_id`, `chapter`, `title`, `compatibility` and `status` must equal its catalog entry. At `executed_unreviewed` and `verified`, `evidence_links` must be non-empty and equal the catalog `evidence`. Notes without a catalog recipe are errors.
- `compatibility: alt_env` and `requires_alt_env: true` go together. The one exception is a recipe with a `classification_unresolved` record (`question`, `source`, `retrieved`), which means a human must still decide. The compatibility matrix shows `unresolved` for those recipes. Recipe 6.1 is currently in that state.
- Symlinks that resolve outside the repository are errors and are never followed.

## Secret scanning is best effort

`scripts/secret_patterns.py` holds the patterns shared by the validator and the notebook lint (common token formats, private key headers, passwords in URLs, workspace hostnames, quoted secret assignments in code, and email addresses outside an allowlist). It will miss secrets that do not match these shapes. A clean scan is not proof that nothing sensitive is present, so review diffs and evidence by hand.

## Why `--strict` still fails

`python scripts/validate_catalog.py --strict` fails on purpose: 63 recipes are evidenced against an expected total of 72. The total comes from the user's statement and has not been reconciled with the physical book's table of contents. `catalog/coverage_gaps.json` names six unconfirmed IDs (8.2, 8.3, 9.2, 10.1, 10.3, 11.2) and notes that chapter 7 may have recipes after 7.4. That does not add up to a confirmed list of nine, so the missing IDs and titles stay unknown until the human supplies the table of contents. The expected total is not lowered and no entries are invented to make strict mode pass.

Automated checks never replace a real Databricks run or human review.
