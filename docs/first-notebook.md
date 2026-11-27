# Run the Chapter 1 smoke test

This guide gets `labs/chapter-01/00-smoke-test.py` running in Databricks Free Edition.

**Status: drafted. No one has executed this notebook.** The authors of Phase 0 had no Databricks access, so every UI label, default name and expected output below is unconfirmed. Where a label appears in quotes, verify it against the current UI.

## What the notebook does

It prints the Spark version, builds a five-row DataFrame in memory, runs a select, a filter and a group-by, writes and reads back a small CSV file in a Unity Catalog volume, writes and reads back a small Delta table, checks the row counts and prints PASS or FAIL. A final cell deletes what it created.

## 1. Get a workspace

1. Go to the Databricks Free Edition sign-up page (find the current link from the Databricks site) and create an account or sign in.
2. Open your workspace in the browser.

## 2. Bring the notebook in

Choose one option.

### Option A: Git folder (whole repo)

1. In the sidebar, open **Workspace** (verify against current UI).
2. Select **Create** and then **Git folder** (verify against current UI).
3. Set the Git repository URL to `https://github.com/ChieNwosu/databricks-cookbook-cloud-labs`. The repo is public, so no token is needed. Leave the provider as GitHub.
4. Select **Create Git folder**, then open `labs/chapter-01/00-smoke-test`.

If the Git folder option is not offered on Free Edition, use Option B.

### Option B: Import the single file

1. Download `labs/chapter-01/00-smoke-test.py` from the repo (the **Raw** button on GitHub, then save the file).
2. In **Workspace**, select **Create** (or the menu on a folder) and then **Import** (verify against current UI).
3. Upload the `.py` file. Databricks should read it as a notebook because of the first line `# Databricks notebook source`.

## 3. Attach compute

1. Open the notebook.
2. In the compute selector at the top right, choose **Serverless** (verify against current UI).

## 4. Check the widgets

The notebook creates three widgets at the top: `catalog`, `schema` and `volume`. The defaults are `workspace`, `default` and `cookbook_smoke_test`. These defaults are **to be confirmed on Free Edition**. Open **Catalog** in the sidebar to see which catalog and schema you can write to, and change the widgets if needed. The notebook runs `CREATE VOLUME IF NOT EXISTS` for the volume name you give it. Each run gets a unique 8 character run id. It writes only to `smoke_<run id>` inside the volume and to a table named `cookbook_smoke_<run id>`. A `finally` block removes only those, and drops the volume only if this run created it and it is empty. If a check fails, the failure is raised after cleanup. If cleanup itself fails, the notebook prints a warning with the run id so you can remove the leftovers by hand.

## 5. Run all

Select **Run all**. The cells run top to bottom.

## What PASS looks like

The output of the report cell should contain one `PASS <check>` line for each of the five checks (`in_memory_rows`, `filter_rows`, `groupby_counts`, `csv_roundtrip`, `delta_roundtrip`), then `OVERALL: PASS`. The first lines print the Spark version. Any `FAIL` line, or an error in a cell, means the run did not pass. Common causes are a catalog or schema you cannot write to, or a missing permission to create a volume. Record what you see honestly, including failures.

## Capture evidence

1. Take a screenshot of the report cell output, or export the notebook as HTML (**File**, **Export**, **HTML**; verify against current UI).
2. Save it under `evidence/chapter-01/`, for example `evidence/chapter-01/smoke-test-YYYY-MM-DD.html`. Remove anything private (names, emails, workspace URLs) first.
3. Copy `templates/evidence-record.md` to a new file in `evidence/chapter-01/` and fill it in with real values: the runtime version shown in the compute details, the date and the result.
4. Open a pull request with the files.

## Status after a run

After a real run the status in `catalog/labs.json` may become `executed_unreviewed`. It stays there until a human reviews the evidence. Only a reviewer sets `verified`, and the validator rejects `verified` entries without evidence, a reviewer, a runtime and a date.
