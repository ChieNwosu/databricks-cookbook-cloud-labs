import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))


def _load(name):
    spec = importlib.util.spec_from_file_location(name + "_t", REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = _load("check_policy")
V = _load("validate_catalog")

GOOD_MYSQL_WF = """name: mysql-manual
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  j:
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    steps:
      - uses: actions/upload-artifact@v4
        with:
          path: out/
          retention-days: 3
"""


class PolicyCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for d in (".kiro", ".github", "templates", "docs", "catalog"):
            shutil.copytree(REPO / d, self.root / d)
        for f in ("README.md", "CONTRIBUTING.md"):
            shutil.copy(REPO / f, self.root / f)

    def tearDown(self):
        self.tmp.cleanup()

    def steer(self, name):
        return self.root / ".kiro" / "steering" / f"{name}.md"

    def wf(self, name, text):
        d = self.root / ".github" / "workflows"
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_text(text, encoding="utf-8")

    def assertRejected(self, fragment):
        errs = P.check_policy(self.root)
        self.assertTrue(any(fragment in e for e in errs), f"{fragment!r} not in {errs}")


class TestPolicy(PolicyCase):
    def test_repo_passes(self):
        self.assertEqual(P.check_policy(REPO), [])

    def test_missing_steering_file(self):
        self.steer("product").unlink()
        self.assertRejected("product.md: steering file missing")

    def test_wrong_inclusion_on_core_file(self):
        self.steer("output-guardrails").write_text("---\ninclusion: manual\n---\n# x\n")
        self.assertRejected("core steering must use 'inclusion: always'")

    def test_invalid_inclusion_value(self):
        self.steer("tech").write_text("---\ninclusion: sometimes\n---\n# x\n")
        self.assertRejected("invalid inclusion")

    def test_invalid_frontmatter(self):
        self.steer("tech").write_text("# no frontmatter\n")
        self.assertRejected("invalid frontmatter")

    def test_filematch_without_pattern(self):
        self.steer("sql-performance").write_text("---\ninclusion: fileMatch\n---\n# x\n")
        self.assertRejected("needs fileMatchPattern")

    def test_em_dash_in_steering(self):
        p = self.steer("structure")
        p.write_text(p.read_text() + "bad \u2014 dash\n")
        self.assertRejected("structure.md: contains an em dash")

    def test_em_dash_in_governance_doc(self):
        p = self.root / "docs" / "agent-governance.md"
        p.write_text(p.read_text() + "x \u2014 y\n")
        self.assertRejected("agent-governance.md: contains an em dash")

    def test_secret_in_steering(self):
        fake = "dapi" + "0123456789abcdef" * 2  # synthetic, nonfunctional
        p = self.steer("tech")
        p.write_text(p.read_text() + f"\ntoken {fake}\n")
        self.assertRejected("possible databricks token")

    def test_workflow_write_permission(self):
        self.wf("a.yml", "name: a\non:\n  push:\npermissions:\n  contents: write\njobs: {}\n")
        self.assertRejected("contents: write is not read-only")

    def test_workflow_job_level_write_permission(self):
        self.wf("a.yml", "name: a\non:\n  push:\npermissions:\n  contents: read\njobs:\n  j:\n    permissions:\n      pull-requests: write\n")
        self.assertRejected("pull-requests: write is not read-only")

    def test_workflow_write_all(self):
        self.wf("a.yml", "name: a\non:\n  push:\npermissions: write-all\njobs: {}\n")
        self.assertRejected("permissions must be read-only")

    def test_workflow_missing_permissions(self):
        self.wf("a.yml", "name: a\non:\n  push:\njobs: {}\n")
        self.assertRejected("missing top-level 'permissions:'")

    def test_pull_request_target(self):
        self.wf("a.yml", "name: a\non:\n  pull_request_target:\npermissions:\n  contents: read\njobs: {}\n")
        self.assertRejected("pull_request_target is not allowed")

    def test_extra_secret_reference(self):
        self.wf("a.yml", "name: a\non:\n  push:\npermissions:\n  contents: read\njobs:\n  j:\n    env:\n      K: ${{ secrets.DEPLOY_KEY }}\n")
        self.assertRejected("secrets.DEPLOY_KEY")

    def test_github_token_secret_allowed(self):
        self.wf("a.yml", "name: a\non:\n  push:\npermissions:\n  contents: read\njobs:\n  j:\n    env:\n      K: ${{ secrets.GITHUB_TOKEN }}\n")
        self.assertEqual(P.check_policy(self.root), [])

    def test_mysql_workflow_schedule_trigger(self):
        errs = []
        P.check_workflow_text("mysql.yml", GOOD_MYSQL_WF.replace("  workflow_dispatch:\n", "  workflow_dispatch:\n  schedule:\n    - cron: '0 0 * * *'\n"), errs)
        self.assertTrue(any("workflow_dispatch only" in e and "schedule" in e for e in errs), errs)

    def test_mysql_workflow_push_trigger(self):
        errs = []
        P.check_workflow_text("mysql.yml", GOOD_MYSQL_WF.replace("  workflow_dispatch:\n", "  push:\n"), errs)
        self.assertTrue(any("workflow_dispatch only" in e for e in errs), errs)

    def test_mysql_workflow_without_timeout(self):
        errs = []
        P.check_workflow_text("mysql.yml", GOOD_MYSQL_WF.replace("    timeout-minutes: 10\n", ""), errs)
        self.assertTrue(any("needs timeout-minutes" in e for e in errs), errs)

    def test_mysql_workflow_long_retention(self):
        errs = []
        P.check_workflow_text("mysql.yml", GOOD_MYSQL_WF.replace("retention-days: 3", "retention-days: 30"), errs)
        self.assertTrue(any("retention-days must be between" in e for e in errs), errs)

    def test_mysql_workflow_missing_retention(self):
        errs = []
        P.check_workflow_text("mysql.yml", GOOD_MYSQL_WF.replace("          retention-days: 3\n", ""), errs)
        self.assertTrue(any("needs retention-days" in e for e in errs), errs)

    def test_good_mysql_workflow_text_is_clean(self):
        errs = []
        P.check_workflow_text("mysql.yml", GOOD_MYSQL_WF, errs)
        self.assertEqual(errs, [])

    def test_active_mysql_workflow_rejected_even_if_well_formed(self):
        self.wf("mysql-benchmark.yml", GOOD_MYSQL_WF)
        self.assertRejected("no mysql workflow is approved for activation")

    def test_template_is_linted(self):
        p = self.root / P.WORKFLOW_TEMPLATE
        p.write_text(p.read_text().replace("workflow_dispatch:", "schedule:", 1))
        self.assertRejected("templates/mysql-benchmark-workflow.yml.template: mysql workflow must be workflow_dispatch only")

    def test_template_missing(self):
        (self.root / P.WORKFLOW_TEMPLATE).unlink()
        self.assertRejected("template missing")

    def test_sql_benchmark_template_labelled_executed(self):
        p = self.root / "templates" / "sql-benchmark.md"
        p.write_text(p.read_text().replace("status: not_started", "status: executed_unreviewed", 1))
        self.assertRejected("status must be not_started")

    def test_sql_benchmark_template_with_filled_result(self):
        p = self.root / "templates" / "sql-benchmark.md"
        p.write_text(p.read_text().replace("result_median_ms: null", "result_median_ms: 12", 1))
        self.assertRejected("result field result_median_ms must be empty")


class TestSqlCompanionRules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "catalog").mkdir()
        shutil.copy(REPO / "catalog" / "sql_companion.json", self.root / "catalog")
        self.recipes = json.loads((REPO / "catalog" / "recipes.json").read_text())["recipes"]
        self.data = json.loads((self.root / "catalog" / "sql_companion.json").read_text())

    def tearDown(self):
        self.tmp.cleanup()

    def errs(self):
        (self.root / "catalog" / "sql_companion.json").write_text(json.dumps(self.data))
        out = []
        V.check_sql_companion(self.root, self.recipes, out)
        return out

    def assertRejected(self, fragment):
        errs = self.errs()
        self.assertTrue(any(fragment in e for e in errs), f"{fragment!r} not in {errs}")

    def entry(self, rid="1.1"):
        return next(e for e in self.data["entries"] if e["recipe_id"] == rid)

    def test_seed_is_valid(self):
        self.assertEqual(self.errs(), [])

    def test_all_recipes_covered_and_none_executed(self):
        self.assertEqual(len(self.data["entries"]), 63)
        for e in self.data["entries"]:
            for t in ("databricks_sql", "mysql"):
                self.assertEqual(e[t]["execution_status"], "not_started")
                self.assertIsNone(e[t]["artifact_path"])

    def test_unknown_recipe_id(self):
        self.data["entries"][0]["recipe_id"] = "99.9"
        self.assertRejected("recipe_id not found")

    def test_duplicate_recipe_id(self):
        self.data["entries"].append(dict(self.data["entries"][0]))
        self.assertRejected("duplicate recipe_id")

    def test_missing_recipe_entry(self):
        self.data["entries"].pop()
        self.assertRejected("no entry for recipes")

    def test_invalid_applicability(self):
        self.entry()["mysql"]["applicability"] = "maybe"
        self.assertRejected("invalid applicability")

    def test_not_applicable_needs_rationale(self):
        self.entry()["mysql"]["applicability"] = "not_applicable"
        self.assertRejected("requires a rationale")

    def test_executed_without_evidence(self):
        e = self.entry()["mysql"]
        e.update(applicability="applicable", artifact_path="sql/mysql/chapter-01/q.sql", execution_status="executed_unreviewed")
        self.assertRejected("requires non-empty evidence")

    def test_executed_with_missing_evidence_file(self):
        e = self.entry()["mysql"]
        e.update(applicability="applicable", artifact_path="sql/mysql/chapter-01/q.sql",
                 execution_status="executed_unreviewed", evidence=["evidence/sql/nope.md"])
        self.assertRejected("evidence file not found")

    def test_evidence_path_traversal(self):
        e = self.entry()["mysql"]
        e.update(applicability="applicable", artifact_path="sql/mysql/chapter-01/q.sql",
                 execution_status="executed_unreviewed", evidence=["../outside.md"])
        self.assertRejected("unsafe evidence path")

    def test_unresolved_cannot_be_executed(self):
        self.entry()["mysql"]["execution_status"] = "verified"
        self.assertRejected("must have execution_status not_started")

    def test_applicable_needs_planned_layout_path(self):
        e = self.entry()["mysql"]
        e["applicability"] = "applicable"
        self.assertRejected("requires artifact_path under sql/mysql/chapter-NN/")
        e["artifact_path"] = "../sql/mysql/chapter-01/q.sql"
        self.assertRejected("requires artifact_path under sql/mysql/chapter-NN/")

    def test_observed_version_needs_evidence(self):
        self.entry()["mysql"]["observed_version"] = "8.0.99"
        self.assertRejected("observed_version requires evidence")

    def test_wrong_target_version(self):
        self.entry()["mysql"]["target_version"] = "5.7"
        self.assertRejected("target_version must be '8.0'")

    def test_verified_needs_reviewer(self):
        d = self.entry()["databricks_sql"]
        d.update(applicability="applicable", artifact_path="sql/databricks/chapter-01/q.sql", execution_status="verified")
        self.assertRejected("verified requires reviewed_by")


if __name__ == "__main__":
    unittest.main()
