"""Shared best-effort secret patterns for validate_catalog.py and lint_notebooks.py.

Detection is best effort and NOT comprehensive. A clean scan does not prove a
file is free of credentials or personal data. Human review is still required.
Each entry is (label, compiled regex, suffix scope). A scope of None applies to
every scanned text file. Otherwise the pattern only applies to those suffixes.
"""
import re

CODE_SUFFIXES = {".py", ".sql", ".yml", ".yaml"}
EMAIL_ALLOWED_DOMAINS = {"example.com", "example.org", "example.net", "users.noreply.github.com"}
EMAIL_RX = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")

SECRET_PATTERNS = [
    ("databricks token", re.compile(r"dapi[0-9a-f]{32}"), None),
    ("aws access key", re.compile(r"AKIA[0-9A-Z]{16}"), None),
    ("aws secret key assignment", re.compile(r"(?i)aws_secret_access_key[\"']?\s*[=:]\s*[\"']?[A-Za-z0-9/+=]{40}"), None),
    ("bearer token", re.compile(r"Bearer [A-Za-z0-9._~+/=-]{20,}"), None),
    ("private key", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----"), None),
    ("github token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})"), None),
    ("slack token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"), None),
    ("google api key", re.compile(r"AIza[0-9A-Za-z_-]{35}"), None),
    ("jwt-like token", re.compile(r"eyJ[A-Za-z0-9_-]{5,}\.eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*"), None),
    ("azure storage account key", re.compile(r"AccountKey=[A-Za-z0-9+/=]{20,}"), None),
    ("password in url", re.compile(r"\b[A-Za-z][A-Za-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@[^\s/]+"), None),
    ("databricks workspace hostname", re.compile(
        r"\b(?:adb-\d+\.\d+\.azuredatabricks\.net|dbc-[0-9a-f]{8}-[0-9a-f]{4}\.cloud\.databricks\.com)"), None),
    ("hard-coded secret", re.compile(
        r"(?i)\b(?:password|passwd|secret|token|api_key|apikey)\s*[=:]\s*[\"'][^\"']+[\"']"), CODE_SUFFIXES),
]


def scan_text(text, suffix=None):
    """Return the sorted labels of patterns found in text. suffix selects scoped patterns."""
    found = set()
    for label, rx, scope in SECRET_PATTERNS:
        if scope is not None and suffix not in scope:
            continue
        if rx.search(text):
            found.add(label)
    for m in EMAIL_RX.finditer(text):
        if m.group(1).lower() not in EMAIL_ALLOWED_DOMAINS:
            found.add("email address")
            break
    return sorted(found)
