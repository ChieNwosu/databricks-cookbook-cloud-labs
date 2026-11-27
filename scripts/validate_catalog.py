#!/usr/bin/env python3
"""Validate catalog/*.json, notes, templates and docs.

Usage: python scripts/validate_catalog.py [--strict] [--root PATH]
Errors exit 1. The coverage gap against the expected recipe total is a warning
unless --strict is given.
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parent
STATUSES = ["not_started", "drafted", "executed_unreviewed", "verified"]
CLASSES = ["native", "adapted", "alt_env"]
ARTIFACT_TYPES = ["notebook", "sql_notebook", "sql_pipeline", "job_yaml", "bundle"]
EXPECTED_CHAPTERS = 11
NOTE_KEYS = [
    "recipe_id", "chapter", "title", "compatibility", "status", "source_ref", "provenance",
    "databricks_runtime", "spark_version", "delta_version", "last_verified", "reviewer",
    "evidence_links", "tags", "llm_summary",
]
EVIDENCE_KEYS = ["recipe_id", "run_url", "screenshot_path", "date", "databricks_runtime", "reviewer", "result"]
SECRET_PATTERNS = [
    ("databricks token", re.compile(r"dapi[0-9a-f]{32}")),
    ("aws access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("bearer token", re.compile(r"Bearer [A-Za-z0-9._~+/=-]{20,}")),
    ("private key", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
]
SKIP_DIRS = {".git", "__pycache__", ".agents", "node_modules"}
TEXT_SUFFIXES = {".md", ".json", ".py", ".yml", ".yaml", ".txt", ".sql", ".ipynb", ".toml", ".cfg", ".ini", ".sh", ""}


def parse_front_matter(text):
    """Parse a restricted YAML front matter block: scalars, [] and '- item' lists."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening ---")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise ValueError("missing closing ---")
    data = {}
    key = None
    for n, line in enumerate(lines[1:end], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") or line.startswith("- "):
            if key is None or not isinstance(data.get(key), list):
                raise ValueError(f"line {n}: list item without list key")
            data[key].append(_scalar(line.split("- ", 1)[1], n))
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if not m:
            raise ValueError(f"line {n}: cannot parse")
        key, val = m.group(1), m.group(2).strip()
        if key in data:
            raise ValueError(f"line {n}: duplicate key {key}")
        if val == "":
            data[key] = []
        elif val == "[]":
            data[key] = []
        elif val.startswith("["):
            inner = val[1:-1].strip() if val.endswith("]") else None
            if inner is None:
                raise ValueError(f"line {n}: unterminated list")
            data[key] = [_scalar(x.strip(), n) for x in inner.split(",")] if inner else []
        else:
            data[key] = _scalar(val, n)
    return data


def _scalar(val, n):
    val = val.strip()
    if val in ("null", "~"):
        return None
    if val in ("true", "false"):
        return val == "true"
    if re.fullmatch(r"-?\d+", val):
        return int(val)
    if val.startswith('"'):
        if len(val) < 2 or not val.endswith('"'):
            raise ValueError(f"line {n}: unterminated string")
        return val[1:-1]
    if val.startswith("'"):
        if len(val) < 2 or not val.endswith("'"):
            raise ValueError(f"line {n}: unterminated string")
        return val[1:-1]
    return val


def _load_json(root, name, errors):
    path = root / "catalog" / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"catalog/{name}: file missing")
    except json.JSONDecodeError as e:
        errors.append(f"catalog/{name}: invalid JSON ({e})")
    return None


def _nonempty(v):
    return v is not None and v != "" and v != []


def check_chapters(data, errors):
    if data is None:
        return set()
    chapters = data.get("chapters") if isinstance(data, dict) else None
    if not isinstance(chapters, list):
        errors.append("chapters.json: 'chapters' must be a list")
        return set()
    if len(chapters) != EXPECTED_CHAPTERS:
        errors.append(f"chapters.json: expected {EXPECTED_CHAPTERS} chapters, found {len(chapters)}")
    ids = []
    for c in chapters:
        for k in ("id", "title", "theme", "upstream_folder"):
            if not _nonempty(c.get(k)):
                errors.append(f"chapters.json: chapter {c.get('id')} missing '{k}'")
        ids.append(c.get("id"))
    if len(set(ids)) != len(ids):
        errors.append("chapters.json: duplicate chapter id")
    return set(ids)


def check_recipes(root, data, chapter_ids, errors):
    if data is None:
        return []
    recipes = data.get("recipes") if isinstance(data, dict) else None
    if not isinstance(recipes, list):
        errors.append("recipes.json: 'recipes' must be a list")
        return []
    seen = set()
    for r in recipes:
        rid = r.get("id")
        tag = f"recipe {rid}"
        for k in ("id", "chapter", "slug", "title", "upstream_path", "upstream_url", "primary_artifact_type",
                  "compatibility", "adaptation_notes", "requires_alt_env", "dependencies", "status", "evidence",
                  "reviewed_by", "databricks_runtime", "last_verified"):
            if k not in r:
                errors.append(f"{tag}: missing field '{k}'")
        if rid in seen:
            errors.append(f"{tag}: duplicate id")
        seen.add(rid)
        ch = r.get("chapter")
        if ch not in chapter_ids:
            errors.append(f"{tag}: unknown chapter {ch}")
        if not isinstance(rid, str) or not re.fullmatch(r"\d+\.\d+", rid) or rid.split(".")[0] != str(ch):
            errors.append(f"{tag}: id does not match chapter {ch}")
        if r.get("compatibility") not in CLASSES:
            errors.append(f"{tag}: invalid compatibility {r.get('compatibility')!r}")
        if r.get("status") not in STATUSES:
            errors.append(f"{tag}: invalid status {r.get('status')!r}")
        if r.get("primary_artifact_type") not in ARTIFACT_TYPES:
            errors.append(f"{tag}: invalid primary_artifact_type {r.get('primary_artifact_type')!r}")
        if not isinstance(r.get("requires_alt_env"), bool):
            errors.append(f"{tag}: requires_alt_env must be boolean")
        if not isinstance(r.get("evidence", []), list):
            errors.append(f"{tag}: evidence must be a list")
        if r.get("status") == "verified":
            for k in ("evidence", "reviewed_by", "databricks_runtime", "last_verified"):
                if not _nonempty(r.get(k)):
                    errors.append(f"{tag}: verified requires non-empty '{k}'")
            for ev in r.get("evidence") or []:
                if not (root / ev).is_file():
                    errors.append(f"{tag}: evidence file not found: {ev}")
        elif r.get("status") == "not_started" and r.get("evidence"):
            errors.append(f"{tag}: not_started recipe must not list evidence")
        if r.get("compatibility") == "alt_env" and r.get("status") == "verified" and not r.get("evidence"):
            errors.append(f"{tag}: alt_env recipe cannot be verified without evidence")
        for k in ("lab_path", "note_path"):
            if r.get(k) and not (root / r[k]).is_file():
                errors.append(f"{tag}: {k} not found: {r[k]}")
    return recipes


def check_compatibility(data, errors):
    if data is None:
        return
    classes = data.get("classes") if isinstance(data, dict) else None
    if not isinstance(classes, dict) or sorted(classes) != sorted(CLASSES):
        errors.append(f"compatibility.json: classes must be exactly {CLASSES}")
    lim = data.get("free_edition_limitations") if isinstance(data, dict) else None
    if not isinstance(lim, dict) or not all(_nonempty(lim.get(k)) for k in ("source", "retrieved", "summary")):
        errors.append("compatibility.json: free_edition_limitations needs source, retrieved, summary")
    if not _nonempty(data.get("classification_status") if isinstance(data, dict) else None):
        errors.append("compatibility.json: classification_status missing")


def check_labs(root, data, errors):
    labs = data.get("labs") if isinstance(data, dict) else None
    if not isinstance(labs, list):
        if data is not None:
            errors.append("labs.json: 'labs' must be a list")
        return
    for lab in labs:
        tag = f"lab {lab.get('id')}"
        if not (root / str(lab.get("path", ""))).is_file():
            errors.append(f"{tag}: path not found: {lab.get('path')}")
        if lab.get("status") not in STATUSES:
            errors.append(f"{tag}: invalid status {lab.get('status')!r}")
        if lab.get("compatibility") not in CLASSES:
            errors.append(f"{tag}: invalid compatibility {lab.get('compatibility')!r}")
        if lab.get("status") in ("executed_unreviewed", "verified") and not lab.get("evidence"):
            errors.append(f"{tag}: {lab.get('status')} requires evidence")
        if lab.get("status") == "verified":
            for k in ("reviewed_by", "databricks_runtime", "last_verified"):
                if not _nonempty(lab.get(k)):
                    errors.append(f"{tag}: verified requires non-empty '{k}'")


def check_versions(data, errors):
    if data is None:
        return
    up = data.get("upstream") if isinstance(data, dict) else None
    fe = data.get("free_edition") if isinstance(data, dict) else None
    if not isinstance(up, dict) or not isinstance(up.get("components"), dict):
        errors.append("versions.json: upstream.components missing")
    else:
        if not re.fullmatch(r"[0-9a-f]{40}", str(up.get("analysed_tree_sha", ""))):
            errors.append("versions.json: upstream.analysed_tree_sha must be a 40 char hex sha")
        for name in ("spark", "kafka"):
            comp = up["components"].get(name)
            if not isinstance(comp, dict) or not _nonempty(comp.get("version")):
                errors.append(f"versions.json: upstream component '{name}' needs a version")
    if not isinstance(fe, dict):
        errors.append("versions.json: free_edition missing")
    else:
        for k in ("databricks_runtime", "spark_version", "delta_version", "observed_on", "observed_by", "evidence"):
            if k not in fe:
                errors.append(f"versions.json: free_edition missing '{k}'")
        observed = [fe.get(k) for k in ("databricks_runtime", "spark_version", "delta_version")]
        if any(_nonempty(v) for v in observed) and not (_nonempty(fe.get("observed_on")) and _nonempty(fe.get("evidence"))):
            errors.append("versions.json: observed free_edition versions require observed_on and evidence")
    if not isinstance(data.get("drift_log"), list):
        errors.append("versions.json: drift_log must be a list")


def check_front_matter_files(root, errors):
    targets = []
    for rel, keys in (("templates/recipe-note.md", NOTE_KEYS), ("templates/evidence-record.md", EVIDENCE_KEYS)):
        targets.append((root / rel, keys, True))
    notes = root / "notes"
    if notes.is_dir():
        targets += [(p, NOTE_KEYS, False) for p in sorted(notes.rglob("*.md"))]
    for path, keys, required in targets:
        rel = path.relative_to(root)
        if not path.is_file():
            if required:
                errors.append(f"{rel}: file missing")
            continue
        try:
            fm = parse_front_matter(path.read_text(encoding="utf-8"))
        except ValueError as e:
            errors.append(f"{rel}: front matter error: {e}")
            continue
        missing = [k for k in keys if k not in fm]
        if missing:
            errors.append(f"{rel}: front matter missing keys {missing}")
            continue
        if keys is NOTE_KEYS:
            if fm["status"] not in STATUSES:
                errors.append(f"{rel}: invalid status {fm['status']!r}")
            if fm["compatibility"] not in CLASSES:
                errors.append(f"{rel}: invalid compatibility {fm['compatibility']!r}")
            if fm["status"] == "verified":
                for k in ("evidence_links", "reviewer", "databricks_runtime", "last_verified"):
                    if not _nonempty(fm[k]):
                        errors.append(f"{rel}: verified requires non-empty '{k}'")


def check_docs_in_sync(root, errors):
    gen = root / "scripts" / "generate_docs.py"
    if not gen.is_file():
        gen = HERE / "generate_docs.py"
    try:
        spec = importlib.util.spec_from_file_location("generate_docs_for_check", gen)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.ROOT = root
        expected = {"docs/coverage-ledger.md": mod.ledger(), "docs/compatibility-matrix.md": mod.matrix()}
    except Exception as e:  # catalog problems are reported by other checks
        errors.append(f"docs sync: could not generate docs ({type(e).__name__}: {e})")
        return
    for rel, text in expected.items():
        p = root / rel
        if not p.is_file() or p.read_text(encoding="utf-8") != text:
            errors.append(f"{rel}: out of date, run python scripts/generate_docs.py")


def iter_text_files(root):
    for p in sorted(root.rglob("*")):
        if not p.is_file() or any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        if p.suffix.lower() in TEXT_SUFFIXES:
            yield p


def check_secrets(root, errors):
    for p in iter_text_files(root):
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, rx in SECRET_PATTERNS:
            if rx.search(text):
                errors.append(f"{p.relative_to(root)}: possible {label}")


def validate(root, strict=False):
    """Return (errors, warnings)."""
    root = Path(root)
    errors, warnings = [], []
    chapter_ids = check_chapters(_load_json(root, "chapters.json", errors), errors)
    recipes = check_recipes(root, _load_json(root, "recipes.json", errors), chapter_ids, errors)
    check_compatibility(_load_json(root, "compatibility.json", errors), errors)
    check_versions(_load_json(root, "versions.json", errors), errors)
    if (root / "catalog" / "labs.json").exists():
        check_labs(root, _load_json(root, "labs.json", errors), errors)
    gaps = _load_json(root, "coverage_gaps.json", errors)
    if gaps is not None and recipes:
        expected = gaps.get("expected_total")
        if gaps.get("evidenced_count") != len(recipes):
            errors.append(f"coverage_gaps.json: evidenced_count {gaps.get('evidenced_count')} != {len(recipes)} recipes")
        if isinstance(expected, int) and len(recipes) < expected:
            msg = f"coverage: {len(recipes)} evidenced recipes vs {expected} expected ({expected - len(recipes)} unaccounted)"
            (errors if strict else warnings).append(msg)
    check_front_matter_files(root, errors)
    check_docs_in_sync(root, errors)
    check_secrets(root, errors)
    return errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true", help="fail on coverage gap")
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    args = ap.parse_args(argv)
    errors, warnings = validate(args.root, args.strict)
    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
