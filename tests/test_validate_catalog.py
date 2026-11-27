import copy
import importlib.util
import json
import re
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
        shutil.copy(REPO / "docs" / "first-notebook.md", self.root / "docs" / "first-notebook.md")  # lab guide
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
        self.mutate_recipes(lambda rs: rs[1].update(  # recipe without a note, so no note must agree
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
        fake = "dapi" + "0123456789abcdef" * 2
        (self.root / "docs" / "leak.md").write_text(f"value {fake}")
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


class TestHardening(CatalogCase):
    """Negative tests for the Phase 0 review findings. Secret values are synthetic and built by concatenation."""

    def evidence_file(self, name="1.1.md"):
        (self.root / "evidence").mkdir(exist_ok=True)
        (self.root / "evidence" / name).write_text("ok")
        return f"evidence/{name}"

    # finding 1
    def test_executed_unreviewed_without_evidence(self):
        self.mutate_recipes(lambda rs: rs[0].update(status="executed_unreviewed"))
        self.assertError("executed_unreviewed requires non-empty 'evidence'")

    def test_executed_unreviewed_with_evidence_passes(self):
        ev = self.evidence_file()
        self.mutate_recipes(lambda rs: rs[1].update(status="executed_unreviewed", evidence=[ev]))
        errs, _ = self.errors()
        self.assertFalse([e for e in errs if "recipe 1.2" in e and "evidence" in e], errs)

    # finding 2
    def _evidence_case(self, ev, fragment, status="executed_unreviewed"):
        self.mutate_recipes(lambda rs: rs[1].update(status=status, evidence=[ev]))
        self.assertError(fragment)

    def test_evidence_traversal(self):
        self._evidence_case("evidence/../catalog/recipes.json", "unsafe evidence path")

    def test_evidence_absolute(self):
        self._evidence_case("/etc/hostname", "absolute paths are not allowed")

    def test_evidence_outside_evidence_dir(self):
        self._evidence_case("catalog/recipes.json", "must resolve inside evidence/")

    def test_evidence_missing_file(self):
        self._evidence_case("evidence/nope.md", "evidence file not found")

    def test_evidence_symlink_escape(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        (Path(outside.name) / "x.md").write_text("x")
        (self.root / "evidence").mkdir()
        (self.root / "evidence" / "link.md").symlink_to(Path(outside.name) / "x.md")
        self._evidence_case("evidence/link.md", "unsafe evidence path")
        self.assertError("unsafe symlink")

    def test_lab_evidence_missing_file(self):
        data = self.read("labs.json")
        data["labs"][0].update(status="executed_unreviewed", evidence=["evidence/nope.md"])
        self.write("labs.json", data)
        self.assertError("lab 1.0: evidence file not found")

    def test_lab_evidence_traversal(self):
        data = self.read("labs.json")
        data["labs"][0].update(status="executed_unreviewed", evidence=["../outside.md"])
        self.write("labs.json", data)
        self.assertError("lab 1.0: unsafe evidence path")

    def test_lab_path_and_guide_unsafe(self):
        data = self.read("labs.json")
        data["labs"][0].update(path="../x.py", guide="/etc/passwd")
        self.write("labs.json", data)
        self.assertError("lab 1.0: unsafe path")
        self.assertError("lab 1.0: unsafe guide")

    # finding 3
    def _note(self, **changes):
        p = self.root / "notes" / "chapter-01" / "1.1-read-csv-data.md"
        text = p.read_text()
        for k, v in changes.items():
            text = re.sub(rf"(?m)^{k}: .*$", f"{k}: {v}", text)
        p.write_text(text)

    def test_note_status_disagrees(self):
        self._note(status="drafted")
        self.assertError("front matter status 'drafted' disagrees")

    def test_note_compatibility_disagrees(self):
        self._note(compatibility="native")
        self.assertError("front matter compatibility 'native' disagrees")

    def test_note_title_and_id_disagree(self):
        self._note(title='"Other"', recipe_id='"9.9"')
        self.assertError("front matter title 'Other' disagrees")
        self.assertError("front matter recipe_id '9.9' disagrees")

    def test_note_without_catalog_recipe(self):
        src = self.root / "notes" / "chapter-01" / "1.1-read-csv-data.md"
        (self.root / "notes" / "chapter-01" / "orphan.md").write_text(src.read_text())
        self.assertError("note has no catalog recipe")

    def test_executed_note_requires_matching_evidence_links(self):
        ev = self.evidence_file()
        self.mutate_recipes(lambda rs: rs[0].update(status="executed_unreviewed", evidence=[ev]))
        self._note(status="executed_unreviewed")
        self.assertError("requires non-empty evidence_links")

    # finding 7
    def test_alt_env_flag_false_without_marker(self):
        def f(rs):
            r = next(r for r in rs if r["id"] == "6.1")
            r.pop("classification_unresolved")
        self.mutate_recipes(f)
        self.assertError("needs a classification_unresolved record")

    def test_incomplete_unresolved_marker(self):
        def f(rs):
            next(r for r in rs if r["id"] == "6.1")["classification_unresolved"]["source"] = ""
        self.mutate_recipes(f)
        self.assertError("classification_unresolved needs non-empty")

    def test_requires_alt_env_true_with_native(self):
        self.mutate_recipes(lambda rs: rs[0].update(compatibility="native", requires_alt_env=True))
        self.assertError("requires_alt_env is true but compatibility")

    def test_repo_recipe_6_1_unresolved_and_matrix(self):
        recipes = json.loads((REPO / "catalog" / "recipes.json").read_text())["recipes"]
        r61 = next(r for r in recipes if r["id"] == "6.1")
        self.assertEqual(r61["compatibility"], "alt_env")
        self.assertFalse(r61["requires_alt_env"])
        for k in ("question", "source", "retrieved"):
            self.assertTrue(r61["classification_unresolved"][k])
        self.assertRegex((REPO / "docs" / "compatibility-matrix.md").read_text(), r"\| 6\.1 \|[^\n]*\| unresolved \|")

    # finding 5 and 8
    def test_repo_recipe_1_1_not_started(self):
        recipes = json.loads((REPO / "catalog" / "recipes.json").read_text())["recipes"]
        r11 = next(r for r in recipes if r["id"] == "1.1")
        self.assertEqual(r11["status"], "not_started")
        self.assertIn("status: not_started", (REPO / r11["note_path"]).read_text())

    def test_repo_coverage_numbers_unchanged(self):
        gaps = json.loads((REPO / "catalog" / "coverage_gaps.json").read_text())
        recipes = json.loads((REPO / "catalog" / "recipes.json").read_text())["recipes"]
        self.assertEqual((gaps["expected_total"], gaps["evidenced_count"], len(recipes)), (72, 63, 63))

    # finding 6
    def test_each_new_secret_pattern(self):
        samples = {
            "github token": "gh" + "p_" + "A1" * 18,
            "github token ": "github" + "_pat_" + "A1b2C3" * 5,
            "slack token": "xo" + "xb-" + "1234567890-abcdefghij",
            "google api key": "AI" + "za" + "A1b2C3d4E5" * 3 + "xyz12",
            "jwt-like token": "ey" + "Jhbgci0.ey" + "Jzdwiy0.sig_part",
            "aws secret key assignment": "aws_secret" + "_access_key = " + "A" * 40,
            "azure storage account key": "Account" + "Key=" + "QUJD" * 6,
            "password in url": "mysql://" + "app:" + "hunter2" + "@db.internal/x",
            "private key": "-----BEGIN " + "OPENSSH PRIVATE KEY-----",
            "email address": "someone" + "@" + "corp-mail.test",
            "databricks workspace hostname": "adb-" + "1234567890123456.7.azure" + "databricks.net",
            "databricks workspace hostname ": "dbc-" + "a1b2c3d4-e5f6.cloud" + ".databricks.com",
        }
        for label, value in samples.items():
            with self.subTest(label=label):
                p = self.root / "docs" / "sample.md"
                p.write_text("x " + value + " y")
                errs, _ = self.errors()
                self.assertTrue(any(f"possible {label.strip()}" in e for e in errs), (label, errs))
        p.unlink()

    def test_generic_secret_assignment_in_code_and_sql_and_yaml(self):
        for name in ("a.py", "b.sql", "c.yml"):
            with self.subTest(name=name):
                (self.root / "docs" / name).write_text("pass" + 'word = "' + "hunter2" + '"\n')
                self.assertError("possible hard-coded secret")
                (self.root / "docs" / name).unlink()

    def test_allowlisted_email_passes(self):
        (self.root / "docs" / "e.md").write_text("contact someone" + "@" + "example.com")
        errs, _ = self.errors()
        self.assertEqual(errs, [])

    def test_secret_in_suffixless_file(self):
        (self.root / "docs" / "NOTES").write_text("x " + "AKIA" + "ABCDEFGHIJKLMNOP")
        self.assertError("possible aws access key")

    def test_unsafe_symlink(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        (Path(outside.name) / "t.txt").write_text("dapi" + "0" * 32)
        (self.root / "docs" / "link.txt").symlink_to(Path(outside.name) / "t.txt")
        errs, _ = self.errors()
        self.assertTrue(any("unsafe symlink" in e for e in errs), errs)
        self.assertFalse(any("possible databricks token" in e for e in errs), "must not follow symlink")


class TestFrontMatter(unittest.TestCase):
    def test_parse(self):
        fm = V.parse_front_matter('---\na: "x"\nb: null\nc: []\nd:\n  - 1\n  - y\ne: [p, q]\n---\nbody')
        self.assertEqual(fm, {"a": "x", "b": None, "c": [], "d": [1, "y"], "e": ["p", "q"]})

    def test_missing_close(self):
        with self.assertRaises(ValueError):
            V.parse_front_matter("---\na: 1\n")


if __name__ == "__main__":
    unittest.main()
