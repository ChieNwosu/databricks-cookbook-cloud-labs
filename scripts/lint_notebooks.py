#!/usr/bin/env python3
"""Structural lint for Databricks source-format notebooks under labs/.

Usage: python scripts/lint_notebooks.py [--root PATH] [FILE ...]
Checks the header, cell separators, that Python cells parse (MAGIC cells are
skipped) and that forbidden patterns are absent. It does not run any notebook.
"""
import argparse
import ast
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parent
HEADER = "# Databricks notebook source"
SEPARATOR = "# COMMAND ----------"
FORBIDDEN = [
    ("spark.master config", re.compile(r"spark\.master")),
    ("sparkContext use", re.compile(r"sparkContext")),
    ("DBFS root path", re.compile(r"dbfs:/|/dbfs/|/FileStore")),
    ("databricks token", re.compile(r"dapi[0-9a-f]{32}")),
    ("aws access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("bearer token", re.compile(r"Bearer [A-Za-z0-9._~+/=-]{20,}")),
    ("hard-coded secret", re.compile(r"(?i)\b(?:password|token|secret|api_key)\s*=\s*[\"'][^\"']+[\"']")),
    ("dbutils.secrets use", re.compile(r"dbutils\.secrets")),
]


def lint_text(text, name="notebook"):
    """Return a list of error strings for one notebook's text."""
    errors = []
    lines = text.split("\n")
    if lines[0].strip() != HEADER:
        errors.append(f"{name}: first line must be '{HEADER}'")
    cells, current = [], []
    for line in lines[1:]:
        if line.strip() == SEPARATOR:
            cells.append(current)
            current = []
        else:
            current.append(line)
    cells.append(current)
    if len(cells) < 2:
        errors.append(f"{name}: expected at least one '{SEPARATOR}' separator")
    for i, cell in enumerate(cells, start=1):
        body = [ln for ln in cell if ln.strip()]
        if not body:
            errors.append(f"{name}: cell {i} is empty")
            continue
        if all(ln.startswith("# MAGIC") for ln in body):
            continue
        if any(ln.startswith("# MAGIC") for ln in body):
            errors.append(f"{name}: cell {i} mixes MAGIC and Python lines")
            continue
        try:
            ast.parse("\n".join(cell))
        except SyntaxError as e:
            errors.append(f"{name}: cell {i} does not parse (line {e.lineno}: {e.msg})")
    for n, line in enumerate(lines, start=1):
        for label, rx in FORBIDDEN:
            if rx.search(line):
                errors.append(f"{name}:{n}: forbidden pattern: {label}")
    if not any(ln.startswith("# MAGIC %md") for ln in lines):
        errors.append(f"{name}: no markdown cell found")
    return errors


def lint_file(path, root=None):
    p = Path(path)
    name = str(p.relative_to(root)) if root and p.is_absolute() and root in p.parents else str(p)
    return lint_text(p.read_text(encoding="utf-8"), name)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("files", nargs="*")
    args = ap.parse_args(argv)
    root = Path(args.root)
    files = [Path(f) for f in args.files] or sorted((root / "labs").rglob("*.py"))
    errors = []
    for f in files:
        errors += lint_file(f, root)
    for e in errors:
        print(f"ERROR: {e}")
    print(f"{len(files)} notebook(s) checked, {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
