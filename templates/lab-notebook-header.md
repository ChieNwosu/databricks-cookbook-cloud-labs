# Lab notebook header and cell conventions

Source notebooks are Databricks source-format Python files (`.py`).

1. First line: `# Databricks notebook source`.
2. Cells are separated by `# COMMAND ----------`.
3. First cell is a markdown cell (`# MAGIC %md`) with: recipe id, title, compatibility class, status, and a link to the recipe note.
4. Second cell defines parameters (catalog, schema, volume path) in one place. No hard-coded workspace names, tokens or user emails.
5. Every cell must be re-runnable. Create data the lab needs inside the notebook or from a volume you populate yourself.
6. No outputs are committed. Do not paste results into the notebook.
7. Last cell cleans up objects the lab created.
8. Code must be original and compile with `python -m py_compile` after magic lines are ignored.
