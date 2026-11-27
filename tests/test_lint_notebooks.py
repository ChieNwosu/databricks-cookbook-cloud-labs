import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import lint_notebooks as ln  # noqa: E402

GOOD = "# Databricks notebook source\n# MAGIC %md\n# MAGIC hi\n\n# COMMAND ----------\n\nx = 1\n"


class LintTests(unittest.TestCase):
    def test_good(self):
        self.assertEqual(ln.lint_text(GOOD), [])

    def test_missing_header(self):
        self.assertTrue(ln.lint_text(GOOD.replace("# Databricks notebook source", "# x", 1)))

    def test_no_separator(self):
        self.assertTrue(ln.lint_text("# Databricks notebook source\n# MAGIC %md\n# MAGIC hi\n"))

    def test_syntax_error(self):
        self.assertTrue(any("does not parse" in e for e in ln.lint_text(GOOD + "def (:\n")))

    def test_magic_cells_skipped(self):
        self.assertEqual(ln.lint_text(GOOD + "\n# COMMAND ----------\n\n# MAGIC %sql\n# MAGIC select 1\n"), [])

    def test_forbidden(self):
        for bad in ('spark.conf.set("spark.master", "x")', "sc = spark.sparkContext", 'token = "abc"',
                    'p = "dbfs:/tmp"', "k = 'dapi" + "0" * 32 + "'"):
            with self.subTest(bad=bad):
                self.assertTrue(any("forbidden" in e for e in ln.lint_text(GOOD + bad + "\n")))

    def test_real_labs_pass(self):
        for p in (ROOT / "labs").rglob("*.py"):
            self.assertEqual(ln.lint_file(p, ROOT), [])


if __name__ == "__main__":
    unittest.main()
