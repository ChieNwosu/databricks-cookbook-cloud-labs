# Databricks notebook source
# MAGIC %md
# MAGIC # Chapter 1 smoke test
# MAGIC
# MAGIC - Lab id: 1.0 (setup check, not a cookbook recipe)
# MAGIC - Compatibility class: native
# MAGIC - Status: drafted. Never executed by the authors. Do not treat as verified.
# MAGIC - Note: `notes/chapter-01/1.1-read-csv-data.md` covers recipe 1.1; this notebook only checks the environment.
# MAGIC
# MAGIC Every run uses a unique run id. Only resources created by this run are cleaned up, in a `finally` block, and a failed check is reported after cleanup.
# MAGIC
# MAGIC This notebook checks that a Databricks workspace can run basic PySpark, write and read a small CSV file and a small Delta table.
# MAGIC The catalog, schema and volume defaults below are to be confirmed on Databricks Free Edition. Change them with the widgets at the top.
# MAGIC Verify the workspace UI labels against the current UI.

# COMMAND ----------

# Parameters: the only place names are defined.
import uuid

dbutils.widgets.text("catalog", "workspace", "Catalog (to be confirmed on Free Edition)")
dbutils.widgets.text("schema", "default", "Schema (to be confirmed on Free Edition)")
dbutils.widgets.text("volume", "cookbook_smoke_test", "Volume name")

catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
volume = dbutils.widgets.get("volume").strip()

for label, value in (("catalog", catalog), ("schema", schema), ("volume", volume)):
    if not value.replace("_", "").isalnum():
        raise ValueError(f"widget '{label}' must contain only letters, digits and underscores")

# One run id per execution. Every path and table name below is derived from it.
run_id = uuid.uuid4().hex[:8]
volume_root = f"/Volumes/{catalog}/{schema}/{volume}"
run_dir = f"{volume_root}/smoke_{run_id}"
csv_dir = f"{run_dir}/people_csv"
table_short = f"cookbook_smoke_{run_id}"
delta_table = f"{catalog}.{schema}.{table_short}"
print("run_id:", run_id)
print("run_dir:", run_dir)
print("delta_table:", delta_table)

# COMMAND ----------

# All work and cleanup happen in this one cell so a failure cannot skip cleanup.
EXPECTED_CHECKS = ("in_memory_rows", "filter_rows", "groupby_counts", "csv_roundtrip", "delta_roundtrip")
checks = {}
problems = []  # failed checks and unexpected exceptions
warnings = []  # cleanup problems, never allowed to hide a problem above
created_path = False
created_table = False
created_volume = False


def describe(exc):
    return f"{type(exc).__name__}: {str(exc)[:200]}"


def record(name, fn):
    """Run one check. An exception is recorded as a failure with its type and message."""
    try:
        checks[name] = bool(fn())
    except Exception as exc:
        checks[name] = False
        problems.append(f"check {name} raised {describe(exc)}")


def safe_rm(path):
    """Remove a path only if it is inside this run's directory."""
    if path != run_dir and not path.startswith(run_dir + "/"):
        raise RuntimeError(f"refusing to remove path outside the run directory: {path}")
    dbutils.fs.rm(path, True)


def volume_existed():
    """True or False if known. None if the lookup failed, which is treated as 'do not drop'."""
    try:
        found = spark.sql(
            f"SELECT 1 FROM `{catalog}`.information_schema.volumes "
            f"WHERE volume_schema = '{schema}' AND volume_name = '{volume}'"
        ).collect()
        return len(found) > 0
    except Exception:
        return None


try:
    print("Spark version:", spark.version)

    # Small in-memory DataFrame, transformed with select, filter and groupBy.
    rows = [
        ("ada", "analytics", 34),
        ("bo", "analytics", 28),
        ("cy", "platform", 41),
        ("di", "platform", 25),
        ("ed", "platform", 39),
    ]
    df = spark.createDataFrame(rows, ["name", "team", "age"])
    selected = df.select("name", "team", "age")
    record("in_memory_rows", lambda: df.count() == 5)
    record("filter_rows", lambda: selected.filter("age > 30").count() == 3)
    record(
        "groupby_counts",
        lambda: {r["team"]: r["count"] for r in df.groupBy("team").count().orderBy("team").collect()}
        == {"analytics": 2, "platform": 3},
    )

    # Create the volume if needed. This run owns it only if it did not exist before.
    existed = volume_existed()
    if existed is None:
        warnings.append("volume lookup failed: ownership unknown, so the volume is never dropped. "
                        "If this run created it, remove it by hand")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS `{catalog}`.`{schema}`.`{volume}`")
    created_volume = existed is False

    # Write and read back a small CSV in the run-scoped directory.
    created_path = True
    df.write.mode("errorifexists").option("header", True).csv(csv_dir)

    def csv_check():
        back = spark.read.option("header", True).option("inferSchema", True).csv(csv_dir)
        return back.count() == 5

    record("csv_roundtrip", csv_check)

    # Write and read back a small Delta table with a run-scoped name.
    created_table = True
    df.write.format("delta").mode("errorifexists").saveAsTable(delta_table)
    record("delta_roundtrip", lambda: spark.table(delta_table).count() == 5)
except Exception as exc:
    problems.append(f"unexpected error {describe(exc)}")
finally:
    # Cleanup touches only what this run created. Failures here are warnings.
    if created_table:
        try:
            if not delta_table.endswith("." + table_short):
                raise RuntimeError("refusing to drop a table that is not run-scoped")
            spark.sql(f"DROP TABLE IF EXISTS `{catalog}`.`{schema}`.`{table_short}`")
        except Exception as exc:
            warnings.append(f"table cleanup failed: {describe(exc)}")
    if created_path:
        try:
            safe_rm(run_dir)
        except Exception as exc:
            warnings.append(f"path cleanup failed: {describe(exc)}")
    if created_volume:
        try:
            if len(dbutils.fs.ls(volume_root)) == 0:
                spark.sql(f"DROP VOLUME IF EXISTS `{catalog}`.`{schema}`.`{volume}`")
            else:
                warnings.append("volume created by this run is not empty and was kept")
        except Exception as exc:
            warnings.append(f"volume cleanup failed: {describe(exc)}")

# Report after cleanup, then fail loudly if anything went wrong.
for name in EXPECTED_CHECKS:
    print(("PASS" if checks.get(name) else "FAIL" if name in checks else "NOT RUN"), name)
for w in warnings:
    print("WARNING:", w)
failed = [n for n in EXPECTED_CHECKS if not checks.get(n)]
print("OVERALL:", "PASS" if not failed and not problems else "FAIL")
if failed or problems:
    raise RuntimeError(f"smoke test failed. Checks not passing: {failed}. Problems: {problems}")
print("Cleanup done for run", run_id)
