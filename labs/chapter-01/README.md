# Chapter 1 labs

| File | Purpose | Status |
| --- | --- | --- |
| `00-smoke-test.py` | Checks PySpark, CSV and Delta round trips in a Unity Catalog volume | drafted, never executed |

The notebook is a Databricks source-format Python file. It is original code and does not copy upstream notebooks.

No one has run this notebook. Follow [docs/first-notebook.md](../../docs/first-notebook.md) to import it, run it on Serverless compute and capture evidence.

Quick path:

1. Workspace, Create, Git folder, URL `https://github.com/ChieNwosu/databricks-cookbook-cloud-labs` (or Workspace, Import, upload the `.py` file). Verify labels against the current UI.
2. Attach Serverless compute.
3. Check the `catalog`, `schema` and `volume` widgets (defaults are to be confirmed on Free Edition).
4. Run all and look for `OVERALL: PASS`.
5. Save a screenshot or HTML export under `evidence/chapter-01/` through a pull request.
