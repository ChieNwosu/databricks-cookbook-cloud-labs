#!/usr/bin/env python3
"""Deterministic repository policy checks (stdlib only).

Usage: python scripts/check_policy.py [--root PATH]

These checks enforce what code can enforce: steering file presence and frontmatter,
no em dashes in policy docs, no secret-like text in steering, and a restrictive shape
for GitHub workflows and the inactive MySQL workflow template. They cannot prove that
an agent follows the steering, that steering is loaded, that prose is truthful or that
a human run really happened. See docs/agent-governance.md.
"""
import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import secret_patterns  # noqa: E402
import validate_catalog  # noqa: E402

DEFAULT_ROOT = HERE.parent
STEERING_DIR = ".kiro/steering"
STEERING_FILES = [
    "product", "tech", "structure", "input-guardrails", "output-guardrails",
    "tool-calling-guardrails", "learning-workflow", "sql-performance", "knowledge-governance",
]
ALWAYS_FILES = [n for n in STEERING_FILES if n != "sql-performance"]
INCLUSION_VALUES = {"always", "fileMatch", "manual", "auto"}
EM_DASH = "\u2014"
MAX_RETENTION_DAYS = 7
WORKFLOW_TEMPLATE = "templates/mysql-benchmark-workflow.yml.template"
# No MySQL workflow is approved for activation in Phase 0.1. Adding a name here is a human decision.
APPROVED_ACTIVE_MYSQL_WORKFLOWS = frozenset()
BAD_TRIGGERS = {"push", "pull_request", "pull_request_target", "schedule", "workflow_run", "issues",
                "issue_comment", "release", "repository_dispatch"}
SQL_EXEC_STATUSES = {"executed_unreviewed", "verified"}


def _read(path):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def check_steering(root, errors):
    base = Path(root) / STEERING_DIR
    for name in STEERING_FILES:
        rel = f"{STEERING_DIR}/{name}.md"
        text = _read(base / f"{name}.md")
        if text is None:
            errors.append(f"{rel}: steering file missing")
            continue
        try:
            fm = validate_catalog.parse_front_matter(text)
        except ValueError as e:
            errors.append(f"{rel}: invalid frontmatter: {e}")
            continue
        inc = fm.get("inclusion")
        if inc not in INCLUSION_VALUES:
            errors.append(f"{rel}: invalid inclusion {inc!r}, expected one of {sorted(INCLUSION_VALUES)}")
            continue
        if name in ALWAYS_FILES and inc != "always":
            errors.append(f"{rel}: core steering must use 'inclusion: always', found {inc!r}")
        if inc == "fileMatch" and not fm.get("fileMatchPattern"):
            errors.append(f"{rel}: fileMatch inclusion needs fileMatchPattern")
        if inc == "auto" and not (fm.get("name") and fm.get("description")):
            errors.append(f"{rel}: auto inclusion needs name and description")
        for label in secret_patterns.scan_text(text, ".md"):
            errors.append(f"{rel}: possible {label}")


def policy_text_files(root):
    root = Path(root)
    out = []
    for sub in (STEERING_DIR, "docs", "templates"):
        d = root / sub
        if d.is_dir():
            out += [p for p in sorted(d.rglob("*")) if p.is_file() and not p.is_symlink()]
    for sub in ("notes", "catalog", "labs", "sql", "evidence"):
        d = root / sub
        if d.is_dir():
            out += [p for p in sorted(d.rglob("*")) if p.is_file() and not p.is_symlink()]
    for name in ("README.md", "CONTRIBUTING.md"):
        if (root / name).is_file():
            out.append(root / name)
    return out


def check_em_dashes(root, errors):
    for p in policy_text_files(root):
        text = _read(p)
        if text is not None and EM_DASH in text:
            errors.append(f"{p.relative_to(root).as_posix()}: contains an em dash")


def _strip(line):
    return re.sub(r"(^|\s)#.*$", "", line).rstrip()


def _triggers(lines):
    """Return the set of trigger names under the top-level 'on:' key."""
    for i, line in enumerate(lines):
        m = re.match(r"^(?:on|\"on\"|'on'):\s*(.*)$", line)
        if not m:
            continue
        inline = m.group(1).strip()
        if inline:
            return set(re.findall(r"[A-Za-z_]+", inline.strip("[]{}")))
        names, indent = set(), None
        for nxt in lines[i + 1:]:
            if not nxt.strip():
                continue
            ind = len(nxt) - len(nxt.lstrip())
            if ind == 0:
                break
            if indent is None:
                indent = ind
            if ind == indent:
                k = re.match(r"\s*([A-Za-z_]+)\s*:", nxt)
                if k:
                    names.add(k.group(1))
        return names
    return set()


def _permission_blocks(lines):
    """Yield (line_no, inline_value, [(scope, value), ...]) for every permissions key."""
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)permissions:\s*(.*)$", line)
        if not m:
            continue
        indent, inline = len(m.group(1)), m.group(2).strip()
        scopes = []
        if not inline:
            for nxt in lines[i + 1:]:
                if not nxt.strip():
                    continue
                if len(nxt) - len(nxt.lstrip()) <= indent:
                    break
                k = re.match(r"\s*([A-Za-z-]+)\s*:\s*(\S+)", nxt)
                if k:
                    scopes.append((k.group(1), k.group(2)))
        yield i + 1, inline, scopes


def check_workflow_text(name, text, errors, is_mysql=None):
    """Lint one workflow (or the workflow template). name is used only in messages."""
    lines = [_strip(raw) for raw in text.split("\n")]
    body = "\n".join(lines)
    if is_mysql is None:
        is_mysql = "mysql" in name.lower() or "mysql" in body.lower()
    if not any(re.match(r"^permissions:", ln) for ln in lines):
        errors.append(f"{name}: missing top-level 'permissions:'")
    for _no, inline, scopes in _permission_blocks(lines):
        if inline and inline not in ("read-all", "{}"):
            errors.append(f"{name}: permissions must be read-only, found {inline!r}")
        for scope, value in scopes:
            if value not in ("read", "none"):
                errors.append(f"{name}: permission {scope}: {value} is not read-only")
    if re.search(r"pull_request_target", body):
        errors.append(f"{name}: pull_request_target is not allowed")
    for m in re.finditer(r"\bsecrets\.([A-Za-z0-9_]+)", body):
        if m.group(1) != "GITHUB_TOKEN":
            errors.append(f"{name}: references secrets.{m.group(1)}; only GITHUB_TOKEN is allowed")
    if re.search(r"^\s*secrets:\s*inherit", body, re.M):
        errors.append(f"{name}: 'secrets: inherit' is not allowed")
    if is_mysql:
        trig = _triggers(lines)
        if trig != {"workflow_dispatch"}:
            bad = sorted(trig & BAD_TRIGGERS) or sorted(trig)
            errors.append(f"{name}: mysql workflow must be workflow_dispatch only, found triggers {bad or 'none'}")
        if not re.search(r"^\s*timeout-minutes:\s*\d+", body, re.M):
            errors.append(f"{name}: mysql workflow needs timeout-minutes")
        if "upload-artifact" in body:
            days = re.findall(r"retention-days:\s*(\d+)", body)
            if not days:
                errors.append(f"{name}: mysql workflow artifact upload needs retention-days")
            elif any(int(d) < 1 or int(d) > MAX_RETENTION_DAYS for d in days):
                errors.append(f"{name}: retention-days must be between 1 and {MAX_RETENTION_DAYS}")
        else:
            errors.append(f"{name}: mysql workflow must upload sanitized evidence with retention-days")
        if re.search(r"actions/cache", body):
            errors.append(f"{name}: mysql workflow must not use a cache")


def check_workflows(root, errors):
    root = Path(root)
    wf_dir = root / ".github" / "workflows"
    if wf_dir.is_dir():
        for p in sorted(wf_dir.iterdir()):
            if p.suffix not in (".yml", ".yaml") or not p.is_file():
                continue
            text = _read(p)
            if text is None:
                continue
            rel = p.relative_to(root).as_posix()
            check_workflow_text(rel, text, errors)
            if "mysql" in (p.name + text).lower() and p.name not in APPROVED_ACTIVE_MYSQL_WORKFLOWS:
                errors.append(f"{rel}: no mysql workflow is approved for activation, keep it as {WORKFLOW_TEMPLATE}")
    tpl = root / WORKFLOW_TEMPLATE
    text = _read(tpl)
    if text is None:
        errors.append(f"{WORKFLOW_TEMPLATE}: template missing")
    else:
        check_workflow_text(WORKFLOW_TEMPLATE, text, errors, is_mysql=True)


def check_sql_labels(root, errors):
    """The benchmark template must not carry executed or verified status or filled results."""
    root = Path(root)
    p = root / "templates" / "sql-benchmark.md"
    text = _read(p)
    if text is None:
        errors.append("templates/sql-benchmark.md: template missing")
        return
    try:
        fm = validate_catalog.parse_front_matter(text)
    except ValueError as e:
        errors.append(f"templates/sql-benchmark.md: front matter error: {e}")
        return
    if fm.get("status") != "not_started":
        errors.append(f"templates/sql-benchmark.md: status must be not_started, found {fm.get('status')!r}")
    for k, v in fm.items():
        if k.startswith("result_") and v not in (None, "", []):
            errors.append(f"templates/sql-benchmark.md: result field {k} must be empty in the template")
    for sub in ("templates", "docs"):
        d = root / sub
        if not d.is_dir():
            continue
        for q in sorted(d.rglob("*.md")):
            if "sql" not in q.name.lower() or q == p:
                continue
            t = _read(q) or ""
            if t.startswith("---"):
                try:
                    f = validate_catalog.parse_front_matter(t)
                except ValueError:
                    continue
                if f.get("status") in SQL_EXEC_STATUSES:
                    errors.append(f"{q.relative_to(root).as_posix()}: SQL document labelled {f.get('status')}")


def check_policy(root):
    """Return a list of error strings for the repository at root."""
    errors = []
    check_steering(root, errors)
    check_em_dashes(root, errors)
    check_workflows(root, errors)
    check_sql_labels(root, errors)
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    args = ap.parse_args(argv)
    errors = check_policy(Path(args.root))
    for e in errors:
        print(f"ERROR: {e}")
    print(f"{len(errors)} policy error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
