# Databricks notebook source
# MAGIC %md
# MAGIC # Chapter 1 smoke test
# MAGIC
# MAGIC - Lab id: 1.0 (setup check, not a cookbook recipe)
# MAGIC - Compatibility class: native
# MAGIC - Status: drafted. Never executed by the authors. Do not treat as verified.
# MAGIC - Note: `notes/chapter-01/1.1-read-csv-data.md` covers recipe 1.1; this notebook only checks the environment.
# MAGIC
# MAGIC This notebook checks that a Databricks workspace can run basic PySpark, write and read a small CSV file and a small Delta table.
# MAGIC The catalog, schema and volume defaults below are to be confirmed on Databricks Free Edition. Change them with the widgets at the top.
# MAGIC Verify the workspace UI labels against the current UI.

# COMMAND ----------

# Parameters: the only place names are defined.
dbutils.widgets.text("catalog", "workspace", "Catalog (to be confirmed on Free Edition)")
dbutils.widgets.text("schema", "default", "Schema (to be confirmed on Free Edition)")
dbutils.widgets.text("volume", "cookbook_smoke_test", "Volume name")

catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
volume = dbutils.widgets.get("volume").strip()

for label, value in (("catalog", catalog), ("schema", schema), ("volume", volume)):
    if not value.replace("_", "").isalnum():
        raise ValueError(f"widget '{label}' must contain only letters, digits and underscores")

volume_dir = f"/Volumes/{catalog}/{schema}/{volume}/smoke_test"
csv_dir = f"{volume_dir}/people_csv"
delta_table = f"`{catalog}`.`{schema}`.`cookbook_smoke_test_delta`"
print("volume_dir:", volume_dir)
print("delta_table:", delta_table)

# COMMAND ----------

checks = {}
print("Spark version:", spark.version)

# COMMAND ----------

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
adults_over_30 = selected.filter(selected.age > 30)
per_team = df.groupBy("team").count().orderBy("team")

checks["in_memory_rows"] = df.count() == 5
checks["filter_rows"] = adults_over_30.count() == 3
per_team_counts = {r["team"]: r["count"] for r in per_team.collect()}
checks["groupby_counts"] = per_team_counts == {"analytics": 2, "platform": 3}

# COMMAND ----------

# Create the volume if needed, then write and read back a small CSV.
spark.sql(f"CREATE VOLUME IF NOT EXISTS `{catalog}`.`{schema}`.`{volume}`")
df.write.mode("overwrite").option("header", True).csv(csv_dir)
csv_back = spark.read.option("header", True).option("inferSchema", True).csv(csv_dir)
checks["csv_roundtrip"] = csv_back.count() == 5

# COMMAND ----------

# Write and read back a small Delta table.
df.write.format("delta").mode("overwrite").saveAsTable(delta_table.replace("`", ""))
delta_back = spark.table(delta_table.replace("`", ""))
checks["delta_roundtrip"] = delta_back.count() == 5

# COMMAND ----------

# Report the result.
for name, ok in checks.items():
    print(("PASS" if ok else "FAIL"), name)
overall = all(checks.values()) and len(checks) == 5
print("OVERALL:", "PASS" if overall else "FAIL")
assert overall, "smoke test failed, see the lines above"

# COMMAND ----------

# Cleanup: remove the files and the table this notebook created. The volume is kept.
dbutils.fs.rm(volume_dir, True)
spark.sql(f"DROP TABLE IF EXISTS {delta_table}")
print("Cleanup done")
