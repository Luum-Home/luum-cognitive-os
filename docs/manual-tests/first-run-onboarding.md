# First-Run Onboarding Proof

> Executable proof that a new project can reach a working Cognitive OS baseline with one installer command and visible time budgets.

## Goal

First-run onboarding should feel like product, not an internal script pile.

This proof verifies that:

- a fresh project installs from a local Cognitive OS source in one command
- the selected harness driver is visible in installer output
- the installer prints clear next checks
- core `.cognitive-os` artifacts exist after install
- `cos-status --json` can inspect the project through `COGNITIVE_OS_PROJECT_DIR`
- install and status flows stay inside explicit performance budgets

## Executable Proof

Run from the Cognitive OS source repo:

```bash
bash scripts/demo-first-run-onboarding.sh
```

Run the Claude projection path:

```bash
bash scripts/demo-first-run-onboarding.sh --harness=claude
```

Keep the temp project for inspection:

```bash
bash scripts/demo-first-run-onboarding.sh --keep
```

## Default Budgets

- Install: `30000 ms`
- Status: `5000 ms`
- Total first-run path: `40000 ms`

Override budgets when testing slower machines or stricter release lanes:

```bash
COS_ONBOARDING_INSTALL_BUDGET_MS=30000 \
COS_ONBOARDING_STATUS_BUDGET_MS=5000 \
COS_ONBOARDING_TOTAL_BUDGET_MS=40000 \
  bash scripts/demo-first-run-onboarding.sh
```

## Automated Regression Test

```bash
python3 -m pytest tests/integration/test_first_run_onboarding.py -q
```

The integration test runs the Codex path because Codex is the current self-hosting pressure point for this branch. The manual proof also supports Claude to make sure the onboarding path remains driver-aware instead of silently Codex-only.

## Acceptance Criteria

- Installer exits `0`.
- Installer output includes success, active harness, settings driver, and next checks.
- `.cognitive-os/hooks/cos`, `.cognitive-os/skills/cos`, and `.cognitive-os/templates/cos` exist.
- Codex install creates `.codex/hooks.json` with `CODEX_PROJECT_DIR`.
- Claude install creates `.claude/settings.json` with `CLAUDE_PROJECT_DIR`.
- `cos-status --json` exits `0`.
- `cos-status --json` reports health, canonical skills, and wired hooks.
- Install, status, and total elapsed times stay under budget.

## What This Does Not Claim

This proof intentionally uses `--skip-manifest-check` to measure the core first-run path without host-dependent dependency reporting noise. The manifest check remains important, but its duration depends on local tool availability and should be measured separately if it becomes part of the promised quick-start path.
