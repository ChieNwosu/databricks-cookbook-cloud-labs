import copy
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


V = _load("validate_catalog")
G = _load("generate_docs")


class CatalogCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(REPO / "catalog", self.root / "catalog")
        shutil.copytree(REPO / "templates", self.root / "templates")
        shutil.copytree(REPO / "notes", self.root / "notes")
        shutil.copytree(REPO / "labs", self.root / "labs")
        (self.root / "docs").mkdir()
        self.regen()

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, name):
        return json.loads((self.root / "catalog" / name).read_text())

    def write(self, name, data):
        (self.root / "catalog" / name).write_text(json.dumps(data, indent=2))

    def regen(self):
        """Regenerate docs for the temp root so only the injected fault is reported."""
        old = G.ROOT
        G.ROOT = self.root
        try:
            (self.root / "docs" / "coverage-ledger.md").write_text(G.ledger(), encoding="utf-8")
            (self.root / "docs" / "compatibility-matrix.md").write_text(G.matrix(), encoding="utf-8")
        finally:
            G.ROOT = old

    def mutate_recipes(self, fn):
        data = self.read("recipes.json")
        fn(data["recipes"])
        self.write("recipes.json", data)
        try:
            self.regen()
        except Exception:
            pass

    def errors(self, strict=False):
        return V.validate(self.root, strict)

    def assertError(self, fragment, strict=False):
        errs, _ = self.errors(strict)
        self.assertTrue(any(fragment in e for e in errs), f"{fragment!r} not in {errs}")


class TestValidator(CatalogCase):
    def test_good_data_passes_with_coverage_warning(self):
        errs, warns = self.errors()
        self.assertEqual(errs, [])
        self.assertTrue(any("63 evidenced" in w for w in warns))

    def test_repo_itself_passes(self):
        errs, _ = V.validate(REPO)
        self.assertEqual(errs, [])

    def test_no_recipe_verified_in_repo(self):
        recipes = json.loads((REPO / "catalog" / "recipes.json").read_text())["recipes"]
        self.assertFalse([r["id"] for r in recipes if r["status"] == "verified"])

    def test_strict_fails_on_gap(self):
        self.assertError("coverage:", strict=True)
        errs, warns = self.errors(strict=True)
        self.assertEqual(warns, [])

    def test_duplicate_id(self):
        self.mutate_recipes(lambda rs: rs.append(copy.deepcopy(rs[0])))
        self.assertError("duplicate id")

    def test_bad_enum_status(self):
        self.mutate_recipes(lambda rs: rs[0].update(status="done"))
        self.assertError("invalid status")

    def test_bad_enum_compatibility(self):
        self.mutate_recipes(lambda rs: rs[0].update(compatibility="magic"))
        self.assertError("invalid compatibility")

    def test_id_chapter_mismatch(self):
        self.mutate_recipes(lambda rs: rs[0].update(chapter=2))
        self.assertError("does not match chapter")

    def test_verified_without_evidence(self):
        self.mutate_recipes(lambda rs: rs[0].update(status="verified"))
        errs, _ = self.errors()
        for k in ("evidence", "reviewed_by", "databricks_runtime", "last_verified"):
            self.assertTrue(any(f"verified requires non-empty '{k}'" in e for e in errs), k)

    def test_verified_with_missing_evidence_file(self):
        self.mutate_recipes(lambda rs: rs[0].update(
            status="verified", evidence=["evidence/nope.md"], reviewed_by="x",
            databricks_runtime="16.4", last_verified="2026-01-01"))
        self.assertError("evidence file not found")

    def test_verified_with_real_evidence_passes(self):
        (self.root / "evidence").mkdir()
        (self.root / "evidence" / "1.1.md").write_text("ok")
        self.mutate_recipes(lambda rs: rs[0].update(
            status="verified", evidence=["evidence/1.1.md"], reviewed_by="x",
            databricks_runtime="16.4", last_verified="2026-01-01"))
        errs, _ = self.errors()
        self.assertEqual(errs, [])

    def test_alt_env_verified_without_evidence(self):
        def f(rs):
            r = next(r for r in rs if r["compatibility"] == "alt_env")
            r.update(status="verified")
        self.mutate_recipes(f)
        self.assertError("alt_env recipe cannot be verified without evidence")

    def test_missing_referenced_file(self):
        self.mutate_recipes(lambda rs: rs[0].update(lab_path="labs/chapter-01/missing.py"))
        self.assertError("lab_path not found")

    def test_lab_missing_file(self):
        data = self.read("labs.json")
        data["labs"][0]["path"] = "labs/chapter-01/missing.py"
        self.write("labs.json", data)
        self.assertError("lab 1.0: path not found")

    def test_lab_executed_without_evidence(self):
        data = self.read("labs.json")
        data["labs"][0]["status"] = "executed_unreviewed"
        self.write("labs.json", data)
        self.assertError("requires evidence")

    def test_no_lab_verified_in_repo(self):
        self.assertTrue(all(l["status"] != "verified" for l in self.read("labs.json")["labs"]))

    def test_secret_pattern(self):
        token = "dapi" + "0123456789abcdef" * 2
        (self.root / "docs" / "leak.md").write_text(f"token {token}")
        self.assertError("possible databricks token")

    def test_private_key_pattern(self):
        (self.root / "docs" / "k.txt").write_text("-----BEGIN " + "RSA PRIVATE KEY-----")
        self.assertError("possible private key")

    def test_wrong_chapter_count(self):
        data = self.read("chapters.json")
        data["chapters"].pop()
        self.write("chapters.json", data)
        self.assertError("expected 11 chapters")

    def test_docs_out_of_sync(self):
        (self.root / "docs" / "coverage-ledger.md").write_text("stale")
        self.assertError("out of date")

    def test_bad_front_matter(self):
        (self.root / "templates" / "recipe-note.md").write_text("---\nrecipe_id: \"1.1\"\n---\n")
        self.assertError("front matter missing keys")

    def test_versions_observed_without_evidence(self):
        data = self.read("versions.json")
        data["free_edition"]["databricks_runtime"] = "16.4"
        self.write("versions.json", data)
        self.assertError("require observed_on and evidence")


class TestFrontMatter(unittest.TestCase):
    def test_parse(self):
        fm = V.parse_front_matter('---\na: "x"\nb: null\nc: []\nd:\n  - 1\n  - y\ne: [p, q]\n---\nbody')
        self.assertEqual(fm, {"a": "x", "b": None, "c": [], "d": [1, "y"], "e": ["p", "q"]})

    def test_missing_close(self):
        with self.assertRaises(ValueError):
            V.parse_front_matter("---\na: 1\n")


if __name__ == "__main__":
    unittest.main()
