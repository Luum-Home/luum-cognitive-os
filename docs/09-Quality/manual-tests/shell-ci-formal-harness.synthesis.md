---
type: quality-synthesis
source: docs/09-Quality/manual-tests/shell-ci-formal-harness.md
provenance: "Proves Shell/CI is a first-class implemented harness that installs into a temp consumer project without requiring IDE accounts."
---

## What it is
A manual test validating that the Shell/CI harness projection (`cos_init.py --harness shell-ci`) produces a working, account-free set of command drivers and a GitHub Actions workflow in a consumer project.

## Key mechanics
- **Test 1 — Installer projection**: run `cos_init.py --default --harness shell-ci` in a temp dir; assert `.cognitive-os/install-meta.json`, `.cognitive-os/shell-ci-projection.json`, `.cognitive-os/scripts/cos/cos-status.sh` exist, `scripts/cos-status.sh` is a symlink, and `.github/workflows/cognitive-os-shell-ci.yml` exists; validate the projection JSON parses and the status script passes `bash -n` syntax check.
- **Test 2 — ACC projection counts**: `scripts/acc_pipeline.py --project-dir . --brief --fail-new` must report gate `pass` and `new_debt.count == 0`; a targeted query against `docs/07-Capabilities/acc/latest.json` confirms `shell-ci/default` and `shell-ci/full` counts are positive and status is `implemented`.
- **Test 3 — Workflow syntax baseline**: `tests/unit/test_project_shell_ci.py` confirms the generated workflow includes syntax checks for Bash and Python projected commands.
- **Non-claims**: does not prove every projected command succeeds in every consumer stack; does not re-enable disabled repository CI workflows; does not require a GitHub account or hosted runner.

## Relations & where used
Sibling proof to `qwen-code-structural-projection.md` and `rules-mcp-structural-projection.md`; all three validate harness projections through the same ACC pipeline and installer entry point (`scripts/cos_init.py`).

## Status / caveats
No dated evidence block embedded — this is a repeatable procedure spec, not a logged historical run.
