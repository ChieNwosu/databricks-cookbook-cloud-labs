"""Cleanup tests for labs/chapter-01/00-smoke-test.py.

These are static checks plus a MOCK harness: the notebook cells are exec()d
against in-memory fake `spark` and `dbutils` objects. This is NOT Databricks
execution and proves nothing about real workspace behaviour.
"""
import ast
import contextlib
import io
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = ROOT / "labs" / "chapter-01" / "00-smoke-test.py"
SEP = "# COMMAND ----------"


def code_cells():
    cells = NOTEBOOK.read_text(encoding="utf-8").split(SEP + "\n")[1:]
    return [c for c in cells if not all(l.startswith("# MAGIC") for l in c.split("\n") if l.strip())]


class FakeRow(dict):
    pass


class FakeDF:
    def __init__(self, rows, spark):
        self.rows, self.spark = rows, spark

    def count(self):
        return len(self.rows)

    def select(self, *cols):
        return FakeDF([{c: r[c] for c in cols} for r in self.rows], self.spark)

    def filter(self, expr):
        col, val = re.fullmatch(r"(\w+) > (\d+)", expr).groups()
        return FakeDF([r for r in self.rows if r[col] > int(val)], self.spark)

    def groupBy(self, col):
        return FakeGroupedDF(self.rows, self.spark, col)

    def orderBy(self, col):
        return FakeDF(sorted(self.rows, key=lambda r: r[col]), self.spark)

    def collect(self):
        return [FakeRow(r) for r in self.rows]

    @property
    def write(self):
        return FakeWriter(self)


class FakeGroupedDF(FakeDF):
    def __init__(self, rows, spark, col):
        super().__init__(rows, spark)
        self.col = col

    def count(self):
        counts = {}
        for r in self.rows:
            counts[r[self.col]] = counts.get(r[self.col], 0) + 1
        return FakeDF([{self.col: k, "count": v} for k, v in counts.items()], self.spark)


class FakeWriter:
    def __init__(self, df):
        self.df, self.m = df, None

    def format(self, _):
        return self

    def mode(self, m):
        self.m = m
        return self

    def option(self, *_):
        return self

    def csv(self, path):
        sp = self.df.spark
        if sp.fail_write:
            raise OSError("injected write failure")
        if self.m == "errorifexists" and any(k.startswith(path) for k in sp.files):
            raise FileExistsError(path)
        sp.files[path + "/part-0.csv"] = self.df.rows

    def saveAsTable(self, name):
        sp = self.df.spark
        if self.m == "errorifexists" and name in sp.tables:
            raise FileExistsError(name)
        sp.tables[name] = self.df.rows


class FakeReader:
    def __init__(self, spark):
        self.spark = spark

    def option(self, *_):
        return self

    def csv(self, path):
        if self.spark.fail_read:
            raise OSError("injected read failure")
        rows = [r for k, v in self.spark.files.items() if k.startswith(path) for r in v]
        return FakeDF(rows, self.spark)


class FakeSpark:
    version = "fake-0"

    def __init__(self, volume_exists=False, lookup_fails=False):
        self.files, self.tables, self.queries = {}, {}, []
        self.volumes = {"unrelated_volume"} | ({"cookbook_smoke_test"} if volume_exists else set())
        self.lookup_fails = lookup_fails
        self.fail_read = self.fail_write = False
        self.wrong_rows = False

    @property
    def read(self):
        return FakeReader(self)

    def createDataFrame(self, rows, cols):
        data = [dict(zip(cols, r)) for r in rows]
        return FakeDF(data[:4] if self.wrong_rows else data, self)

    def table(self, name):
        return FakeDF(self.tables[name], self)

    def sql(self, q):
        self.queries.append(q)
        out = FakeDF([], self)
        if "information_schema.volumes" in q:
            if self.lookup_fails:
                raise RuntimeError("lookup failed")
            out.rows = [{"1": 1}] if "cookbook_smoke_test" in self.volumes else []
        elif q.startswith("CREATE VOLUME"):
            self.volumes.add("cookbook_smoke_test")
        elif q.startswith("DROP VOLUME"):
            self.volumes.discard("cookbook_smoke_test")
        elif q.startswith("DROP TABLE"):
            self.tables.pop(".".join(re.findall(r"`([^`]+)`", q)), None)
        return out


class FakeFs:
    def __init__(self, spark, rm_fails=False):
        self.spark, self.rm_fails, self.rm_calls = spark, rm_fails, []

    def rm(self, path, recurse=False):
        self.rm_calls.append(path)
        if self.rm_fails:
            raise OSError("injected rm failure")
        for k in [k for k in self.spark.files if k == path or k.startswith(path + "/")]:
            del self.spark.files[k]

    def ls(self, path):
        return [k for k in self.spark.files if k.startswith(path + "/")]


class FakeWidgets:
    def text(self, *_):
        pass

    def get(self, name):
        return {"catalog": "workspace", "schema": "default", "volume": "cookbook_smoke_test"}[name]


class FakeDbutils:
    def __init__(self, spark, rm_fails=False):
        self.fs, self.widgets = FakeFs(spark, rm_fails), FakeWidgets()


def run_notebook(spark, rm_fails=False):
    """Exec the code cells in order. Returns (namespace, stdout, exception or None)."""
    dbu = FakeDbutils(spark, rm_fails)
    ns = {"spark": spark, "dbutils": dbu, "__name__": "mock_notebook"}
    buf, exc = io.StringIO(), None
    with contextlib.redirect_stdout(buf):
        try:
            for cell in code_cells():
                exec(compile(cell, str(NOTEBOOK), "exec"), ns)
        except Exception as e:  # the notebook is expected to raise on failure
            exc = e
    return ns, buf.getvalue(), exc, dbu


class StaticChecks(unittest.TestCase):
    def setUp(self):
        self.src = NOTEBOOK.read_text(encoding="utf-8")
        self.tree = ast.parse("\n".join(code_cells()))

    def test_try_finally_present(self):
        tries = [n for n in ast.walk(self.tree) if isinstance(n, ast.Try) and n.finalbody]
        self.assertTrue(tries)

    def test_run_id_scopes_names(self):
        self.assertIn("uuid.uuid4().hex[:8]", self.src)
        self.assertRegex(self.src, r'table_short = f"cookbook_smoke_\{run_id\}"')
        self.assertRegex(self.src, r'run_dir = f"\{volume_root\}/smoke_\{run_id\}"')

    def test_rm_only_inside_guard(self):
        for fn in [n for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef)]:
            if fn.name != "safe_rm":
                self.assertNotIn("dbutils.fs.rm", ast.unparse(fn))
        top_level = ast.Module(body=[n for n in self.tree.body if not isinstance(n, ast.FunctionDef)], type_ignores=[])
        calls = re.findall(r"dbutils\.fs\.rm\(([^)]*)\)", ast.unparse(top_level))
        self.assertEqual(calls, [])
        self.assertNotRegex(self.src, r"rm\(\s*volume_root")

    def test_failure_raised_after_cleanup(self):
        cell = next(c for c in code_cells() if "finally:" in c)
        self.assertLess(cell.index("finally:"), cell.rindex("raise RuntimeError"))

    def test_no_assert_before_cleanup(self):
        cell = next(c for c in code_cells() if "finally:" in c)
        self.assertNotIn("assert ", cell)


class MockHarness(unittest.TestCase):
    """Mock-based only. Not Databricks execution."""

    def test_happy_path_cleans_everything_and_drops_created_volume(self):
        sp = FakeSpark(volume_exists=False)
        ns, out, exc, dbu = run_notebook(sp)
        self.assertIsNone(exc, out)
        self.assertEqual(sp.files, {})
        self.assertEqual(sp.tables, {})
        self.assertNotIn("cookbook_smoke_test", sp.volumes)
        self.assertIn("unrelated_volume", sp.volumes)

    def test_check_raising_still_cleans_up_and_reports(self):
        sp = FakeSpark()
        sp.fail_read = True
        ns, out, exc, dbu = run_notebook(sp)
        self.assertIsInstance(exc, RuntimeError)
        self.assertIn("csv_roundtrip", str(exc))
        self.assertIn("OSError", str(exc))
        self.assertEqual(sp.files, {})
        self.assertEqual(sp.tables, {})
        self.assertTrue(dbu.fs.rm_calls)

    def test_failed_check_value_is_reported_after_cleanup(self):
        sp = FakeSpark()
        sp.wrong_rows = True
        ns, out, exc, dbu = run_notebook(sp)
        self.assertIsInstance(exc, RuntimeError)
        self.assertIn("in_memory_rows", str(exc))
        self.assertEqual(sp.files, {})
        self.assertEqual(sp.tables, {})

    def test_write_failure_still_cleans_up(self):
        sp = FakeSpark()
        sp.fail_write = True
        ns, out, exc, dbu = run_notebook(sp)
        self.assertIsInstance(exc, RuntimeError)
        self.assertIn("unexpected error OSError", str(exc))
        self.assertTrue(dbu.fs.rm_calls)

    def test_only_run_scoped_resources_removed(self):
        sp = FakeSpark(volume_exists=True)
        root = "/Volumes/workspace/default/cookbook_smoke_test"
        sp.files[f"{root}/user_data/keep.csv"] = [{"a": 1}]
        sp.files[f"{root}/smoke_deadbeef/old.csv"] = [{"a": 2}]
        sp.tables["workspace.default.cookbook_smoke_deadbeef"] = [{"a": 3}]
        sp.tables["workspace.default.people"] = [{"a": 4}]
        ns, out, exc, dbu = run_notebook(sp)
        self.assertIsNone(exc, out)
        run_dir = ns["run_dir"]
        for path in dbu.fs.rm_calls:
            self.assertTrue(path == run_dir or path.startswith(run_dir + "/"), path)
        self.assertIn(f"{root}/user_data/keep.csv", sp.files)
        self.assertIn(f"{root}/smoke_deadbeef/old.csv", sp.files)
        self.assertIn("workspace.default.people", sp.tables)
        self.assertIn("workspace.default.cookbook_smoke_deadbeef", sp.tables)

    def test_preexisting_volume_is_never_dropped(self):
        sp = FakeSpark(volume_exists=True)
        ns, out, exc, dbu = run_notebook(sp)
        self.assertIsNone(exc, out)
        self.assertIn("cookbook_smoke_test", sp.volumes)
        self.assertFalse(any(q.startswith("DROP VOLUME") for q in sp.queries))

    def test_unknown_volume_state_is_never_dropped(self):
        sp = FakeSpark(volume_exists=True, lookup_fails=True)
        ns, out, exc, dbu = run_notebook(sp)
        self.assertIsNone(exc, out)
        self.assertIn("cookbook_smoke_test", sp.volumes)
        self.assertFalse(any(q.startswith("DROP VOLUME") for q in sp.queries))

    def test_cleanup_failure_does_not_mask_original_error(self):
        sp = FakeSpark()
        sp.fail_read = True
        ns, out, exc, dbu = run_notebook(sp, rm_fails=True)
        self.assertIsInstance(exc, RuntimeError)
        self.assertIn("csv_roundtrip", str(exc))
        self.assertIn("WARNING: path cleanup failed", out)

    def test_run_ids_differ_between_runs(self):
        a = run_notebook(FakeSpark())[0]["run_id"]
        b = run_notebook(FakeSpark())[0]["run_id"]
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
