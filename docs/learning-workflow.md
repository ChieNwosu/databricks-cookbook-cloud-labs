# Learning workflow

You learn each recipe by doing it. Kiro helps. Kiro does not complete the cookbook for you.

1. You read the physical-book recipe.
2. You identify its objective and predict the expected behavior.
3. Kiro provides scaffolding, hints and compatibility guidance.
4. You attempt the implementation.
5. You execute the lab in Databricks or an approved SQL environment.
6. Kiro reviews your code and the evidence you supply.
7. Automated validation checks the repository records (`python scripts/validate_catalog.py` and the other checks).
8. You approve verification. Only a human sets `verified`.
9. Original evergreen knowledge is produced, and your reflections stay in the human-authored section of the note.

Supplemental SQL work follows the same loop and never replaces the book objective. See [sql-companion.md](sql-companion.md) and [knowledge-governance.md](knowledge-governance.md).

Phase 0.1 stops before Recipe 1.1. The next phase starts only on your explicit approval.
