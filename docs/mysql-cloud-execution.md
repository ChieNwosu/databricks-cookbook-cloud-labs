# MySQL cloud execution design

Status: design only. The workflow was **not dispatched** and no MySQL benchmark has been run. Do not read this page as evidence of any result.

## Approach

Use a standard GitHub-hosted `ubuntu-24.04` runner and the preinstalled MySQL service, so nothing runs on the learner's machine and no Docker is needed. The template is [templates/mysql-benchmark-workflow.yml.template](../templates/mysql-benchmark-workflow.yml.template). It lives outside `.github/workflows/`, so GitHub cannot run it. `scripts/check_policy.py` fails if a MySQL workflow appears under `.github/workflows/` and also lints the template.

## Design controls

| Control | Design |
| --- | --- |
| Trigger | `workflow_dispatch` only. No push, pull request, schedule or other trigger. No benchmark on every commit |
| Inputs | `scenario` is a choice. `dataset_rows` is validated as an integer from 1 to 100000 |
| Permissions | `contents: read` only. No secrets other than the built-in token, which is not used |
| Runtime limit | `timeout-minutes` is set |
| Infrastructure | None persistent. The service starts on the runner, an ephemeral database is created and dropped |
| Data | Synthetic, generated with a fixed seed. No real credentials or user data. The runner's default local root login is not a real credential |
| Evidence | `SELECT VERSION()` is recorded. Plans are sanitized (hostnames, paths, users removed) before upload |
| Artifacts | `retention-days` between 1 and 7. No cache |

## Approval

Activating the workflow, dispatching it, or using paid runners, an external database or any new cloud resource each needs separate explicit human approval. The actual MySQL version must be taken from a real run and recorded as `observed_version` in the companion catalog together with evidence.

## Limits of the checks

The policy check verifies workflow shape. It does not prove a run happened, that fixtures are synthetic, or that plans were sanitized correctly. A human reviews each evidence artifact.
