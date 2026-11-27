# Agent governance

This repo uses AI agents (Kiro and delegated sub-agents) to draft material. This page states the policy model, the threats it targets, and which controls are enforced by code or platform permissions versus which are only advisory.

## Policy model

| Layer | Where | Nature |
| --- | --- | --- |
| Input, output, tool-calling guardrails, learning workflow, knowledge governance | `.kiro/steering/*.md` | Advisory instructions to the agent |
| Deterministic repository checks | `scripts/validate_catalog.py`, `scripts/lint_notebooks.py`, `scripts/check_policy.py`, `tests/` | Enforced when run, and run in CI |
| CI workflow permissions | `.github/workflows/validate.yml` (`contents: read`) | Enforced by GitHub |
| Branch and PR permissions, review, merge | GitHub settings and the human | Enforced by GitHub and the human |
| Human approval gates | See below | Enforced only by the human |

Steering files use Kiro's documented frontmatter (`inclusion: always` for the core set, `inclusion: fileMatch` with `fileMatchPattern` for `sql-performance.md`). The [official steering page](https://kiro.dev/docs/steering/) was checked on 2026-11-27 for the supported modes `always`, `fileMatch`, `manual` and `auto`. The steering files were created in this phase. Their loading in any session has not been observed, so this repo does not claim they are active. Custom agents do not load steering automatically and must list it in their resources.

## Threat scenarios

| Threat | Advisory control | Enforced control |
| --- | --- | --- |
| Prompt injection in upstream files or fetched pages | `input-guardrails.md`, reviewer | None. Fetched text cannot be filtered by code here |
| Secret disclosure or commit | `output-guardrails.md` | Best-effort pattern scan in `validate_catalog.py` and `lint_notebooks.py` (CI), steering scan in `check_policy.py`, `.gitignore` |
| Path traversal or symlink escape | `input-guardrails.md` | `_safe_rel`, `check_repo_path`, `check_evidence_paths`, `check_unsafe_paths` and their tests |
| Fabricated execution evidence | `output-guardrails.md` | Evidence file must exist for `executed_unreviewed` and `verified`. Existence is checked, truth is not |
| Status inflation by an agent | `output-guardrails.md` | `verified` needs reviewer, runtime, date, engine version. Notes must match the catalog. A pure `agent_generated` note cannot be `verified` |
| Test weakening or acceptance changes | `output-guardrails.md`, reviewer | Tests run in CI. A weakened test is visible in the diff but not blocked by code |
| Scope creep into Recipe 1.1 | `product.md`, `learning-workflow.md` | Recipe 1.1 stays `not_started` and its note is a stub (validator and tests) |
| Unauthorized workflow dispatch or activation | `tool-calling-guardrails.md` | `check_policy.py` rejects any MySQL workflow under `.github/workflows/`, non-read permissions, `pull_request_target` and extra secrets |
| Destructive notebook cleanup | Code review | Run-scoped names and cleanup logic covered by static and mock tests (not live runs) |
| Malicious dependency or MCP tool | `tool-calling-guardrails.md` | Stdlib-only code. No dependency manifest exists. Human review of any addition |

## Advisory versus enforced

| Advisory (agent may ignore) | Enforced (code or platform) |
| --- | --- |
| Steering files and prompts | GitHub token scope and branch protection |
| Reviewer sub-agent opinion | CI job with `contents: read` |
| This document | Validators, policy check and unit tests, exit codes |

## What automated checks cannot guarantee

- That the agent follows steering at runtime, or that steering is loaded in a session.
- That prose is truthful, original or free of copied text. There is no semantic copyright check.
- That secret detection is complete. Patterns are best effort.
- That evidence is genuine, or that a run really happened. Only presence, path safety and shape are checked.
- That a human reviewer really reviewed anything.
- That a template or document is not edited to hide a problem, beyond what tests and review catch.

## Permission boundaries

Authorized: repository-scoped edits on the PR branch, read-only GitHub inspection, documentation retrieval, standard-library checks, bounded unit tests, commits to the PR branch.

## Human approval gates

The human must approve: setting `verified`, merging, starting the next phase or Recipe 1.1, any paid or cloud resource, any workflow activation or dispatch, any new dependency or MCP tool, lowering `expected_total`.

## Tool actions

| Action | Status |
| --- | --- |
| Read and edit repository files, run local checks and unit tests, commit on the PR branch | Allowed |
| Read official documentation and the public upstream repository | Allowed |
| Merge, write to main, force push, rewrite history, delete branches | Denied |
| Databricks API calls, workspace changes, AWS provisioning, IAM changes, paid services, installing Docker | Denied |
| Dispatch or activate the MySQL workflow, run MySQL benchmarks | Blocked until human approval |
| Credential access or transfer, unapproved MCP tools, remote scripts | Denied |

If a needed action is blocked, report the blocker. Do not work around it.

## Policy check

`python scripts/check_policy.py` verifies steering files and frontmatter, em dash absence in docs and templates, steering secret scan, workflow shape (read-only permissions, no `pull_request_target`, only `GITHUB_TOKEN` secrets, MySQL workflows manual with timeout and retention of 7 days or less), and that the SQL benchmark template is `not_started`. CI runs it. SQL companion catalog rules run inside `validate_catalog.py`.
